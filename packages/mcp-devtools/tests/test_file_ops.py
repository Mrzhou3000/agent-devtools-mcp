"""文件操作工具测试 —— read_file / write_file"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from mcp.server.fastmcp import FastMCP

from mcp_common.security.sandbox import Sandbox
from mcp_devtools.tools.file_ops import (
    ALLOWED_TEXT_EXTENSIONS,
    validate_file_extension,
    register_file_tools,
)


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    """创建临时工作目录"""
    # 创建一个测试文件
    test_file = tmp_path / "hello.txt"
    test_file.write_text("Hello, World!", encoding="utf-8")

    # 创建一个子目录文件
    sub_dir = tmp_path / "src"
    sub_dir.mkdir()
    sub_file = sub_dir / "server.py"
    sub_file.write_text("print('hello')", encoding="utf-8")

    return tmp_path


@pytest.fixture
def mcp_and_sandbox(workspace: Path) -> tuple[Any, ...]:
    """创建 MCP Server 和 Sandbox 实例"""
    sandbox = Sandbox(workspace_root=str(workspace))
    mcp = FastMCP("test-devtools")
    read_file, write_file = register_file_tools(mcp, sandbox, allow_write=False)
    return mcp, sandbox, read_file, write_file


class TestValidateFileExtension:
    """文件扩展名校验测试"""

    def test_allowed_extensions(self) -> None:
        """所有允许的扩展名应该通过"""
        for ext in ALLOWED_TEXT_EXTENSIONS:
            # 不抛异常就算通过
            validate_file_extension(f"file{ext}")

    def test_disallowed_extensions(self) -> None:
        """不允许的扩展名应该被拒绝"""
        with pytest.raises(ValueError, match="不支持的文件类型"):
            validate_file_extension("file.exe")

        with pytest.raises(ValueError, match="不支持的文件类型"):
            validate_file_extension("file.dll")

        with pytest.raises(ValueError, match="不支持的文件类型"):
            validate_file_extension("file.bin")

        with pytest.raises(ValueError, match="不支持的文件类型"):
            validate_file_extension("file.jpg")

    def test_no_extension(self) -> None:
        """没有扩展名的文件应该被拒绝"""
        with pytest.raises(ValueError, match="不支持的文件类型"):
            validate_file_extension("Makefile")


class TestReadFile:
    """read_file 工具测试"""

    def test_read_existing_file(self, mcp_and_sandbox: Any, workspace: Path) -> None:
        """读取存在的文件应该成功"""
        _, _, read_file, _ = mcp_and_sandbox
        result = read_file("hello.txt")
        assert result == "Hello, World!"

    def test_read_nested_file(self, mcp_and_sandbox: Any, workspace: Path) -> None:
        """读取子目录文件应该成功"""
        _, _, read_file, _ = mcp_and_sandbox
        result = read_file("src/server.py")
        assert result == "print('hello')"

    def test_read_nonexistent_file(self, mcp_and_sandbox: Any, workspace: Path) -> None:
        """读取不存在的文件应该返回友好提示"""
        _, _, read_file, _ = mcp_and_sandbox
        result = read_file("nonexistent.py")
        assert "❌" in result
        assert "文件不存在" in result

    @pytest.mark.security
    def test_read_outside_workspace(self, mcp_and_sandbox: Any, workspace: Path) -> None:
        """读取工作目录外的文件应该被拒绝"""
        _, _, read_file, _ = mcp_and_sandbox
        result = read_file("../../etc/passwd")
        assert "❌" in result
        assert "路径越权" in result

    @pytest.mark.security
    def test_read_path_traversal(self, mcp_and_sandbox: Any, workspace: Path) -> None:
        """路径穿越攻击应该被拒绝"""
        _, _, read_file, _ = mcp_and_sandbox
        result = read_file("src/../../../etc/passwd")
        assert "❌" in result

    @pytest.mark.security
    def test_read_binary_file(self, mcp_and_sandbox: Any, workspace: Path) -> None:
        """读取二进制文件应该被拒绝"""
        _, _, read_file, _ = mcp_and_sandbox
        # 创建一个 .exe 文件
        exe_file = workspace / "test.exe"
        exe_file.write_bytes(b"\x00\x01\x02\x03")
        result = read_file("test.exe")
        assert "❌" in result
        assert "不支持的文件类型" in result


class TestWriteFile:
    """write_file 工具测试"""

    def test_write_disabled_by_default(self, mcp_and_sandbox: Any, workspace: Path) -> None:
        """写入操作默认应该禁用"""
        _, _, read_file, write_file = mcp_and_sandbox
        result = write_file("test.txt", "content")
        assert "❌" in result
        assert "写入操作未启用" in result

    def test_write_enabled(self, workspace: Path) -> None:
        """启用写入后应该可以写入文件"""
        sandbox = Sandbox(workspace_root=str(workspace))
        mcp = FastMCP("test-devtools")
        read_file, write_file = register_file_tools(mcp, sandbox, allow_write=True)

        result = write_file("new_file.txt", "Hello from test!")
        assert "✅" in result
        assert "写入成功" in result

        # 验证文件确实写入了
        assert (workspace / "new_file.txt").read_text() == "Hello from test!"

    def test_write_outside_workspace(self, workspace: Path) -> None:
        """写入到工作目录外应该被拒绝"""
        sandbox = Sandbox(workspace_root=str(workspace))
        mcp = FastMCP("test-devtools")
        read_file, write_file = register_file_tools(mcp, sandbox, allow_write=True)

        result = write_file("../../etc/hacked.txt", "pwned")
        assert "❌" in result

    def test_write_create_parent(self, workspace: Path) -> None:
        """设置 create_parent 后应该创建父目录"""
        sandbox = Sandbox(workspace_root=str(workspace))
        mcp = FastMCP("test-devtools")
        read_file, write_file = register_file_tools(mcp, sandbox, allow_write=True)

        result = write_file("a/b/c/deep_file.txt", "deep", create_parent=True)
        assert "✅" in result
        assert (workspace / "a/b/c/deep_file.txt").read_text() == "deep"

    def test_write_without_parent(self, workspace: Path) -> None:
        """不设置 create_parent 且父目录不存在应该提示"""
        sandbox = Sandbox(workspace_root=str(workspace))
        mcp = FastMCP("test-devtools")
        read_file, write_file = register_file_tools(mcp, sandbox, allow_write=True)

        result = write_file("x/y/no_parent.txt", "content")
        assert "❌" in result
        assert "父目录不存在" in result


class TestReadFileEdgeCases:
    """read_file 边界情况测试"""

    def test_file_too_large(self, workspace: Path) -> None:
        """文件过大应该被拒绝"""
        import mcp_devtools.tools.file_ops as fo

        # 创建大于 MAX_FILE_SIZE 的文件
        large_file = workspace / "large.txt"
        large_file.write_text("x" * (fo.MAX_FILE_SIZE + 1), encoding="utf-8")

        sandbox = Sandbox(workspace_root=str(workspace))
        mcp = FastMCP("test-devtools")
        read_file, _ = register_file_tools(mcp, sandbox, allow_write=False)
        result = read_file("large.txt")
        assert "❌" in result
        assert "文件过大" in result

    def test_read_binary_bytes(self, workspace: Path) -> None:
        """包含非 UTF-8 字节的文件"""
        sandbox = Sandbox(workspace_root=str(workspace))
        mcp = FastMCP("test-devtools")
        read_file, _ = register_file_tools(mcp, sandbox, allow_write=False)

        # 写入包含非 UTF-8 内容的文件
        bin_file = workspace / "bin_data.bin"
        bin_file.write_bytes(b"\xff\xfe\x00Hello\n")  # UTF-16 BOM 但作为文本读
        # 用 .txt 扩展名绕过类型检查，触发解码错误
        txt_file = workspace / "bad_utf8.txt"
        # Python 3.12 默认严格编码，写入一些非法字节
        txt_file.write_bytes(b"Hello\x80World\n\xff\xfetest\n")

        result = read_file("bad_utf8.txt")
        # 不崩就算通过
        assert isinstance(result, str)
        assert "❌" not in result or "文件读取失败" in result


class TestWriteFileEdgeCases:
    """write_file 边界情况测试"""

    def test_write_content_too_large(self, workspace: Path) -> None:
        """写入内容过大应该被拒绝"""
        import mcp_devtools.tools.file_ops as fo

        sandbox = Sandbox(workspace_root=str(workspace))
        mcp = FastMCP("test-devtools")
        _, write_file = register_file_tools(mcp, sandbox, allow_write=True)

        # 写入超过 MAX_WRITE_SIZE 的内容
        large_content = "x" * (fo.MAX_WRITE_SIZE + 1)
        result = write_file("output.txt", large_content)
        assert "❌" in result
        assert "过大" in result or "最大" in result
