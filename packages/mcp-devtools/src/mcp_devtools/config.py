"""mcp-devtools 模块配置

提供开发工具模块的类型安全配置。

用法:
    from mcp_devtools.config import DevToolsConfig

    config = DevToolsConfig.from_dict({"allow_write": True})
    print(config.workspace_root)  # "."
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DevToolsConfig:
    """开发工具模块配置

    Attributes:
        workspace_root: 工作目录路径
        allow_write: 是否允许文件写入（默认 False）
        allow_command: 是否允许命令执行（默认 False）
        allowed_commands: 命令白名单
        command_timeout: 命令超时秒数（默认 30）
        async_command_timeout: 异步命令超时秒数（默认 300）
    """

    workspace_root: str = "."
    allow_write: bool = False
    allow_command: bool = False
    allowed_commands: list[str] = field(default_factory=lambda: [
        "git", "python", "uv", "pip",
        "ls", "cat", "grep", "find", "pwd", "echo",
        "node", "npm", "npx",
    ])
    command_timeout: int = 30
    async_command_timeout: int = 300

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DevToolsConfig:
        return cls(
            workspace_root=data.get("workspace_root", "."),
            allow_write=bool(data.get("allow_write", False)),
            allow_command=bool(data.get("allow_command", False)),
            allowed_commands=data.get("allowed_commands", [
                "git", "python", "uv", "pip",
                "ls", "cat", "grep", "find", "pwd", "echo",
                "node", "npm", "npx",
            ]),
            command_timeout=int(data.get("command_timeout", 30)),
            async_command_timeout=int(data.get("async_command_timeout", 300)),
        )
