"""sqlglot SQL 语法解析器测试 —— AST 级别 SQL 校验

覆盖所有场景:
  - 正常只读 SQL ✅
  - 各种写操作拦截 ❌
  - CTE/子查询中的隐藏写入
  - 多语句注入（分号）
  - 注释绕过检测
  - 语法错误处理
  - sqlglot 未安装回退
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from mcp_common.security.sql_validator import SQLValidationError

# 只在 sqlglot 可用时导入
try:
    from mcp_common.security.sqlglot_validator import (
        HAS_SQLGLOT,
        validate_readonly_query_ast,
    )

    HAS_SQLGLOT_IMPORT = HAS_SQLGLOT
except ImportError:
    HAS_SQLGLOT_IMPORT = False


if TYPE_CHECKING or HAS_SQLGLOT_IMPORT:
    from mcp_common.security import sqlglot_validator


# ============================================================
# 基础只读查询
# ============================================================


class TestValidReadonlyQueries:
    """合法的只读查询应该通过 AST 校验"""

    def test_select_simple(self) -> None:
        """简单的 SELECT"""
        validate_readonly_query_ast("SELECT * FROM users")

    def test_select_columns(self) -> None:
        """指定列的 SELECT"""
        validate_readonly_query_ast("SELECT id, name, email FROM users")

    def test_select_with_where(self) -> None:
        """带 WHERE 的 SELECT"""
        validate_readonly_query_ast("SELECT * FROM users WHERE age > 18")

    def test_select_with_join(self) -> None:
        """带 JOIN 的 SELECT"""
        validate_readonly_query_ast(
            "SELECT u.name, o.amount FROM users u JOIN orders o ON u.id = o.user_id"
        )

    def test_select_with_group_by(self) -> None:
        """带 GROUP BY 和聚合的 SELECT"""
        validate_readonly_query_ast(
            "SELECT department, COUNT(*) FROM employees GROUP BY department"
        )

    def test_select_with_subquery(self) -> None:
        """子查询"""
        validate_readonly_query_ast("SELECT * FROM users WHERE id IN (SELECT user_id FROM orders)")

    def test_select_with_limit(self) -> None:
        """带 LIMIT 的 SELECT"""
        validate_readonly_query_ast("SELECT * FROM users LIMIT 10")

    def test_select_with_order(self) -> None:
        """带 ORDER BY 的 SELECT"""
        validate_readonly_query_ast("SELECT * FROM users ORDER BY created_at DESC")

    def test_select_with_union(self) -> None:
        """UNION 查询"""
        validate_readonly_query_ast("SELECT name FROM users UNION SELECT name FROM admins")

    def test_select_with_trailing_semicolon(self) -> None:
        """末尾分号是合法的"""
        validate_readonly_query_ast("SELECT * FROM users;")

    def test_explain_query(self) -> None:
        """EXPLAIN 查询"""
        validate_readonly_query_ast("EXPLAIN SELECT * FROM users")

    def test_describe_table(self) -> None:
        """DESCRIBE 查询"""
        validate_readonly_query_ast("DESCRIBE users")

    def test_with_cte(self) -> None:
        """WITH (CTE) 查询"""
        validate_readonly_query_ast(
            "WITH active_users AS (SELECT * FROM users WHERE active = 1) "
            "SELECT * FROM active_users"
        )

    def test_cte_with_multiple(self) -> None:
        """多个 CTE"""
        validate_readonly_query_ast(
            "WITH "
            "active AS (SELECT * FROM users WHERE active = 1), "
            "ordered AS (SELECT * FROM active ORDER BY name) "
            "SELECT * FROM ordered"
        )

    def test_select_numeric(self) -> None:
        """纯数值查询"""
        validate_readonly_query_ast("SELECT 1")

    def test_select_function(self) -> None:
        """函数调用"""
        validate_readonly_query_ast("SELECT COUNT(*), MAX(price), MIN(price) FROM products")


# ============================================================
# 写操作拦截
# ============================================================


class TestWriteOperationsRejected:
    """所有写入操作应该被 AST 拒绝"""

    @pytest.mark.parametrize(
        "sql,op",
        [
            ("DROP TABLE users", "DROP"),
            ("DROP DATABASE mydb", "DROP"),
            ("INSERT INTO users VALUES (1, 'admin')", "INSERT"),
            ("UPDATE users SET name = 'hacker' WHERE id = 1", "UPDATE"),
            ("DELETE FROM users WHERE id = 1", "DELETE"),
            ("ALTER TABLE users ADD COLUMN hacker TEXT", "ALTER"),
            ("CREATE TABLE hackers (id INT)", "CREATE"),
            ("TRUNCATE TABLE users", "TRUNCATE"),
            ("REPLACE INTO users VALUES (1, 'admin')", "REPLACE"),
            ("RENAME TABLE users TO hackers", "RENAME"),
            ("MERGE INTO target USING source ON id = id WHEN MATCHED THEN UPDATE", "MERGE"),
            ("GRANT SELECT ON users TO 'hacker'", "GRANT"),
            ("REVOKE SELECT ON users FROM 'user'", "REVOKE"),
            ("CALL some_procedure()", "CALL"),
        ],
    )
    def test_write_operation_rejected(self, sql: str, op: str) -> None:
        """写操作应该被拒绝"""
        with pytest.raises(SQLValidationError):
            validate_readonly_query_ast(sql)


# ============================================================
# 子查询 / CTE 中的隐藏写操作
# ============================================================


class TestHiddenWriteOperations:
    """在只读结构内部隐藏写操作"""

    @pytest.mark.security
    def test_cte_with_drop(self) -> None:
        """CTE 中不能有 DROP"""
        with pytest.raises(SQLValidationError, match="DROP"):
            validate_readonly_query_ast("WITH dropped AS (DROP TABLE users) SELECT * FROM dropped")

    @pytest.mark.security
    def test_cte_with_insert(self) -> None:
        """CTE 中不能有 INSERT"""
        with pytest.raises(SQLValidationError, match="INSERT"):
            validate_readonly_query_ast(
                "WITH ins AS (INSERT INTO log VALUES (1)) SELECT * FROM ins"
            )

    @pytest.mark.security
    def test_subquery_with_update(self) -> None:
        """子查询中不能有 UPDATE"""
        with pytest.raises(SQLValidationError, match="UPDATE"):
            validate_readonly_query_ast("SELECT * FROM (UPDATE users SET name = 'x') AS t")

    @pytest.mark.security
    def test_nested_cte_write(self) -> None:
        """嵌套 CTE 中的写操作"""
        with pytest.raises(SQLValidationError):
            validate_readonly_query_ast(
                "WITH outer_cte AS ("
                "  WITH inner_cte AS (DELETE FROM items) "
                "  SELECT * FROM inner_cte"
                ") "
                "SELECT * FROM outer_cte"
            )


# ============================================================
# 多语句注入
# ============================================================


class TestMultiStatementDetection:
    """分号分隔的多条语句应该被拦截"""

    @pytest.mark.security
    def test_select_then_drop(self) -> None:
        """SELECT + DROP 多语句"""
        with pytest.raises(SQLValidationError):
            validate_readonly_query_ast("SELECT 1; DROP TABLE users")

    @pytest.mark.security
    def test_select_then_insert(self) -> None:
        """SELECT + INSERT 多语句"""
        with pytest.raises(SQLValidationError):
            validate_readonly_query_ast("SELECT * FROM users; INSERT INTO log VALUES (1)")

    @pytest.mark.security
    def test_multiple_selects(self) -> None:
        """多条 SELECT（仍然是多语句）"""
        with pytest.raises(SQLValidationError):
            validate_readonly_query_ast("SELECT * FROM users; SELECT * FROM admins")

    @pytest.mark.security
    def test_hidden_multi_statement(self) -> None:
        """注释中的分号不应该影响检测"""
        with pytest.raises(SQLValidationError):
            validate_readonly_query_ast("SELECT * FROM users; /* comment */ SELECT * FROM admins")


# ============================================================
# 注释处理
# ============================================================


class TestCommentHandling:
    """注释中的关键字不应该影响检测"""

    def test_select_with_line_comment(self) -> None:
        """行注释（--）"""
        validate_readonly_query_ast("SELECT * FROM users -- this is a comment")

    def test_select_with_block_comment(self) -> None:
        """块注释（/* */）"""
        validate_readonly_query_ast("SELECT * FROM users /* comment with DROP inside */")

    @pytest.mark.security
    def test_block_comment_with_write(self) -> None:
        """块注释后的写操作应该被拦截"""
        with pytest.raises(SQLValidationError):
            validate_readonly_query_ast("SELECT 1; /* comment */ INSERT INTO users VALUES (1)")


# ============================================================
# 边界条件和错误处理
# ============================================================


class TestEdgeCases:
    """边界条件和错误处理"""

    def test_empty_sql(self) -> None:
        """空 SQL"""
        with pytest.raises(SQLValidationError, match="不能为空"):
            validate_readonly_query_ast("")

    def test_whitespace_only(self) -> None:
        """只有空白字符"""
        with pytest.raises(SQLValidationError, match="不能为空"):
            validate_readonly_query_ast("   \n  ")

    @pytest.mark.security
    def test_sql_injection_via_union(self) -> None:
        """UNION 注入 —— UNION 是只读的"""
        # UNION 本身是只读的，应该通过
        validate_readonly_query_ast("SELECT * FROM users UNION SELECT * FROM admins")


# ============================================================
# sqlglot 回退行为 (HAS_SQLGLOT = False)
# ============================================================


class TestFallbackBehavior:
    """sqlglot 未安装时的行为"""

    def test_no_sqlglot_raises_runtime_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """没有 sqlglot 时应该抛出 RuntimeError"""
        # 注意：需要确保这个测试在 sqlglot 可用时也能正确模拟
        if HAS_SQLGLOT_IMPORT:
            monkeypatch.setattr(sqlglot_validator, "HAS_SQLGLOT", False)

        with pytest.raises(RuntimeError, match="sqlglot 未安装"):
            validate_readonly_query_ast("SELECT * FROM users")

    def test_no_sqlglot_with_empty_sql(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """没有 sqlglot + 空 SQL 仍然应该报错"""
        if HAS_SQLGLOT_IMPORT:
            monkeypatch.setattr(sqlglot_validator, "HAS_SQLGLOT", False)

        with pytest.raises(SQLValidationError, match="不能为空"):
            validate_readonly_query_ast("")


# ============================================================
# 语法错误
# ============================================================


class TestSyntaxErrors:
    """SQL 语法错误处理"""

    def test_invalid_syntax(self) -> None:
        """无效的 SQL 语法应该报错"""
        with pytest.raises(SQLValidationError, match="SQL 语法解析失败|无法验证"):
            validate_readonly_query_ast("SELECT FROM")

    def test_garbage_input(self) -> None:
        """乱码输入"""
        with pytest.raises(SQLValidationError, match="解析失败|无法验证|解析异常"):
            validate_readonly_query_ast("@@@$$$~~~")

    def test_incomplete_query(self) -> None:
        """不完整的查询"""
        with pytest.raises(SQLValidationError, match="解析失败|无法验证"):
            validate_readonly_query_ast("SELECT FROM")


# ============================================================
# 大小写不敏感性
# ============================================================


class TestCaseInsensitivity:
    """SQL 关键字大小写不敏感"""

    def test_lowercase_select(self) -> None:
        """小写 select"""
        validate_readonly_query_ast("select * from users")

    def test_mixed_case_select(self) -> None:
        """混合大小写 SeLeCt"""
        validate_readonly_query_ast("SeLeCt * FrOm users")

    @pytest.mark.security
    def test_lowercase_drop(self) -> None:
        """小写 drop"""
        with pytest.raises(SQLValidationError):
            validate_readonly_query_ast("drop table users")


# ============================================================
# 性能测试（确保不会超时）
# ============================================================


class TestPerformance:
    """SQL 解析性能"""

    def test_large_query(self) -> None:
        """较大的查询不应该超时"""
        columns = ", ".join(f"col_{i}" for i in range(100))
        sql = (
            f"SELECT {columns} FROM very_large_table WHERE id IN (SELECT ref_id FROM another_table)"
        )
        # 应该快速完成
        validate_readonly_query_ast(sql)

    def test_deeply_nested_query(self) -> None:
        """深层嵌套的查询"""
        sql = (
            "WITH "
            + ", ".join(f"lv_{i} AS (SELECT * FROM base WHERE level = {i})" for i in range(20))
            + " SELECT * FROM lv_19"
        )
        validate_readonly_query_ast(sql)
