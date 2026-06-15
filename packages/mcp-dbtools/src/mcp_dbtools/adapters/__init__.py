"""数据库适配器（策略模式）"""

from .base import BaseAdapter, ColumnInfo, TableInfo
from .postgresql import PostgreSQLAdapter
from .sqlite import SQLiteAdapter

__all__ = [
    "BaseAdapter",
    "ColumnInfo",
    "TableInfo",
    "PostgreSQLAdapter",
    "SQLiteAdapter",
]
