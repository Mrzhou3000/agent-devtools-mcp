"""SQL 校验器 —— 防止 SQL 注入 + 只读检查

核心原则:
    1. 只允许 SELECT / EXPLAIN / DESCRIBE / SHOW / WITH 开头的查询
    2. 拦截 INSERT / UPDATE / DELETE / DROP / ALTER 等写入操作
    3. 防止多条语句执行（分号注入）
    4. 参数化查询（不在这里实现，在 db_engine 中强制使用）

什么是 SQL 注入?
    如果直接拼接用户输入:
    f"SELECT * FROM users WHERE id = {user_input}"
    用户输入: "1; DROP TABLE users; --"
    → 实际执行: SELECT * FROM users WHERE id = 1; DROP TABLE users; --  ← 灾难！

    正确做法:
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_input,))
    → 用户输入被当作值，不是 SQL 语句 ✅

用法:
    validate_readonly_query("SELECT * FROM users")      # ✅ 通过
    validate_readonly_query("DROP TABLE users")          # ❌ 拒绝
    validate_readonly_query("SELECT 1; DROP TABLE users") # ❌ 多语句
"""

from __future__ import annotations

import re
from typing import Pattern


class SQLValidationError(PermissionError):
    """SQL 校验失败时抛出的异常"""


# 写入操作关键字 —— 这些关键字禁止出现在查询中
# 注意：只匹配完整的单词（用 \b 边界），防止匹配到列名中的片段
WRITE_PATTERNS: Pattern[str] = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|REPLACE|"
    r"GRANT|REVOKE|EXEC|EXECUTE|CALL|MERGE|RENAME)\s",
    re.IGNORECASE,
)

# 允许的查询前缀 —— 只有这些开头的 SQL 是只读的
ALLOWED_PREFIXES: list[str] = [
    "SELECT",
    "EXPLAIN",
    "DESCRIBE",
    "DESC",
    "SHOW",
    "WITH",
]


def validate_readonly_query(sql: str) -> None:
    """验证 SQL 查询是只读的

    三条检查规则:
    1. 以只读关键字开头（SELECT / EXPLAIN / DESCRIBE / SHOW / WITH）
    2. 不包含写入关键字（INSERT / UPDATE / DELETE / DROP 等）
    3. 不包含多条语句（分号注入防护）

    Args:
        sql: 用户提交的 SQL 查询语句

    Raises:
        SQLValidationError: 如果查询不满足只读要求
    """
    if not sql or not sql.strip():
        raise SQLValidationError("SQL 查询不能为空")

    stripped = sql.strip()

    # 1️⃣ 检查是否以只读关键字开头
    if not _starts_with_allowed_prefix(stripped):
        raise SQLValidationError(
            "仅允许只读查询（SELECT / EXPLAIN / DESCRIBE / SHOW / WITH）\n"
            f"💡 检测到以 '{stripped.split()[0]}' 开头，这不是只读操作"
        )

    # 2️⃣ 检查是否包含写入关键字
    if WRITE_PATTERNS.search(stripped):
        match = WRITE_PATTERNS.search(stripped)
        keyword = match.group(1) if match else "未知"
        raise SQLValidationError(
            f"查询中包含被禁止的写入操作: '{keyword}'\n"
            f"💡 本服务仅支持只读查询，如需写入请联系管理员"
        )

    # 3️⃣ 检查多语句（分号注入防护）
    # 先移除字符串字面量里的分号（字符串里的 ; 是安全的）
    cleaned = _remove_string_literals(stripped)
    # 去掉末尾的分号（SELECT 1; 是合法的）
    cleaned = cleaned.rstrip(";")
    if ";" in cleaned:
        raise SQLValidationError(
            "不允许执行多条语句（检测到分号）\n💡 如果确实需要执行多条语句，请分开调用"
        )


def validate_table_name(name: str) -> None:
    """验证表名是否合法

    表名只允许包含字母、数字、下划线，且不能以数字开头。

    Args:
        name: 表名

    Raises:
        SQLValidationError: 如果表名不合法
    """
    if not name or not name.strip():
        raise SQLValidationError("表名不能为空")

    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", name):
        raise SQLValidationError(f"非法的表名: '{name}'\n💡 表名只能包含字母、数字和下划线")


def _starts_with_allowed_prefix(sql: str) -> bool:
    """检查 SQL 是否以允许的关键字开头"""
    first_word = sql.split()[0].upper() if sql.split() else ""
    return first_word in ALLOWED_PREFIXES


def _remove_string_literals(sql: str) -> str:
    """移除 SQL 中的字符串字面量

    因为字符串里的分号是安全的（如 WHERE name = 'hello; world'），
    但检测多语句时应该忽略它们。

    实现方式: 用正则替换掉单引号字符串的内容
    """
    # 匹配单引号字符串（包括转义的单引号）
    return re.sub(r"'(?:[^'\\]|\\.)*'", "", sql)
