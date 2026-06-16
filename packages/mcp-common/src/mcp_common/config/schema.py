"""配置模型 —— 类型安全的配置数据结构

使用 Pydantic 定义配置模型，提供类型校验和自动补全。

用法:
    from mcp_common.config.schema import AppConfig

    config = AppConfig.from_dict({
        "devtools": {"allow_write": True}
    })
    print(config.devtools.allow_write)  # True
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DevToolsConfig:
    """开发工具模块配置"""

    workspace_root: str = "."
    allow_write: bool = False
    allow_command: bool = False
    allowed_commands: list[str] = field(
        default_factory=lambda: [
            "git",
            "python",
            "uv",
            "pip",
            "ls",
            "cat",
            "grep",
            "find",
            "pwd",
            "echo",
            "node",
            "npm",
            "npx",
        ]
    )
    command_timeout: int = 30

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DevToolsConfig:
        return cls(
            workspace_root=data.get("workspace_root", "."),
            allow_write=bool(data.get("allow_write", False)),
            allow_command=bool(data.get("allow_command", False)),
            allowed_commands=data.get(
                "allowed_commands",
                [
                    "git",
                    "python",
                    "uv",
                    "pip",
                    "ls",
                    "cat",
                    "grep",
                    "find",
                    "pwd",
                    "echo",
                    "node",
                    "npm",
                    "npx",
                ],
            ),
            command_timeout=int(data.get("command_timeout", 30)),
        )


@dataclass
class DatabaseConfig:
    """数据库模块配置"""

    read_only: bool = True
    max_rows: int = 1000
    query_timeout: int = 30

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DatabaseConfig:
        return cls(
            read_only=bool(data.get("read_only", True)),
            max_rows=int(data.get("max_rows", 1000)),
            query_timeout=int(data.get("query_timeout", 30)),
        )


@dataclass
class KnowledgeBaseConfig:
    """知识库模块配置"""

    default_top_k: int = 5
    chunk_size: int = 500
    chunk_overlap: int = 50

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> KnowledgeBaseConfig:
        return cls(
            default_top_k=int(data.get("default_top_k", 5)),
            chunk_size=int(data.get("chunk_size", 500)),
            chunk_overlap=int(data.get("chunk_overlap", 50)),
        )


@dataclass
class AppConfig:
    """应用整体配置"""

    devtools: DevToolsConfig = field(default_factory=DevToolsConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    knowledge_base: KnowledgeBaseConfig = field(default_factory=KnowledgeBaseConfig)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AppConfig:
        return cls(
            devtools=DevToolsConfig.from_dict(data.get("devtools", {})),
            database=DatabaseConfig.from_dict(data.get("database", {})),
            knowledge_base=KnowledgeBaseConfig.from_dict(data.get("knowledge_base", {})),
        )
