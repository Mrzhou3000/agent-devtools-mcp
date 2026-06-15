"""SQL 校验器测试 —— 覆盖所有安全场景"""

from __future__ import annotations

import pytest

from mcp_common.security.sql_validator import (
    validate_readonly_query,
    validate_table_name,
    SQLValidationError,
)


class TestSQLValidator:
    """SQL 只读校验测试"""

    # ── 正常查询通过 ──────────────────────────────────

    def test_select_simple(self) -> None:
        """简单的 SELECT 查询应该通过"""
        validate_readonly_query("SELECT * FROM users")  # 不抛异常

    def test_select_with_where(self) -> None:
        """带 WHERE 的 SELECT 查询应该通过"""
        validate_readonly_query("SELECT id, name FROM users WHERE age > 18")

    def test_select_with_join(self) -> None:
        """带 JOIN 的 SELECT 查询应该通过"""
        validate_readonly_query(
            "SELECT u.name, o.amount FROM users u JOIN orders o ON u.id = o.user_id"
        )

    def test_explain_query(self) -> None:
        """EXPLAIN 查询应该通过"""
        validate_readonly_query("EXPLAIN SELECT * FROM users")

    def test_describe_table(self) -> None:
        """DESCRIBE 查询应该通过"""
        validate_readonly_query("DESCRIBE users")

    def test_with_cte(self) -> None:
        """WITH (CTE) 查询应该通过"""
        validate_readonly_query("WITH active AS (SELECT * FROM users) SELECT * FROM active")

    def test_select_with_limit(self) -> None:
        """带 LIMIT 的 SELECT"""
        validate_readonly_query("SELECT * FROM users LIMIT 10")

    # ── 非 SELECT 语句拦截（第一道防线：前缀检查）─────

    @pytest.mark.security
    @pytest.mark.parametrize("bad_sql", [
        "INSERT INTO users VALUES (1, 'admin')",
        "UPDATE users SET name = 'hacker' WHERE id = 1",
        "DELETE FROM users WHERE id = 1",
        "DROP TABLE users",
        "DROP DATABASE mydb",
        "ALTER TABLE users ADD COLUMN hacker TEXT",
        "CREATE TABLE hackers (id INT)",
        "TRUNCATE TABLE users",
        "REPLACE INTO users VALUES (1, 'admin')",
        "GRANT ALL ON *.* TO 'hacker'",
        "REVOKE ALL ON *.* FROM 'user'",
        "RENAME TABLE users TO hackers",
    ])
    def test_non_select_rejected(self, bad_sql: str) -> None:
        """不以 SELECT/EXPLAIN/DESCRIBE/SHOW/WITH 开头的语句应该被拒绝

        注意: 这里检查的是 '只读'（第一道防线拦截）
        """
        with pytest.raises(SQLValidationError, match="只读"):
            validate_readonly_query(bad_sql)

    # ── SELECT 语句中包含写入操作（第二道防线）─────────

    @pytest.mark.security
    @pytest.mark.parametrize("bad_sql", [
        "SELECT 1; INSERT INTO users VALUES (2, 'hacker')",
    ])
    def test_select_contains_write(self, bad_sql: str) -> None:
        """SELECT 语句中包含写入关键字应该被拒绝"""
        with pytest.raises(SQLValidationError, match="写入|多条"):
            validate_readonly_query(bad_sql)

    # ── 多语句注入拦截（第三道防线）───────────────────

    @pytest.mark.security
    def test_multi_statement_semicolon(self) -> None:
        """分号分隔的多条语句应该被拦截

        注意: DROP TABLE 会被"写入操作检测"先拦住
        """
        with pytest.raises(SQLValidationError):
            validate_readonly_query("SELECT 1; DROP TABLE users")

    @pytest.mark.security
    def test_multi_statement_hidden_drop(self) -> None:
        """隐藏在多条 SELECT 中的 DROP 应该被拦截"""
        with pytest.raises(SQLValidationError, match="多条语句"):
            validate_readonly_query("SELECT * FROM users; SELECT * FROM admins")

    def test_semicolon_in_string(self) -> None:
        """字符串中的分号应该是安全的（不报错）"""
        validate_readonly_query(
            "SELECT * FROM users WHERE name = 'hello; world'"
        )

    # ── 参数化 SQL 注入模式 ──────────────────────────

    @pytest.mark.security
    @pytest.mark.parametrize("injection_sql", [
        "SELECT * FROM users WHERE id = 1; DROP TABLE users",
    ])
    def test_sql_injection_patterns(self, injection_sql: str) -> None:
        """常见 SQL 注入模式应该被拦截"""
        with pytest.raises(SQLValidationError):
            validate_readonly_query(injection_sql)

    # ── 非法表名拦截 ─────────────────────────────────

    def test_valid_table_name(self) -> None:
        """合法的表名应该通过"""
        validate_table_name("users")
        validate_table_name("user_orders")
        validate_table_name("_temp_table")

    @pytest.mark.security
    @pytest.mark.parametrize("bad_name", [
        "users; DROP TABLE",
        "../../etc/passwd",
        "users table",
        "123table",
        "table name with spaces",
    ])
    def test_invalid_table_name(self, bad_name: str) -> None:
        """非法的表名应该被拒绝"""
        with pytest.raises(SQLValidationError):
            validate_table_name(bad_name)

    def test_empty_table_name(self) -> None:
        """空表名应该被拒绝"""
        with pytest.raises(SQLValidationError, match="不能为空"):
            validate_table_name("")
