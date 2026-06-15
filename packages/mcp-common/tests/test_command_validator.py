"""命令校验器测试 —— 覆盖所有安全场景"""

from __future__ import annotations

import pytest

from mcp_common.security.command_validator import (
    CommandValidator,
    CommandValidationError,
)


class TestCommandValidator:
    """命令校验器测试"""

    def setup_method(self) -> None:
        self.validator = CommandValidator()

    # ── 正常命令通过 ──────────────────────────────────

    def test_allowed_command_no_args(self) -> None:
        """白名单内的命令（无参数）应该通过"""
        # 不抛异常就算通过
        self.validator.validate("git", [])

    def test_allowed_command_with_args(self) -> None:
        """白名单内的命令（带参数）应该通过"""
        self.validator.validate("git", ["status"])
        self.validator.validate("git", ["diff", "--cached"])
        self.validator.validate("python", ["--version"])
        self.validator.validate("ls", ["-la", "/tmp"])

    def test_command_none_args(self) -> None:
        """args 为 None 时应该和空列表一样处理"""
        self.validator.validate("git")  # 不传 args

    # ── 命令不在白名单 ────────────────────────────────

    @pytest.mark.security
    def test_disallowed_command(self) -> None:
        """不在白名单的命令应该被拒绝"""
        with pytest.raises(CommandValidationError, match="不在白名单"):
            self.validator.validate("rm", ["-rf", "/"])

    @pytest.mark.security
    def test_disallowed_command_sudo(self) -> None:
        """sudo 应该被拒绝"""
        with pytest.raises(CommandValidationError):
            self.validator.validate("sudo", ["rm", "-rf", "/"])

    @pytest.mark.security
    def test_disallowed_command_chmod(self) -> None:
        """chmod 应该被拒绝"""
        with pytest.raises(CommandValidationError):
            self.validator.validate("chmod", ["777", "/etc/shadow"])

    # ── 参数注入攻击拦截 ──────────────────────────────

    @pytest.mark.security
    @pytest.mark.parametrize("dangerous_char", [
        ";",     # 命令分隔符
        "`",     # 命令替换
        "$",     # 变量引用
        "|",     # 管道
        "&&",    # 与运算
        "||",    # 或运算
        ">",     # 重定向
        "<",     # 重定向
        "&",     # 后台运行
        "\n",    # 换行注入
    ])
    def test_dangerous_chars_in_args(self, dangerous_char: str) -> None:
        """参数中的危险字符应该被拦截"""
        with pytest.raises(CommandValidationError, match="危险字符"):
            self.validator.validate("git", [f"status{dangerous_char}rm -rf /"])

    @pytest.mark.security
    @pytest.mark.parametrize("attack_input", [
        "`cat /etc/passwd`",
        "$(cat /etc/passwd)",
        "1; SELECT * FROM admins",
        "& ping 8.8.8.8 &",
        "|| whoami",
        "&& echo hacked",
    ])
    def test_common_injection_patterns(self, attack_input: str) -> None:
        """常见命令注入模式应该被拦截"""
        with pytest.raises(CommandValidationError):
            self.validator.validate("git", [attack_input])

    # ── 白名单管理 ───────────────────────────────────

    def test_add_allowed_command(self) -> None:
        """动态添加命令到白名单"""
        self.validator.add_allowed_command("docker")
        self.validator.validate("docker", ["ps"])  # 应该通过

    def test_remove_allowed_command(self) -> None:
        """从白名单移除命令"""
        self.validator.remove_allowed_command("git")
        with pytest.raises(CommandValidationError):
            self.validator.validate("git", ["status"])
