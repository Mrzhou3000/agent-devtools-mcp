"""PostgreSQL 数据库适配器测试

由于 PostgreSQL 服务在 CI/开发环境不一定可用，
使用 unittest.mock 模拟 asyncpg 连接进行测试。

覆盖:
  - connect / disconnect
  - execute_query (sqlite 风格参数和 PostgreSQL 参数)
  - list_tables
  - describe_table
  - 错误处理
  - 策略模式兼容性
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_dbtools.adapters import PostgreSQLAdapter


@pytest.fixture
def adapter() -> PostgreSQLAdapter:
    """创建 PostgreSQL 适配器实例（未连接）"""
    return PostgreSQLAdapter(
        host="localhost",
        port=5432,
        database="testdb",
        user="testuser",
        password="testpass",
    )


@pytest.fixture
def mock_connection() -> MagicMock:
    """创建模拟的 asyncpg 连接"""
    conn = MagicMock()
    conn.fetch = AsyncMock()
    conn.fetchrow = AsyncMock()
    conn.close = AsyncMock()
    return conn


class TestConnection:
    """连接管理测试"""

    async def test_connect_success(self, adapter: PostgreSQLAdapter) -> None:
        """连接成功"""
        with patch("asyncpg.connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = MagicMock()
            await adapter.connect()
            assert adapter._connection is not None
            mock_connect.assert_called_once_with(
                host="localhost",
                port=5432,
                database="testdb",
                user="testuser",
                password="testpass",
            )

    async def test_connect_failure(self, adapter: PostgreSQLAdapter) -> None:
        """连接失败应该抛出异常"""
        with patch("asyncpg.connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.side_effect = ConnectionError("Connection refused")
            with pytest.raises(ConnectionError, match="Connection refused"):
                await adapter.connect()

    async def test_disconnect(self, adapter: PostgreSQLAdapter) -> None:
        """断开连接"""
        with patch("asyncpg.connect", new_callable=AsyncMock) as mock_connect:
            conn = MagicMock()
            conn.close = AsyncMock()
            mock_connect.return_value = conn
            await adapter.connect()
            await adapter.disconnect()
            conn.close.assert_called_once()
            assert adapter._connection is None

    async def test_double_disconnect(self, adapter: PostgreSQLAdapter) -> None:
        """断开未连接或已断开的连接不报错"""
        await adapter.disconnect()  # 未连接时断开
        assert adapter._connection is None


class TestExecuteQuery:
    """查询执行测试"""

    async def test_select_all(self, adapter: PostgreSQLAdapter, mock_connection: MagicMock) -> None:
        """SELECT 查询应该返回结果"""
        adapter._connection = mock_connection

        # 模拟返回数据
        mock_connection.fetch = AsyncMock(
            return_value=[
                create_record({"id": 1, "name": "Alice", "age": 30}),
                create_record({"id": 2, "name": "Bob", "age": 25}),
            ]
        )

        result = await adapter.execute_query("SELECT * FROM users ORDER BY id")

        assert len(result) == 2
        assert result[0]["name"] == "Alice"
        assert result[1]["name"] == "Bob"
        mock_connection.fetch.assert_called_once_with("SELECT * FROM users ORDER BY id")

    async def test_select_with_params(
        self, adapter: PostgreSQLAdapter, mock_connection: MagicMock
    ) -> None:
        """带参数的查询"""
        adapter._connection = mock_connection

        mock_connection.fetch = AsyncMock(
            return_value=[
                create_record({"id": 1, "name": "Alice"}),
            ]
        )

        result = await adapter.execute_query("SELECT * FROM users WHERE id = $1", (1,))

        assert len(result) == 1
        assert result[0]["name"] == "Alice"
        mock_connection.fetch.assert_called_once_with("SELECT * FROM users WHERE id = $1", 1)

    async def test_empty_result(
        self, adapter: PostgreSQLAdapter, mock_connection: MagicMock
    ) -> None:
        """空结果"""
        adapter._connection = mock_connection
        mock_connection.fetch = AsyncMock(return_value=[])

        result = await adapter.execute_query("SELECT * FROM users WHERE age > 100")
        assert result == []


class TestListTables:
    """列出表测试"""

    async def test_list_tables(
        self, adapter: PostgreSQLAdapter, mock_connection: MagicMock
    ) -> None:
        """列出所有表"""
        adapter._connection = mock_connection

        # mock list_tables SQL query
        mock_connection.fetch = AsyncMock(
            return_value=[
                create_record({"table_name": "users"}),
                create_record({"table_name": "posts"}),
            ]
        )

        # mock describe_table queries
        mock_connection.fetchrow = AsyncMock(return_value=create_record({"cnt": 5}))

        # 第一次 describe_table
        mock_connection.fetch.side_effect = [
            # list_tables result
            [
                create_record({"table_name": "users"}),
                create_record({"table_name": "posts"}),
            ],
            # describe_table users columns
            [
                create_record(
                    {
                        "column_name": "id",
                        "data_type": "integer",
                        "is_nullable": "NO",
                        "column_default": None,
                        "is_pk": True,
                    }
                ),
                create_record(
                    {
                        "column_name": "name",
                        "data_type": "text",
                        "is_nullable": "NO",
                        "column_default": None,
                        "is_pk": False,
                    }
                ),
            ],
            # describe_table posts columns
            [
                create_record(
                    {
                        "column_name": "id",
                        "data_type": "integer",
                        "is_nullable": "NO",
                        "column_default": None,
                        "is_pk": True,
                    }
                ),
                create_record(
                    {
                        "column_name": "title",
                        "data_type": "text",
                        "is_nullable": "YES",
                        "column_default": None,
                        "is_pk": False,
                    }
                ),
            ],
        ]

        tables = await adapter.list_tables()

        assert len(tables) == 2
        assert tables[0].name == "users"
        assert tables[1].name == "posts"

        # 验证第一个表的列信息
        assert len(tables[0].columns) == 2
        assert tables[0].columns[0].name == "id"
        assert tables[0].columns[0].is_primary_key is True
        assert tables[0].columns[1].name == "name"
        assert tables[0].columns[1].data_type == "text"

    async def test_list_tables_empty(
        self, adapter: PostgreSQLAdapter, mock_connection: MagicMock
    ) -> None:
        """空数据库"""
        adapter._connection = mock_connection
        mock_connection.fetch = AsyncMock(return_value=[])

        tables = await adapter.list_tables()
        assert tables == []


class TestDescribeTable:
    """查看表结构测试"""

    async def test_describe_existing_table(
        self, adapter: PostgreSQLAdapter, mock_connection: MagicMock
    ) -> None:
        """查看存在的表结构"""
        adapter._connection = mock_connection

        # mock columns query
        mock_connection.fetch = AsyncMock(
            return_value=[
                create_record(
                    {
                        "column_name": "id",
                        "data_type": "integer",
                        "is_nullable": "NO",
                        "column_default": None,
                        "is_pk": True,
                    }
                ),
                create_record(
                    {
                        "column_name": "name",
                        "data_type": "character varying",
                        "is_nullable": "NO",
                        "column_default": None,
                        "is_pk": False,
                    }
                ),
                create_record(
                    {
                        "column_name": "email",
                        "data_type": "text",
                        "is_nullable": "YES",
                        "column_default": None,
                        "is_pk": False,
                    }
                ),
            ]
        )
        mock_connection.fetchrow = AsyncMock(return_value=create_record({"cnt": 10}))

        info = await adapter.describe_table("users")

        assert info.name == "users"
        assert info.row_count == 10
        assert len(info.columns) == 3
        assert info.columns[0].name == "id"
        assert info.columns[0].data_type == "integer"
        assert info.columns[0].is_primary_key is True
        assert info.columns[0].nullable is False
        assert info.columns[2].name == "email"
        assert info.columns[2].nullable is True

    async def test_describe_invalid_name(self, adapter: PostgreSQLAdapter) -> None:
        """非法表名应该被拒绝"""
        with pytest.raises((ValueError, PermissionError)):
            await adapter.describe_table("users; DROP TABLE posts")

    async def test_describe_with_default(
        self, adapter: PostgreSQLAdapter, mock_connection: MagicMock
    ) -> None:
        """包含默认值的列"""
        adapter._connection = mock_connection
        mock_connection.fetch = AsyncMock(
            return_value=[
                create_record(
                    {
                        "column_name": "status",
                        "data_type": "text",
                        "is_nullable": "YES",
                        "column_default": "'active'::text",
                        "is_pk": False,
                    }
                ),
            ]
        )
        mock_connection.fetchrow = AsyncMock(return_value=create_record({"cnt": 0}))

        info = await adapter.describe_table("settings")
        assert info.columns[0].default == "'active'::text"


class TestDbType:
    """数据库类型标识测试"""

    def test_db_type(self, adapter: PostgreSQLAdapter) -> None:
        """数据库类型标识"""
        assert adapter.db_type == "postgresql"


class TestStrategyPattern:
    """策略模式兼容性测试"""

    async def test_adapter_is_instance_of_base(self, adapter: PostgreSQLAdapter) -> None:
        """PostgreSQLAdapter 是 BaseAdapter 的子类"""
        from mcp_dbtools.adapters.base import BaseAdapter

        assert isinstance(adapter, BaseAdapter)

    async def test_adapter_implements_abstract_methods(self) -> None:
        """PostgreSQLAdapter 实现了所有抽象方法"""
        # 验证不会因为未实现抽象方法而无法实例化
        import inspect
        from mcp_dbtools.adapters.base import BaseAdapter

        pg_async_methods = {
            name
            for name, _ in inspect.getmembers(
                PostgreSQLAdapter, predicate=inspect.iscoroutinefunction
            )
        }
        pg_properties = {
            name
            for name, _ in inspect.getmembers(
                PostgreSQLAdapter, predicate=lambda o: isinstance(o, property)
            )
        }
        pg_members = pg_async_methods | pg_properties

        base_abstract = {
            name
            for name, method in inspect.getmembers(BaseAdapter)
            if getattr(method, "__isabstractmethod__", False)
        }

        for method in base_abstract:
            assert method in pg_members, f"PostgreSQLAdapter 未实现抽象方法 {method}"

    async def test_can_register_tools_like_sqlite(self, adapter: PostgreSQLAdapter) -> None:
        """PostgreSQLAdapter 能像 SQLiteAdapter 一样注册工具"""
        from mcp.server.fastmcp import FastMCP
        from mcp_dbtools.tools.query import register_query_tools

        mcp = FastMCP("test-pg-tools")
        # 不应该抛出异常
        register_query_tools(mcp, adapter)
        # 验证工具已注册
        tool_manager = getattr(mcp, "_tool_manager", None)
        if tool_manager:
            tools = tool_manager.list_tools()
            tool_names = [t.name for t in tools]
            assert "query" in tool_names
            assert "list_tables" in tool_names
            assert "describe_table" in tool_names
            assert "query_with_pagination" in tool_names


# ============================================================
# Helpers
# ============================================================


def create_record(data: dict[str, Any]) -> MagicMock:
    """创建模拟的 asyncpg Record 对象"""
    record = MagicMock()
    record.keys.return_value = list(data.keys())
    record.values.return_value = list(data.values())
    # 支持 dict-like 访问
    record.__getitem__.side_effect = lambda k: data[k]
    # 支持 __contains__
    record.__contains__.side_effect = lambda k: k in data
    return record
