"""mcp-dbtools 模块配置

提供数据库查询模块的类型安全配置。
配置默认值在 mcp-common 的 schema 中定义。

用法:
    from mcp_dbtools.config import DBToolsConfig

    config = DBToolsConfig.from_dict({"max_rows": 500})
    print(config.read_only)   # True
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class DBToolsConfig:
    """数据库工具模块配置

    Attributes:
        read_only: 是否只读（默认 True，拒绝写入语句）
        max_rows: 查询最大返回行数（默认 1000）
        query_timeout: 查询超时秒数（默认 30）
    """

    read_only: bool = True
    max_rows: int = 1000
    query_timeout: int = 30

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DBToolsConfig:
        return cls(
            read_only=bool(data.get("read_only", True)),
            max_rows=int(data.get("max_rows", 1000)),
            query_timeout=int(data.get("query_timeout", 30)),
        )
