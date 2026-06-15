"""sqlglot SQL 语法解析器 —— AST 级别 SQL 校验

用真实的 SQL 解析器（sqlglot）替代正则匹配进行只读校验。
优势:
  1. 在语法树（AST）层面判断语句类型，**不可绕过**
  2. 正确处理注释、CTE、子查询
  3. 比正则匹配更安全、更可靠

设计:
  - 优先使用 sqlglot（如果已安装）
  - 回退到 regex 校验器（无需额外依赖）

用法:
  from mcp_common.security.sqlglot_validator import validate_readonly_query_ast

  validate_readonly_query_ast("SELECT * FROM users")       # ✅ 通过
  validate_readonly_query_ast("DROP TABLE users")           # ❌ AST 拒绝
  validate_readonly_query_ast("/*comment*/INSERT INTO...")  # ❌ 正则可能漏，AST 不会
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from .sql_validator import SQLValidationError

try:
    import sqlglot  # type: ignore[import-not-found]
    from sqlglot import exp

    HAS_SQLGLOT = True
except ImportError:  # pragma: no cover
    HAS_SQLGLOT = False

if TYPE_CHECKING:
    import sqlglot  # noqa: F401
    from sqlglot import exp  # noqa: F401


# AST 节点类型 —— 这些就是"只读"的 SQL 语句
_READONLY_TYPES: frozenset[Any] = frozenset()

# Command 类型中允许的命令名（EXPLAIN / SHOW 等用 Command 表示）
_READONLY_COMMANDS: frozenset[str] = frozenset()

# 在非 TYPE_CHECKING 时也构造（如果 sqlglot 可用）
if HAS_SQLGLOT:
    _READONLY_TYPES = frozenset([
        exp.Select,
        exp.Describe,
        exp.Union,
        exp.Intersect,
        exp.Except,
    ])
    _READONLY_COMMANDS = frozenset([
        "EXPLAIN",
        "SHOW",
    ])


def _is_readonly_statement(node: exp.Expression) -> bool:
    """检查 AST 是否为只读语句"""
    if not HAS_SQLGLOT:
        return True  # 没有 sqlglot 时不做 AST 检查，由正则层负责
    # 直接匹配已知只读类型（Select, Describe 等）
    if any(isinstance(node, t) for t in _READONLY_TYPES):
        return True
    # Command 类型需要通过命令名进一步判断（EXPLAIN / SHOW 是只读的）
    if isinstance(node, exp.Command) and hasattr(node, "this"):
        cmd_name = str(node.this).upper()
        return cmd_name in _READONLY_COMMANDS
    return False


def _find_write_operations(node: exp.Expression) -> list[str]:
    """在 AST 中查找所有写操作节点，返回操作名列表"""
    writes: list[str] = []
    if not HAS_SQLGLOT:
        return writes

    write_types = {
        exp.Insert: "INSERT",
        exp.Update: "UPDATE",
        exp.Delete: "DELETE",
        exp.Drop: "DROP",
        exp.Alter: "ALTER",
        exp.Create: "CREATE",
        exp.TruncateTable: "TRUNCATE",
        exp.Replace: "REPLACE",
        exp.Merge: "MERGE",
        exp.Grant: "GRANT",
        exp.Revoke: "REVOKE",
    }

    # 这些操作在 sqlglot 中被解析为 Command（Command.this 是命令名）
    write_commands: frozenset[str] = frozenset([
        "REPLACE",
        "RENAME",
        "CALL",
    ])

    for child in node.walk():
        # 检查已知 AST 类型
        for ast_type, name in write_types.items():
            if isinstance(child, ast_type):
                writes.append(name)
                break  # 每个节点只匹配一次
        # 检查 Command 类型的写操作（REPLACE/RENAME/CALL 等已由 write_types 处理）
        if isinstance(child, exp.Command) and hasattr(child, "this"):
            cmd = str(child.this).upper()
            if cmd in write_commands:
                writes.append(cmd)

    # 去重但保持顺序
    seen: set[str] = set()
    unique: list[str] = []
    for w in writes:
        if w not in seen:
            seen.add(w)
            unique.append(w)
    return unique


def validate_readonly_query_ast(sql: str) -> None:
    """用 sqlglot AST 验证 SQL 是否只读

    Args:
        sql: SQL 查询语句

    Raises:
        SQLValidationError: 如果包含写操作或解析失败
    """
    if not sql or not sql.strip():
        raise SQLValidationError("SQL 查询不能为空")

    if not HAS_SQLGLOT:
        # 没有 sqlglot 时无法执行 AST 校验
        raise RuntimeError(
            "sqlglot 未安装，无法使用 AST 校验。\n"
            "请安装: uv add mcp-common -E sqlglot\n"
            "或使用 validate_readonly_query() 正则回退"
        )

    stripped = sql.strip()

    try:
        parsed = sqlglot.parse_one(stripped, read="sqlite")
    except (sqlglot.errors.ParseError, sqlglot.errors.TokenError) as e:
        raise SQLValidationError(
            f"SQL 语法解析失败，无法验证安全性\n"
            f"  {e}\n"
            f"💡 请检查 SQL 语法是否正确"
        )
    except Exception as e:
        raise SQLValidationError(f"SQL 解析异常: {e}")

    # 1️⃣ 检查顶层语句是否为只读类型
    if not _is_readonly_statement(parsed):
        stmt_type = parsed.key.upper() if hasattr(parsed, "key") else "未知"
        raise SQLValidationError(
            f"仅允许只读查询，检测到 '{stmt_type}' 语句\n"
            f"💡 本服务仅支持 SELECT / WITH / EXPLAIN 等只读操作"
        )

    # 2️⃣ 在 AST 中扫描所有写操作节点
    #   （即使顶层是 SELECT, CTE 或子查询中也可能包含写操作）
    writes = _find_write_operations(parsed)
    if writes:
        ops = ", ".join(writes)
        raise SQLValidationError(
            f"查询中包含被禁止的写入操作: {ops}\n"
            f"💡 本服务仅支持只读查询，如需写入请联系管理员"
        )

    # 3️⃣ 多语句检查
    #  sqlglot.parse_one 只返回第一条语句，但如果有分号分隔的多条，
    #  需要用 parse()（复数）。我们检查是否有额外的语句。
    try:
        all_statements = list(sqlglot.parse(stripped, read="sqlite"))
        # 过滤掉 None（空语句）和末尾空白语句
        all_statements = [s for s in all_statements if s is not None]
        if len(all_statements) > 1:
            extra = ", ".join(s.key.upper() for s in all_statements[1:] if hasattr(s, "key"))
            raise SQLValidationError(
                f"不允许执行多条语句（检测到 {len(all_statements)} 条）\n"
                f"  额外语句: {extra}\n"
                f"💡 如果确实需要，请分开调用"
            )
    except SQLValidationError:
        raise
    except Exception as e:
        raise SQLValidationError(f"多语句检查失败: {e}")
