"""命令校验器 —— 防止命令注入攻击（Command Injection）

核心原则:
    1. 命令白名单 —— 只允许执行预设的命令
    2. 禁用 shell 模式 —— 永远使用 subprocess.run([cmd, args], shell=False)
    3. 参数校验 —— 拒绝包含危险字符的参数

什么是 shell 注入?
    如果你用 subprocess.run(f"git {user_input}", shell=True)
    用户输入 "status; rm -rf /" → 实际执行两条命令：
    1. git status
    2. rm -rf /  ← 灾难！

    但如果你用 subprocess.run(["git", user_input], shell=False)
    用户输入 "status; rm -rf /" → 系统找一个叫
    "status; rm -rf /" 的 git 子命令 → 找不到 → 报错 ✅

用法:
    validator = CommandValidator()
    validator.validate("git", ["status"])       # ✅ 通过
    validator.validate("rm", ["-rf", "/"])      # ❌ rm 不在白名单
    validator.validate("git", ["; rm -rf /"])   # ❌ 含危险字符
"""

from __future__ import annotations

from typing import Set


class CommandValidationError(PermissionError):
    """命令校验失败时抛出的异常"""


# 危险字符 —— 这些字符在 shell 中有特殊含义
# 如果参数中包含它们，可能是注入攻击
DANGEROUS_CHARS: Set[str] = {
    ";",  # 命令分隔符
    "`",  # 命令替换
    "$",  # 变量引用 / 命令替换 $(...)
    "|",  # 管道
    "&&",  # 与运算
    "||",  # 或运算
    ">",  # 重定向输出
    "<",  # 重定向输入
    "&",  # 后台运行
    "\n",  # 换行（多行命令）
}

# 默认白名单 —— 只允许这些命令被执行
# 原则：只加确定安全的开发工具，不加高危命令
DEFAULT_ALLOWED_COMMANDS: Set[str] = {
    # 版本控制
    "git",
    # Python 生态
    "python",
    "python3",
    "uv",
    "pip",
    # Node.js 生态
    "node",
    "npm",
    "npx",
    # 文件查看（只读）
    "ls",
    "cat",
    "head",
    "tail",
    "grep",
    "find",
    "wc",
    # 目录 / 路径
    "pwd",
    "which",
    "echo",
    # 构建工具
    "make",
    "cmake",
    # 代码格式化
    "ruff",
    "black",
}


class CommandValidator:
    """命令校验器 —— 确保只执行安全的命令"""

    def __init__(self, allowed_commands: Set[str] | None = None) -> None:
        """
        Args:
            allowed_commands: 允许执行的命令白名单
                              （默认使用 DEFAULT_ALLOWED_COMMANDS）
        """
        self.allowed_commands = allowed_commands or DEFAULT_ALLOWED_COMMANDS.copy()

    def validate(self, command: str, args: list[str] | None = None) -> None:
        """校验命令和参数是否安全

        Args:
            command: 命令名（如 "git", "python"）
            args: 命令参数列表（如 ["status"], ["--version"]）

        Raises:
            CommandValidationError: 如果命令不在白名单或参数包含危险字符
        """
        if args is None:
            args = []

        # 1️⃣ 检查命令是否在白名单中
        if command not in self.allowed_commands:
            allowed_list = ", ".join(sorted(self.allowed_commands))
            raise CommandValidationError(
                f"命令 '{command}' 不在白名单内。\n"
                f"💡 允许的命令: {allowed_list}\n"
                f"💡 如需添加，请在配置中设置 allowed_commands"
            )

        # 2️⃣ 检查参数是否包含危险字符
        for arg in args:
            self._validate_arg(arg)

    def _validate_arg(self, arg: str) -> None:
        """检查单个参数是否包含危险字符"""
        for char in DANGEROUS_CHARS:
            if char in arg:
                raise CommandValidationError(
                    f"参数包含危险字符 '{char}'，已拦截。\n"
                    f"💡 参数内容: {arg[:100]}{'...' if len(arg) > 100 else ''}"
                )

    def add_allowed_command(self, command: str) -> None:
        """动态添加一个命令到白名单"""
        self.allowed_commands.add(command)

    def remove_allowed_command(self, command: str) -> None:
        """从白名单中移除一个命令"""
        self.allowed_commands.discard(command)
