"""SQLite 数据库适配器

使用 aiosqlite 实现异步数据库访问。
SQLite 开箱即用，无需额外配置数据库服务。
"""

from __future__ import annotations

from typing import Any

from mcp_common.security.sql_validator import validate_table_name

from .base import BaseAdapter, ColumnInfo, TableInfo


class SQLiteAdapter(BaseAdapter):
    """SQLite 数据库适配器

    使用示例:
        adapter = SQLiteAdapter(database="data.db")
        async with adapter:
            tables = await adapter.list_tables()
            result = await adapter.execute_query("SELECT * FROM users")
    """

    def __init__(self, database: str, **kwargs: Any) -> None:
        super().__init__(database=database, **kwargs)
        self._database = database

    async def connect(self) -> None:
        import aiosqlite

        self._connection = await aiosqlite.connect(self._database)
        self._connection.row_factory = aiosqlite.Row

    async def disconnect(self) -> None:
        if self._connection:
            await self._connection.close()
            self._connection = None

    async def execute_query(
        self, sql: str, params: tuple[Any, ...] | None = None
    ) -> list[dict[str, Any]]:
        cursor = await self._connection.execute(sql, params or ())
        rows = await cursor.fetchall()
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        await cursor.close()

        return [dict(zip(columns, row)) for row in rows]

    async def list_tables(self) -> list[TableInfo]:
        rows = await self.execute_query(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = []
        for row in rows:
            info = await self.describe_table(row["name"])
            tables.append(info)
        return tables

    async def describe_table(self, table_name: str) -> TableInfo:
        validate_table_name(table_name)

        rows = await self.execute_query(f"PRAGMA table_info('{table_name}')")

        columns = [
            ColumnInfo(
                name=row["name"],
                data_type=row["type"] or "TEXT",
                nullable=not row["notnull"],
                is_primary_key=bool(row["pk"]),
                default=row["dflt_value"],
            )
            for row in rows
        ]

        # 获取行数
        count_result = await self.execute_query(f"SELECT COUNT(*) as cnt FROM '{table_name}'")
        row_count = count_result[0]["cnt"] if count_result else 0

        return TableInfo(
            name=table_name,
            columns=columns,
            row_count=row_count,
        )

    @property
    def db_type(self) -> str:
        return "sqlite"
