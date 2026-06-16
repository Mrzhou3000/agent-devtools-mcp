"""知识库管理工具测试 —— create_kb / list_kbs / delete_kb

测试通过 FastMCP 实例注册工具，再提取并调用。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from mcp.server.fastmcp import FastMCP

from mcp_kbtools.kb_manager import KBManager
from mcp_kbtools.tools.kb_manage import register_kb_manage_tools


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
    """创建临时知识库管理器"""
    return KBManager(data_dir=str(tmp_path / "kb_data"))


@pytest.fixture
def mcp_and_manager(manager: KBManager) -> tuple[FastMCP, KBManager]:
    """注册好工具的 MCP 实例"""
    mcp = FastMCP("test-kb-manage")
    register_kb_manage_tools(mcp, manager)
    return mcp, manager


class TestCreateKB:
    """create_kb 工具测试"""

    async def test_create_success(self, mcp_and_manager: tuple[FastMCP, KBManager]) -> None:
        """创建知识库成功"""
        mcp, _ = mcp_and_manager
        tool = _find_tool(mcp, "create_kb")
        assert tool is not None
        result = await tool("test_kb", "测试知识库")
        assert "创建成功" in result
        assert "test_kb" in result

    async def test_create_duplicate(self, mcp_and_manager: tuple[FastMCP, KBManager]) -> None:
        """重复创建应报错"""
        mcp, manager = mcp_and_manager
        manager.create_kb("dup_kb")
        tool = _find_tool(mcp, "create_kb")
        result = await tool("dup_kb")
        assert "❌" in result

    async def test_create_invalid_name(self, mcp_and_manager: tuple[FastMCP, KBManager]) -> None:
        """非法名称应报错"""
        mcp, _ = mcp_and_manager
        tool = _find_tool(mcp, "create_kb")
        result = await tool("../invalid", "穿越路径")
        assert "❌" in result


class TestListKBs:
    """list_kbs 工具测试"""

    async def test_list_empty(self, mcp_and_manager: tuple[FastMCP, KBManager]) -> None:
        """空列表"""
        mcp, _ = mcp_and_manager
        tool = _find_tool(mcp, "list_kbs")
        result = await tool()
        assert "暂无" in result

    async def test_list_with_kbs(self, mcp_and_manager: tuple[FastMCP, KBManager]) -> None:
        """有知识库时列出来"""
        mcp, manager = mcp_and_manager
        manager.create_kb("kb_a", "知识库A")
        manager.create_kb("kb_b")
        tool = _find_tool(mcp, "list_kbs")
        result = await tool()
        assert "kb_a" in result
        assert "kb_b" in result
        assert "2 个" in result


class TestDeleteKB:
    """delete_kb 工具测试"""

    async def test_delete_success(self, mcp_and_manager: tuple[FastMCP, KBManager]) -> None:
        """删除成功"""
        mcp, manager = mcp_and_manager
        manager.create_kb("to_delete")
        tool = _find_tool(mcp, "delete_kb")
        result = await tool("to_delete")
        assert "已删除" in result
        kbs = manager.list_kbs()
        assert len(kbs) == 0

    async def test_delete_not_found(self, mcp_and_manager: tuple[FastMCP, KBManager]) -> None:
        """删除不存在的知识库"""
        mcp, _ = mcp_and_manager
        tool = _find_tool(mcp, "delete_kb")
        result = await tool("nonexistent")
        assert "❌" in result
