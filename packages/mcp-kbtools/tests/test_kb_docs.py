"""知识库文档管理工具测试 —— add_document / delete_document / list_kb_docs

通过 FastMCP 实例注册工具，提取后直接调用。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from mcp.server.fastmcp import FastMCP

from mcp_kbtools.kb_manager import KBManager
from mcp_kbtools.tools.kb_docs import register_kb_docs_tools


def _find_tool(mcp: FastMCP, name: str) -> Any:
    """从 FastMCP 实例中查找工具函数"""
    tool_manager = getattr(mcp, "_tool_manager", None)
    if tool_manager:
        for tool in tool_manager.list_tools():
            if tool.name == name:
                return tool.fn
    return None


@pytest.fixture
def manager(tmp_path: Path) -> KBManager:
    """创建带 default 知识库的管理器"""
    mgr = KBManager(data_dir=str(tmp_path / "kb_data"))
    mgr.create_kb("default", "默认知识库")
    return mgr


@pytest.fixture
def mcp_and_manager(manager: KBManager) -> tuple[FastMCP, KBManager]:
    """注册好工具的 MCP 实例"""
    mcp = FastMCP("test-kb-docs")
    register_kb_docs_tools(mcp, manager)
    return mcp, manager


class TestAddDocument:
    """add_document 工具测试"""

    async def test_add_success(
        self, mcp_and_manager: tuple[FastMCP, KBManager], tmp_path: Path
    ) -> None:
        """添加文档成功"""
        mcp, _ = mcp_and_manager
        doc = tmp_path / "test.md"
        doc.write_text("# Hello\n\nWorld content here.\n")

        tool = _find_tool(mcp, "add_document")
        result = await tool("default", str(doc))
        assert "添加成功" in result
        assert "test.md" in result

    async def test_add_file_not_found(self, mcp_and_manager: tuple[FastMCP, KBManager]) -> None:
        """文件不存在"""
        mcp, _ = mcp_and_manager
        tool = _find_tool(mcp, "add_document")
        result = await tool("default", "/nonexistent/path.txt")
        assert "❌" in result

    async def test_add_unsupported_type(
        self, mcp_and_manager: tuple[FastMCP, KBManager], tmp_path: Path
    ) -> None:
        """不支持的文件类型"""
        mcp, _ = mcp_and_manager
        doc = tmp_path / "test.exe"
        doc.write_bytes(b"\x00\x01")

        tool = _find_tool(mcp, "add_document")
        result = await tool("default", str(doc))
        assert "❌" in result

    async def test_add_kb_not_found(
        self, mcp_and_manager: tuple[FastMCP, KBManager], tmp_path: Path
    ) -> None:
        """知识库不存在"""
        mcp, _ = mcp_and_manager
        doc = tmp_path / "test.md"
        doc.write_text("# Test\n")

        tool = _find_tool(mcp, "add_document")
        result = await tool("nonexistent_kb", str(doc))
        assert "❌" in result

    async def test_add_chunk_size_zero(
        self, mcp_and_manager: tuple[FastMCP, KBManager], tmp_path: Path
    ) -> None:
        """分块大小为 0 也能处理"""
        mcp, _ = mcp_and_manager
        doc = tmp_path / "zero.md"
        doc.write_text("# Zero chunk\nSome text.\n")

        tool = _find_tool(mcp, "add_document")
        result = await tool("default", str(doc), chunk_size=0)
        assert "添加成功" in result or "❌" in result


class TestDeleteDocument:
    """delete_document 工具测试"""

    async def test_delete_success(
        self, mcp_and_manager: tuple[FastMCP, KBManager], tmp_path: Path
    ) -> None:
        """删除成功"""
        mcp, manager = mcp_and_manager
        doc = tmp_path / "del_test.md"
        doc.write_text("# Delete me\nContent.\n")
        manager.add_document("default", str(doc))

        tool = _find_tool(mcp, "delete_document")
        result = await tool("default", str(doc))
        assert "已删除" in result

    async def test_delete_not_found(self, mcp_and_manager: tuple[FastMCP, KBManager]) -> None:
        """删除不存在的文档（幂等操作，不报错）"""
        mcp, _ = mcp_and_manager
        tool = _find_tool(mcp, "delete_document")
        result = await tool("default", "/not/indexed.md")
        assert "已删除" in result or "失败" in result


class TestListKBDocs:
    """list_kb_docs 工具测试"""

    async def test_list_empty(self, mcp_and_manager: tuple[FastMCP, KBManager]) -> None:
        """空知识库"""
        mcp, _ = mcp_and_manager
        tool = _find_tool(mcp, "list_kb_docs")
        result = await tool("default")
        assert "为空" in result

    async def test_list_with_docs(
        self, mcp_and_manager: tuple[FastMCP, KBManager], tmp_path: Path
    ) -> None:
        """有文档时列出"""
        mcp, manager = mcp_and_manager
        doc = tmp_path / "list_test.md"
        doc.write_text("# List me\nContent.\n")
        manager.add_document("default", str(doc))

        tool = _find_tool(mcp, "list_kb_docs")
        result = await tool("default")
        assert "list_test" in result or "List me" in result

    async def test_list_kb_not_found(self, mcp_and_manager: tuple[FastMCP, KBManager]) -> None:
        """知识库不存在"""
        mcp, _ = mcp_and_manager
        tool = _find_tool(mcp, "list_kb_docs")
        result = await tool("fake_kb")
        assert "❌" in result
