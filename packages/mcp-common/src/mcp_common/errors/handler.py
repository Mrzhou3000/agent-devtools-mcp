"""统一错误处理

所有 MCP 工具的错误通过此模块处理，确保：
1. 错误信息格式统一（用户可读的语言）
2. 包含解决建议
3. 错误被审计日志记录

用法:
    from mcp_common.errors.handler import format_error, ToolError

    # 主动抛出带建议的错误
    raise ToolError("文件不存在", code="COM_NFO_001",
                    suggestion="请检查文件路径是否正确")

    # 格式化安全异常
    error_msg = format_error(e, context={"tool": "read_file"})
"""

from __future__ import annotations

from typing import Any

from .codes import ErrorCategory, get_error_code


class ToolError(Exception):
    """工具有效错误 —— 带有建议操作的错误

    Attributes:
        message: 用户可读的错误描述
        code: 错误码（如 "COM_SEC_001"）
        suggestion: 解决建议
        details: 额外详细信息
    """

    def __init__(
        self,
        message: str,
        code: str = "COM_UNKNOWN_001",
        suggestion: str = "",
        details: dict[str, Any] | None = None,
    ):
        self.message = message
        self.code = code
        self.suggestion = suggestion or _default_suggestion(code)
        self.details = details or {}
        super().__init__(self.__str__())

    def __str__(self) -> str:
        parts = [f"❌ {self.message}"]
        if self.suggestion:
            parts.append(f"💡 {self.suggestion}")
        return "\n".join(parts)

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "suggestion": self.suggestion,
            "details": self.details,
        }


# 已知错误码的默认建议
_SUGGESTIONS: dict[str, str] = {
    "COM_SEC_001": "请检查文件路径是否包含 '..'，或使用了工作目录之外的绝对路径",
    "COM_SEC_002": "支持的扩展名: .md, .py, .txt, .json, .yaml, .toml, .js, .ts, .html, .css",
    "COM_SEC_003": "请使用白名单中的命令，或联系管理员添加",
    "COM_SEC_004": "命令参数中不允许包含特殊字符",
    "COM_SEC_005": "如果确实需要写入操作，请配置 read_only=false",
    "COM_SEC_006": "请一次只执行一条 SQL 查询",
    "COM_VAL_001": "请检查参数是否完整",
    "COM_EXE_003": "请简化命令或增加 timeout 参数",
    "COM_EXE_004": "建议优化 SQL 查询或增加索引",
    "COM_EXE_005": "请检查数据库路径和权限配置",
    "COM_NFO_001": "请检查文件路径是否正确",
    "COM_NFO_002": "请先调用 list_tables 查看所有可用表",
    "COM_NFO_003": "请先调用 create_kb 创建知识库",
    "COM_NFO_004": "请检查命令是否已安装",
    "COM_CFG_001": '请在配置中设置 allow_write=true（默认禁用，安全考虑）',
    "COM_CFG_002": '请在配置中设置 allow_command=true（默认禁用，安全考虑）',
}


def _default_suggestion(code: str) -> str:
    """获取错误码的默认建议"""
    return _SUGGESTIONS.get(code, "请检查输入参数后重试")  # fmt: skip


def format_error(error: Exception, context: dict[str, Any] | None = None) -> str:
    """将异常格式化为用户友好的错误消息

    统一的错误三要素:
    1. ❌ 发生了什么（用户能理解的语言）
    2. 💡 怎么解决（给出具体操作建议）
    3. 🔗 参考文档（指向配置文档或工具文档）

    Args:
        error: 原始异常
        context: 可选的上下文信息（如工具名、参数等）

    Returns:
        格式化后的错误消息
    """
    if isinstance(error, ToolError):
        return str(error)

    if isinstance(error, PermissionError):
        msg = str(error)
        return (
            f"❌ 权限错误: {msg}\n"
            f"💡 请检查操作权限或配置文件中的开关设置"
        )

    if isinstance(error, FileNotFoundError):
        return (
            f"❌ 文件不存在: {error}\n"
            f"💡 请检查文件路径是否正确"
        )

    if isinstance(error, TimeoutError):
        return (
            f"❌ 操作超时: {error}\n"
            f"💡 建议简化操作或增加超时时间"
        )

    # 通用错误
    context_str = ""
    if context:
        ctx_parts = [f"{k}={v}" for k, v in context.items()]
        context_str = f" ({', '.join(ctx_parts)})"

    return (
        f"❌ 操作失败{context_str}: {error}\n"
        f"💡 请检查输入参数后重试"
    )


def is_security_error(error: Exception) -> bool:
    """判断是否为安全相关错误"""
    if isinstance(error, ToolError):
        ec = get_error_code(error.code)
        return ec is not None and ec.category == ErrorCategory.SECURITY
    return isinstance(error, PermissionError)
