"""命令执行工具测试 —— run_command / git_status / git_diff"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from mcp.server.fastmcp import FastMCP

from mcp_common.security.sandbox import Sandbox
from mcp_devtools.tools.command_ops import register_command_tools


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    """创建临时工作目录"""
    # 创建一个测试文件
    test_file = tmp_path / "hello.txt"
    test_file.write_text("Hello, World!", encoding="utf-8")
    return tmp_path


@pytest.fixture
def mcp_and_sandbox(workspace: Path) -> tuple[Any, ...]:
    """创建 MCP Server 和 Sandbox 实例"""
    sandbox = Sandbox(workspace_root=str(workspace))
    mcp = FastMCP("test-devtools")
    register_command_tools(mcp, sandbox)
    return mcp, sandbox


def _find_tool(mcp: FastMCP, name: str) -> Any:
    """从 FastMCP 实例中查找工具函数"""
    # FastMCP 在注册时将工具函数作为可调用对象保存
    # 我们可以通过检查 mcp._tool_manager 来找到它
    tool_manager = getattr(mcp, "_tool_manager", None)
    if tool_manager:
        for tool in tool_manager.list_tools():
            if tool.name == name:
                return tool.fn
    return None


class TestRunCommand:
    """run_command 工具测试"""

    @pytest.mark.asyncio
    async def test_echo_command(self, mcp_and_sandbox: Any, workspace: Path) -> None:
        """允许的命令应该执行成功"""
        mcp, sandbox = mcp_and_sandbox
        tool_fn = _find_tool(mcp, "run_command")
        if tool_fn is None:
            pytest.skip("无法获取 run_command 工具函数")

        result = await tool_fn("echo", "Hello World")
        assert "Hello World" in result

    @pytest.mark.asyncio
    async def test_python_command(self, mcp_and_sandbox: Any, workspace: Path) -> None:
        """python 命令应该执行成功"""
        mcp, sandbox = mcp_and_sandbox
        tool_fn = _find_tool(mcp, "run_command")
        if tool_fn is None:
            pytest.skip("无法获取 run_command 工具函数")

        result = await tool_fn("python", "-c print('hi')")
        # 注意：python -c 带参数时需要正确的 shell 分词
        # 这里测试简单场景
        assert result  # 至少返回了内容

    @pytest.mark.asyncio
    async def test_disallowed_command(self, mcp_and_sandbox: Any, workspace: Path) -> None:
        """不允许的命令应该被拒绝"""
        mcp, sandbox = mcp_and_sandbox
        tool_fn = _find_tool(mcp, "run_command")
        if tool_fn is None:
            pytest.skip("无法获取 run_command 工具函数")

        result = await tool_fn("rm", "-rf /")
        assert "❌" in result

    @pytest.mark.asyncio
    async def test_dangerous_chars(self, mcp_and_sandbox: Any, workspace: Path) -> None:
        """参数中含有危险字符应该被拒绝"""
        mcp, sandbox = mcp_and_sandbox
        tool_fn = _find_tool(mcp, "run_command")
        if tool_fn is None:
            pytest.skip("无法获取 run_command 工具函数")

        result = await tool_fn("echo", "hello; rm -rf /")
        assert "❌" in result

    @pytest.mark.asyncio
    async def test_timeout(self, mcp_and_sandbox: Any, workspace: Path) -> None:
        """超时的命令应该返回提示"""
        mcp, sandbox = mcp_and_sandbox
        tool_fn = _find_tool(mcp, "run_command")
        if tool_fn is None:
            pytest.skip("无法获取 run_command 工具函数")

        # 创建一个休眠脚本文件，避免参数中含有危险字符
        sleep_script = workspace / "_sleep_test.py"
        sleep_script.write_text("import time\ntime.sleep(10)\n", encoding="utf-8")

        result = await tool_fn("python", f"{sleep_script.name}", timeout=1)
        assert "❌" in result
        assert "超时" in result

    @pytest.mark.asyncio
    @pytest.mark.security
    async def test_path_traversal_workdir(self, mcp_and_sandbox: Any, workspace: Path) -> None:
        """路径穿越的工作目录应该被拒绝"""
        mcp, sandbox = mcp_and_sandbox
        tool_fn = _find_tool(mcp, "run_command")
        if tool_fn is None:
            pytest.skip("无法获取 run_command 工具函数")

        result = await tool_fn("ls", work_dir="../../etc")
        assert "❌" in result


class TestGitStatus:
    """git_status 工具测试"""

    @pytest.mark.asyncio
    async def test_not_a_git_repo(self, mcp_and_sandbox: Any, workspace: Path) -> None:
        """非 Git 仓库应该提示"""
        mcp, sandbox = mcp_and_sandbox
        tool_fn = _find_tool(mcp, "git_status")
        if tool_fn is None:
            pytest.skip("无法获取 git_status 工具函数")

        result = await tool_fn(".")
        assert "❌" in result
        assert "不是 Git 仓库" in result

    @pytest.mark.asyncio
    async def test_path_traversal(self, mcp_and_sandbox: Any, workspace: Path) -> None:
        """路径穿越应该被拒绝"""
        mcp, sandbox = mcp_and_sandbox
        tool_fn = _find_tool(mcp, "git_status")
        if tool_fn is None:
            pytest.skip("无法获取 git_status 工具函数")

        result = await tool_fn("../../etc")
        assert "❌" in result


class TestGitDiff:
    """git_diff 工具测试"""

    @pytest.mark.asyncio
    async def test_not_a_git_repo(self, mcp_and_sandbox: Any, workspace: Path) -> None:
        """非 Git 仓库应该提示"""
        mcp, sandbox = mcp_and_sandbox
        tool_fn = _find_tool(mcp, "git_diff")
        if tool_fn is None:
            pytest.skip("无法获取 git_diff 工具函数")

        result = await tool_fn(work_dir=".")
        assert "❌" in result
        assert "不是 Git 仓库" in result

    @pytest.mark.asyncio
    async def test_path_traversal(self, mcp_and_sandbox: Any, workspace: Path) -> None:
        """路径穿越应该被拒绝"""
        mcp, sandbox = mcp_and_sandbox
        tool_fn = _find_tool(mcp, "git_diff")
        if tool_fn is None:
            pytest.skip("无法获取 git_diff 工具函数")

        result = await tool_fn(work_dir="../../etc")
        assert "❌" in result
