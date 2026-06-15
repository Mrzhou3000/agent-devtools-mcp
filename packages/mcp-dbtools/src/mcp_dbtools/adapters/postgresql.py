"""PostgreSQL 数据库适配器

使用 asyncpg 实现异步 PostgreSQL 数据库访问。
需要 PostgreSQL 服务可用。

使用示例:
    adapter = PostgreSQLAdapter(
        host="localhost",
        port=5432,
        database="mydb",
        user="postgres",
        password="secret",
    )
    async with adapter:
        tables = await adapter.list_tables()
        result = await adapter.execute_query("SELECT * FROM users")
"""
from __future__ import annotations

from typing import Any

from mcp_common.security.sql_validator import validate_table_name  # type: ignore[import-not-found]

from .base import BaseAdapter, ColumnInfo, TableInfo


class PostgreSQLAdapter(BaseAdapter):
    """PostgreSQL 数据库适配器

    通过 asyncpg 连接 PostgreSQL，
    使用 information_schema 获取元数据。
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        database: str | None = None,
        user: str | None = None,
        password: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password,
            **kwargs,
        )
        self._host = host
        self._port = port
        self._database = database
        self._user = user
        self._password = password

    async def connect(self) -> None:
        import asyncpg  # type: ignore[import-not-found]

        self._connection = await asyncpg.connect(
            host=self._host,
            port=self._port,
            database=self._database,
            user=self._user,
            password=self._password,
        )

    async def disconnect(self) -> None:
        if self._connection:
            await self._connection.close()
            self._connection = None

    async def execute_query(
        self, sql: str, params: tuple[Any, ...] | None = None
    ) -> list[dict[str, Any]]:
        if params is None:
            rows = await self._connection.fetch(sql)
        else:
            rows = await self._connection.fetch(sql, *params)

        if not rows:
            return []

        columns = list(rows[0].keys())
        return [dict(zip(columns, row.values())) for row in rows]

    async def list_tables(self) -> list[TableInfo]:
        rows = await self._connection.fetch(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_type = 'BASE TABLE'
            ORDER BY table_name
            """
        )
        tables = []
        for row in rows:
            info = await self.describe_table(row["table_name"])
            tables.append(info)
        return tables

    async def describe_table(self, table_name: str) -> TableInfo:
        validate_table_name(table_name)

        # 获取列信息
        column_rows = await self._connection.fetch(
            """
            SELECT
                c.column_name,
                c.data_type,
                c.is_nullable,
                c.column_default,
                CASE WHEN pk.column_name IS NOT NULL THEN TRUE ELSE FALSE END AS is_pk
            FROM information_schema.columns c
            LEFT JOIN (
                SELECT ku.column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage ku
                    ON tc.constraint_name = ku.constraint_name
                    AND tc.table_schema = ku.table_schema
                WHERE tc.constraint_type = 'PRIMARY KEY'
                  AND tc.table_schema = 'public'
                  AND tc.table_name = $1
            ) pk ON pk.column_name = c.column_name
            WHERE c.table_schema = 'public'
              AND c.table_name = $1
            ORDER BY c.ordinal_position
            """,
            table_name,
        )

        columns = [
            ColumnInfo(
                name=row["column_name"],
                data_type=row["data_type"],
                nullable=row["is_nullable"] == "YES",
                is_primary_key=row["is_pk"],
                default=row["column_default"],
            )
            for row in column_rows
        ]

        # 获取行数
        count_result = await self._connection.fetchrow(
            f"SELECT COUNT(*) AS cnt FROM {table_name}"
        )
        row_count = count_result["cnt"] if count_result else 0

        return TableInfo(
            name=table_name,
            columns=columns,
            row_count=row_count,
        )

    @property
    def db_type(self) -> str:
        return "postgresql"
