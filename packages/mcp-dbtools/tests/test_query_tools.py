"""数据库查询工具测试 —— query / list_tables / describe_table

使用 SQLite 内存数据库（:memory:）测试，无需真实数据库文件。
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

import pytest
from mcp.server.fastmcp import FastMCP

from mcp_dbtools.adapters import SQLiteAdapter
from mcp_dbtools.tools.query import register_query_tools


@pytest.fixture
async def adapter() -> AsyncGenerator[SQLiteAdapter, None]:
    """创建并初始化内存 SQLite 数据库"""
    db = SQLiteAdapter(database=":memory:")
    await db.connect()

    # 创建测试表
    await db.execute_query(
        "CREATE TABLE users ("
        "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "  name TEXT NOT NULL,"
        "  email TEXT UNIQUE,"
        "  age INTEGER DEFAULT 0"
        ")"
    )
    await db.execute_query(
        "CREATE TABLE posts ("
        "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "  title TEXT NOT NULL,"
        "  user_id INTEGER REFERENCES users(id)"
        ")"
    )

    # 插入测试数据
    await db.execute_query(
        "INSERT INTO users (name, email, age) VALUES (?, ?, ?)",
        ("Alice", "alice@test.com", 30),
    )
    await db.execute_query(
        "INSERT INTO users (name, email, age) VALUES (?, ?, ?)",
        ("Bob", "bob@test.com", 25),
    )
    await db.execute_query(
        "INSERT INTO posts (title, user_id) VALUES (?, ?)",
        ("Hello World", 1),
    )

    yield db
    await db.disconnect()


def _find_tool(mcp: FastMCP, name: str) -> Any:
    """从 FastMCP 实例中查找工具函数"""
    tool_manager = getattr(mcp, "_tool_manager", None)
    if tool_manager:
        for tool in tool_manager.list_tools():
            if tool.name == name:
                return tool.fn
    return None


class TestListTables:
    """list_tables 工具测试"""

    @pytest.mark.asyncio
    async def test_list_tables(self, adapter: SQLiteAdapter) -> None:
        """列出所有表"""
        mcp = FastMCP("test-dbtools")
        register_query_tools(mcp, adapter)
        fn = _find_tool(mcp, "list_tables")

        result = await fn()
        assert "users" in result
        assert "posts" in result

    @pytest.mark.asyncio
    async def test_list_tables_empty(self) -> None:
        """空数据库应该返回提示"""
        db = SQLiteAdapter(database=":memory:")
        await db.connect()

        mcp = FastMCP("test-dbtools")
        register_query_tools(mcp, db)
        fn = _find_tool(mcp, "list_tables")

        result = await fn()
        assert "数据库中没有表" in result
        await db.disconnect()


class TestDescribeTable:
    """describe_table 工具测试"""

    @pytest.mark.asyncio
    async def test_describe_existing_table(self, adapter: SQLiteAdapter) -> None:
        """查看存在的表结构"""
        mcp = FastMCP("test-dbtools")
        register_query_tools(mcp, adapter)
        fn = _find_tool(mcp, "describe_table")

        result = await fn("users")
        assert "users" in result
        assert "id" in result
        assert "name" in result
        assert "email" in result
        assert "age" in result

    @pytest.mark.asyncio
    async def test_describe_nonexistent_table(self, adapter: SQLiteAdapter) -> None:
        """查看不存在的表应该返回错误"""
        mcp = FastMCP("test-dbtools")
        register_query_tools(mcp, adapter)
        fn = _find_tool(mcp, "describe_table")

        result = await fn("nonexistent")
        assert "❌" in result

    @pytest.mark.asyncio
    async def test_describe_invalid_name(self, adapter: SQLiteAdapter) -> None:
        """非法的表名应该被拒绝"""
        mcp = FastMCP("test-dbtools")
        register_query_tools(mcp, adapter)
        fn = _find_tool(mcp, "describe_table")

        result = await fn("users; DROP TABLE posts")
        assert "❌" in result


class TestQuery:
    """query 工具测试"""

    @pytest.mark.asyncio
    async def test_select_all(self, adapter: SQLiteAdapter) -> None:
        """SELECT 查询应该成功"""
        mcp = FastMCP("test-dbtools")
        register_query_tools(mcp, adapter)
        fn = _find_tool(mcp, "query")

        result = await fn("SELECT * FROM users ORDER BY id")
        assert "Alice" in result
        assert "Bob" in result
        assert "2 行" in result

    @pytest.mark.asyncio
    async def test_select_with_where(self, adapter: SQLiteAdapter) -> None:
        """带 WHERE 的 SELECT 应该成功"""
        mcp = FastMCP("test-dbtools")
        register_query_tools(mcp, adapter)
        fn = _find_tool(mcp, "query")

        result = await fn("SELECT name, age FROM users WHERE age > 25")
        assert "Alice" in result
        assert "Bob" not in result

    @pytest.mark.asyncio
    async def test_select_join(self, adapter: SQLiteAdapter) -> None:
        """JOIN 查询应该成功"""
        mcp = FastMCP("test-dbtools")
        register_query_tools(mcp, adapter)
        fn = _find_tool(mcp, "query")

        result = await fn(
            "SELECT u.name, p.title FROM users u "
            "JOIN posts p ON u.id = p.user_id"
        )
        assert "Alice" in result
        assert "Hello World" in result

    @pytest.mark.asyncio
    async def test_empty_result(self, adapter: SQLiteAdapter) -> None:
        """查询结果为空应该返回提示"""
        mcp = FastMCP("test-dbtools")
        register_query_tools(mcp, adapter)
        fn = _find_tool(mcp, "query")

        result = await fn("SELECT * FROM users WHERE age > 100")
        assert "查询结果为空" in result

    @pytest.mark.security
    @pytest.mark.asyncio
    async def test_insert_rejected(self, adapter: SQLiteAdapter) -> None:
        """INSERT 语句应该被拒绝"""
        mcp = FastMCP("test-dbtools")
        register_query_tools(mcp, adapter)
        fn = _find_tool(mcp, "query")

        result = await fn("INSERT INTO users VALUES (3, 'Eve', 'eve@test.com', 20)")
        assert "❌" in result
        assert "SQL 被拒绝" in result or "只读" in result

    @pytest.mark.security
    @pytest.mark.asyncio
    async def test_drop_rejected(self, adapter: SQLiteAdapter) -> None:
        """DROP 语句应该被拒绝"""
        mcp = FastMCP("test-dbtools")
        register_query_tools(mcp, adapter)
        fn = _find_tool(mcp, "query")

        result = await fn("DROP TABLE users")
        assert "❌" in result

    @pytest.mark.security
    @pytest.mark.asyncio
    async def test_multi_statement_rejected(self, adapter: SQLiteAdapter) -> None:
        """多语句（SELECT + 分号）应该被拒绝"""
        mcp = FastMCP("test-dbtools")
        register_query_tools(mcp, adapter)
        fn = _find_tool(mcp, "query")

        result = await fn("SELECT * FROM users; DROP TABLE users")
        assert "❌" in result


class TestPagination:
    """query_with_pagination 工具测试"""

    @pytest.mark.asyncio
    async def test_pagination_first_page(self, adapter: SQLiteAdapter) -> None:
        """第1页应该返回前 page_size 条"""
        mcp = FastMCP("test-dbtools")
        register_query_tools(mcp, adapter)
        fn = _find_tool(mcp, "query_with_pagination")

        result = await fn("SELECT * FROM users ORDER BY id", page=1, page_size=1)
        assert "Alice" in result
        assert "第 1/2 页" in result or "1/2" in result
        assert "总行数: 2" in result

    @pytest.mark.asyncio
    async def test_pagination_second_page(self, adapter: SQLiteAdapter) -> None:
        """第2页应该返回剩余数据"""
        mcp = FastMCP("test-dbtools")
        register_query_tools(mcp, adapter)
        fn = _find_tool(mcp, "query_with_pagination")

        result = await fn("SELECT * FROM users ORDER BY id", page=2, page_size=1)
        assert "Bob" in result
        assert "第 2/2 页" in result or "2/2" in result

    @pytest.mark.asyncio
    async def test_pagination_invalid_page(self, adapter: SQLiteAdapter) -> None:
        """页码小于 1 应报错"""
        mcp = FastMCP("test-dbtools")
        register_query_tools(mcp, adapter)
        fn = _find_tool(mcp, "query_with_pagination")

        result = await fn("SELECT * FROM users", page=0)
        assert "❌" in result

    @pytest.mark.asyncio
    async def test_pagination_empty_result(self, adapter: SQLiteAdapter) -> None:
        """匹配不存在的条件应返回空"""
        mcp = FastMCP("test-dbtools")
        register_query_tools(mcp, adapter)
        fn = _find_tool(mcp, "query_with_pagination")

        result = await fn("SELECT * FROM users WHERE age > 100", page=1, page_size=20)
        assert "总行数: 0" in result

    @pytest.mark.asyncio
    async def test_pagination_all_in_one(self, adapter: SQLiteAdapter) -> None:
        """page_size 足够大时应该返回全部数据"""
        mcp = FastMCP("test-dbtools")
        register_query_tools(mcp, adapter)
        fn = _find_tool(mcp, "query_with_pagination")

        result = await fn("SELECT * FROM users ORDER BY id", page=1, page_size=100)
        assert "Alice" in result
        assert "Bob" in result
        assert "总行数: 2" in result

    @pytest.mark.asyncio
    async def test_pagination_sql_rejected(self, adapter: SQLiteAdapter) -> None:
        """非 SELECT 语句应被拒绝"""
        mcp = FastMCP("test-dbtools")
        register_query_tools(mcp, adapter)
        fn = _find_tool(mcp, "query_with_pagination")

        result = await fn("DELETE FROM users")
        assert "❌" in result
        assert "被拒绝" in result or "只读" in result
