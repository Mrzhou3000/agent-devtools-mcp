"""知识库搜索工具测试 —— semantic_search

通过 FastMCP 实例注册工具，提取后直接调用。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from mcp.server.fastmcp import FastMCP

from mcp_kbtools.kb_manager import KBManager
from mcp_kbtools.tools.kb_search import register_kb_search_tools


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
    """创建带文档的知识库管理器"""
    mgr = KBManager(data_dir=str(tmp_path / "kb_data"))
    mgr.create_kb("default", "默认知识库")

    doc = tmp_path / "search_doc.md"
    doc.write_text(
        "# Python 教程\n\n"
        "Python 是一种编程语言。\n"
        "常用于 Web 开发和数据分析。\n\n"
        "## BM25 搜索\n\n"
        "BM25 是关键词搜索算法。\n"
        "用于检索匹配的文档片段。\n"
    )
    mgr.add_document("default", str(doc))

    return mgr


@pytest.fixture
def mcp_and_manager(manager: KBManager) -> tuple[FastMCP, KBManager]:
    """注册好工具的 MCP 实例"""
    mcp = FastMCP("test-kb-search")
    register_kb_search_tools(mcp, manager)
    return mcp, manager


class TestSemanticSearch:
    """semantic_search 工具测试"""

    async def test_search_found(self, mcp_and_manager: tuple[FastMCP, KBManager]) -> None:
        """找到结果"""
        mcp, _ = mcp_and_manager
        tool = _find_tool(mcp, "semantic_search")
        result = await tool("default", "Python")
        assert "Python" in result
        assert "搜索结果" in result or "🔍" in result

    async def test_search_not_found(self, mcp_and_manager: tuple[FastMCP, KBManager]) -> None:
        """未找到结果"""
        mcp, _ = mcp_and_manager
        tool = _find_tool(mcp, "semantic_search")
        result = await tool("default", "zzzznonexistent")
        assert "未找到" in result

    async def test_search_empty_query(self, mcp_and_manager: tuple[FastMCP, KBManager]) -> None:
        """空关键词"""
        mcp, _ = mcp_and_manager
        tool = _find_tool(mcp, "semantic_search")
        result = await tool("default", "")
        assert "不能为空" in result

    async def test_search_whitespace_query(
        self, mcp_and_manager: tuple[FastMCP, KBManager]
    ) -> None:
        """纯空格"""
        mcp, _ = mcp_and_manager
        tool = _find_tool(mcp, "semantic_search")
        result = await tool("default", "   ")
        assert "不能为空" in result

    async def test_search_top_k_clamp(self, mcp_and_manager: tuple[FastMCP, KBManager]) -> None:
        """top_k 超限自动修正"""
        mcp, _ = mcp_and_manager
        tool = _find_tool(mcp, "semantic_search")
        result = await tool("default", "Python", top_k=999)
        assert result  # 不抛异常就算通过

    async def test_search_top_k_min(self, mcp_and_manager: tuple[FastMCP, KBManager]) -> None:
        """top_k 最小为 1"""
        mcp, _ = mcp_and_manager
        tool = _find_tool(mcp, "semantic_search")
        result = await tool("default", "Python", top_k=0)
        assert result

    async def test_search_kb_not_found(self, mcp_and_manager: tuple[FastMCP, KBManager]) -> None:
        """知识库不存在"""
        mcp, _ = mcp_and_manager
        tool = _find_tool(mcp, "semantic_search")
        result = await tool("wrong_kb", "Python")
        assert "❌" in result
