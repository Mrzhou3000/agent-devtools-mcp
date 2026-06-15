"""统一错误码定义

所有 MCP 模块使用统一的错误码体系，便于客户端识别和处理。

错误码格式: {模块}_{分类}_{编号}
    - 模块: 三位字母缩写（COM=common, DEV=devtools, DB=dbtools, KB=kbtools）
    - 分类: 三位字母缩写（SEC=安全, VAL=校验, EXE=执行, CFG=配置）
    - 编号: 三位数字（从 001 开始）

用法:
    from mcp_common.errors.codes import ErrorCode, ErrorCategory

    err = ErrorCode.COM_SEC_001  # "路径穿越检测"
    print(err.category)           # ErrorCategory.SECURITY
    print(err.message)           # "路径越权：文件路径超出工作目录范围"
"""

from __future__ import annotations

from enum import Enum
from typing import Final


class ErrorCategory(Enum):
    """错误分类"""

    SECURITY = "security"       # 安全相关（路径穿越、命令注入、SQL 注入）
    VALIDATION = "validation"   # 校验相关（参数校验、类型校验）
    EXECUTION = "execution"     # 执行相关（超时、IO 错误、进程崩溃）
    CONFIG = "configuration"    # 配置相关（缺少配置、配置错误）
    NOT_FOUND = "not_found"     # 未找到（文件不存在、表不存在）
    UNKNOWN = "unknown"         # 未知错误


class ErrorCode:
    """错误码

    每个错误码包含: 唯一标识、分类、用户可读的消息、建议操作。
    """

    def __init__(
        self,
        code: str,
        category: ErrorCategory,
        message: str,
        suggestion: str = "",
    ) -> None:
        self.code = code
        self.category = category
        self.message = message
        self.suggestion = suggestion

    def to_dict(self) -> dict[str, str]:
        return {
            "code": self.code,
            "category": self.category.value,
            "message": self.message,
            "suggestion": self.suggestion,
        }

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"

    def __repr__(self) -> str:
        return f"ErrorCode({self.code})"


# ═══════════════════════════════════════════════════════════════
# 安全类错误 (SEC)
# ═══════════════════════════════════════════════════════════════

COM_SEC_001: Final[ErrorCode] = ErrorCode(
    "COM_SEC_001",
    ErrorCategory.SECURITY,
    "路径越权：文件路径超出工作目录范围",
    "请检查文件路径是否包含 '..'，或使用了工作目录之外的绝对路径",
)

COM_SEC_002: Final[ErrorCode] = ErrorCode(
    "COM_SEC_002",
    ErrorCategory.SECURITY,
    "文件类型不允许：只允许读取文本文件",
    "支持的扩展名: .md, .py, .txt, .json, .yaml, .toml, .js, .ts, .html, .css",
)

COM_SEC_003: Final[ErrorCode] = ErrorCode(
    "COM_SEC_003",
    ErrorCategory.SECURITY,
    "命令不在白名单内",
    "请使用白名单中的命令，或联系管理员添加",
)

COM_SEC_004: Final[ErrorCode] = ErrorCode(
    "COM_SEC_004",
    ErrorCategory.SECURITY,
    "参数包含危险字符，已拦截",
    "命令参数中不允许包含 ; ` $ | && || > < 等特殊字符",
)

COM_SEC_005: Final[ErrorCode] = ErrorCode(
    "COM_SEC_005",
    ErrorCategory.SECURITY,
    "仅允许只读查询（SELECT/EXPLAIN/DESCRIBE/SHOW）",
    "如果确实需要写入操作，请配置 read_only=false",
)

COM_SEC_006: Final[ErrorCode] = ErrorCode(
    "COM_SEC_006",
    ErrorCategory.SECURITY,
    "不允许执行多条 SQL 语句",
    "请一次只执行一条 SQL 查询",
)

# ═══════════════════════════════════════════════════════════════
# 校验类错误 (VAL)
# ═══════════════════════════════════════════════════════════════

COM_VAL_001: Final[ErrorCode] = ErrorCode(
    "COM_VAL_001",
    ErrorCategory.VALIDATION,
    "参数校验失败：缺少必填参数",
    "请检查参数是否完整",
)

COM_VAL_002: Final[ErrorCode] = ErrorCode(
    "COM_VAL_002",
    ErrorCategory.VALIDATION,
    "参数类型错误",
    "请检查参数类型是否正确",
)

COM_VAL_003: Final[ErrorCode] = ErrorCode(
    "COM_VAL_003",
    ErrorCategory.VALIDATION,
    "非法的表名格式",
    "表名只能包含字母、数字和下划线",
)

# ═══════════════════════════════════════════════════════════════
# 执行类错误 (EXE)
# ═══════════════════════════════════════════════════════════════

COM_EXE_001: Final[ErrorCode] = ErrorCode(
    "COM_EXE_001",
    ErrorCategory.EXECUTION,
    "文件读取失败",
    "请检查文件是否存在，以及文件权限是否正确",
)

COM_EXE_002: Final[ErrorCode] = ErrorCode(
    "COM_EXE_002",
    ErrorCategory.EXECUTION,
    "文件写入失败",
    "请检查磁盘空间和文件权限",
)

COM_EXE_003: Final[ErrorCode] = ErrorCode(
    "COM_EXE_003",
    ErrorCategory.EXECUTION,
    "命令执行超时",
    "请简化命令或增加 timeout 参数",
)

COM_EXE_004: Final[ErrorCode] = ErrorCode(
    "COM_EXE_004",
    ErrorCategory.EXECUTION,
    "数据库查询超时",
    "建议优化 SQL 查询或增加索引",
)

COM_EXE_005: Final[ErrorCode] = ErrorCode(
    "COM_EXE_005",
    ErrorCategory.EXECUTION,
    "数据库连接失败",
    "请检查数据库路径和权限配置",
)

# ═══════════════════════════════════════════════════════════════
# 未找到类错误 (NFO)
# ═══════════════════════════════════════════════════════════════

COM_NFO_001: Final[ErrorCode] = ErrorCode(
    "COM_NFO_001",
    ErrorCategory.NOT_FOUND,
    "文件不存在",
    "请检查文件路径是否正确",
)

COM_NFO_002: Final[ErrorCode] = ErrorCode(
    "COM_NFO_002",
    ErrorCategory.NOT_FOUND,
    "数据库表不存在",
    "请先调用 list_tables 查看所有可用表",
)

COM_NFO_003: Final[ErrorCode] = ErrorCode(
    "COM_NFO_003",
    ErrorCategory.NOT_FOUND,
    "知识库不存在",
    "请先调用 create_kb 创建知识库",
)

COM_NFO_004: Final[ErrorCode] = ErrorCode(
    "COM_NFO_004",
    ErrorCategory.NOT_FOUND,
    "命令未找到",
    "请检查命令是否已安装，或使用绝对路径",
)

# ═══════════════════════════════════════════════════════════════
# 配置类错误 (CFG)
# ═══════════════════════════════════════════════════════════════

COM_CFG_001: Final[ErrorCode] = ErrorCode(
    "COM_CFG_001",
    ErrorCategory.CONFIG,
    "写入操作未启用",
    '请在配置中设置 allow_write=true（默认禁用，安全考虑）',
)

COM_CFG_002: Final[ErrorCode] = ErrorCode(
    "COM_CFG_002",
    ErrorCategory.CONFIG,
    "命令执行未启用",
    '请在配置中设置 allow_command=true（默认禁用，安全考虑）',
)


# ═══════════════════════════════════════════════════════════════
# 工具函数
# ═══════════════════════════════════════════════════════════════

# 所有错误码的列表
ALL_ERROR_CODES: list[ErrorCode] = [
    COM_SEC_001, COM_SEC_002, COM_SEC_003, COM_SEC_004, COM_SEC_005, COM_SEC_006,
    COM_VAL_001, COM_VAL_002, COM_VAL_003,
    COM_EXE_001, COM_EXE_002, COM_EXE_003, COM_EXE_004, COM_EXE_005,
    COM_NFO_001, COM_NFO_002, COM_NFO_003, COM_NFO_004,
    COM_CFG_001, COM_CFG_002,
]

ERROR_CODE_MAP: dict[str, ErrorCode] = {ec.code: ec for ec in ALL_ERROR_CODES}


def get_error_code(code: str) -> ErrorCode | None:
    """根据错误码字符串查找 ErrorCode 对象"""
    return ERROR_CODE_MAP.get(code)
