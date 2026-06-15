"""安全沙箱 —— 三层防御体系的总控

这是安全模块的入口，其他模块（devtools/dbtools/kbtools）通过 Sandbox 来执行所有安全检查。

三层防御在代码中的体现:
    第1层 边界防护: Sandbox 初始化时设置工作目录和命令白名单
    第2层 操作管控: validate_path() / validate_command() / validate_sql() 方法
    第3层 审计追溯: log_call() 方法记录每次工具调用

用法:
    sandbox = Sandbox(workspace_root="/home/user/projects")

    # 校验文件路径
    path = sandbox.validate_path("src/server.py")

    # 校验命令
    sandbox.validate_command("git", ["status"])

    # 记录审计日志
    sandbox.log_call("read_file", {"path": "src/server.py"}, "success")
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .path_validator import PathValidator
from .command_validator import CommandValidator
from .sql_validator import validate_readonly_query, validate_table_name


class AuditEntry:
    """一条审计日志记录"""

    def __init__(
        self,
        tool_name: str,
        args_safe: dict[str, Any],
        status: str,
        duration_ms: float = 0,
        error: str | None = None,
    ):
        self.timestamp = datetime.now(timezone.utc)
        self.tool_name = tool_name
        self.args_safe = args_safe  # 脱敏后的参数（不记录文件内容）
        self.status = status
        self.duration_ms = duration_ms
        self.error = error

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "tool": self.tool_name,
            "args": self.args_safe,
            "status": self.status,
            "duration_ms": self.duration_ms,
            "error": self.error,
        }


class Sandbox:
    """安全沙箱 —— 所有工具调用的安全守卫

    整合路径校验、命令校验、SQL 校验，并提供审计日志功能。
    每个 MCP 模块（devtools/dbtools/kbtools）初始化时创建一个 Sandbox 实例。
    """

    def __init__(
        self,
        workspace_root: str | Path,
        allowed_commands: set[str] | None = None,
    ) -> None:
        """
        Args:
            workspace_root: 工作目录路径（所有文件操作限制在此目录内）
            allowed_commands: 命令白名单（None 则使用默认白名单）
        """
        self.path_validator = PathValidator(workspace_root)
        self.command_validator = CommandValidator(allowed_commands)

        # 审计日志存储（内存中，生产环境应持久化到磁盘）
        self.audit_log: list[AuditEntry] = []

    # ════════════════════════════════════════════════
    # 第2层：操作管控 —— 各种校验方法
    # ════════════════════════════════════════════════

    def validate_path(self, target_path: str) -> Path:
        """校验文件路径（路径穿越防护）

        Args:
            target_path: 用户传入的相对路径

        Returns:
            安全的绝对路径
        """
        return self.path_validator.validate(target_path)

    def validate_file(self, target_path: str) -> Path:
        """校验路径且必须存在（文件读取前调用）"""
        return self.path_validator.validate_file(target_path)

    def validate_command(self, command: str, args: list[str] | None = None) -> None:
        """校验命令（命令注入防护）

        Args:
            command: 命令名
            args: 命令参数
        """
        self.command_validator.validate(command, args)

    def validate_sql_query(self, sql: str) -> None:
        """校验 SQL 查询（只读检查 + 注入防护）"""
        validate_readonly_query(sql)

    def validate_table_name(self, name: str) -> None:
        """校验表名"""
        validate_table_name(name)

    # ════════════════════════════════════════════════
    # 第3层：审计追溯 —— 日志记录
    # ════════════════════════════════════════════════

    def log_call(
        self,
        tool_name: str,
        args: dict[str, Any],
        status: str = "success",
        duration_ms: float = 0,
        error: str | None = None,
    ) -> None:
        """记录工具调用到审计日志

        Args:
            tool_name: 调用的工具名
            args: 工具参数（会自动脱敏，不记录文件内容）
            status: 调用状态（"success" / "error" / "rejected"）
            duration_ms: 执行耗时（毫秒）
            error: 错误信息（如果有）
        """
        entry = AuditEntry(
            tool_name=tool_name,
            args_safe=self._sanitize_args(args),
            status=status,
            duration_ms=duration_ms,
            error=error,
        )
        self.audit_log.append(entry)

    def get_audit_log(self, last_n: int = 50) -> list[dict[str, Any]]:
        """获取最近的审计日志

        Args:
            last_n: 返回最近多少条记录

        Returns:
            审计日志列表（字典格式）
        """
        return [entry.to_dict() for entry in self.audit_log[-last_n:]]

    # ════════════════════════════════════════════════
    # 内部方法
    # ════════════════════════════════════════════════

    @staticmethod
    def _sanitize_args(args: dict[str, Any]) -> dict[str, Any]:
        """脱敏参数：不记录文件内容和大文本数据

        审计日志中只记录"文件名"，不记录"文件内容"
        """
        sanitized: dict[str, Any] = {}
        SENSITIVE_KEYS = {"content", "body", "data", "sql"}  # SQL 本身不脱敏，因为需要审计

        for key, value in args.items():
            if key in SENSITIVE_KEYS:
                if isinstance(value, str) and len(value) > 100:
                    sanitized[key] = value[:50] + f"... (共 {len(value)} 字符)"
                else:
                    sanitized[key] = value
            else:
                sanitized[key] = value

        return sanitized
