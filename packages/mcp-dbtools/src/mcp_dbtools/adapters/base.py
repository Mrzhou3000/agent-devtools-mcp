"""数据库适配器基类（策略模式）

所有数据库类型通过统一的抽象接口访问，
上层工具代码无需关心具体的数据库类型。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ColumnInfo:
    """列信息"""
    name: str
    data_type: str
    nullable: bool
    is_primary_key: bool = False
    default: str | None = None
    comment: str | None = None


@dataclass
class TableInfo:
    """表信息"""
    name: str
    columns: list[ColumnInfo]
    row_count: int | None = None
    comment: str | None = None


class BaseAdapter(ABC):
    """数据库适配器抽象基类

    所有数据库适配器（SQLite / PostgreSQL / MySQL）都继承此类。
    策略模式让上层工具代码与具体数据库解耦。
    """

    def __init__(self, **kwargs: Any) -> None:
        self._connection: Any = None
        self._config = kwargs

    @abstractmethod
    async def connect(self) -> None:
        """连接到数据库"""
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        """断开数据库连接"""
        ...

    @abstractmethod
    async def execute_query(self, sql: str, params: tuple[Any, ...] | None = None) -> list[dict[str, Any]]:
        """执行查询并返回结果列表（每行一个 dict）"""
        ...

    @abstractmethod
    async def list_tables(self) -> list[TableInfo]:
        """列出数据库中所有表"""
        ...

    @abstractmethod
    async def describe_table(self, table_name: str) -> TableInfo:
        """查看指定表的列结构"""
        ...

    @property
    @abstractmethod
    def db_type(self) -> str:
        """数据库类型名称"""
        ...

    # ── 上下文管理器支持 ──

    async def __aenter__(self) -> BaseAdapter:
        await self.connect()
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.disconnect()
