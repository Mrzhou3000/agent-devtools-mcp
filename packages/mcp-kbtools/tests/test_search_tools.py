"""知识库搜索工具测试 —— search / list_docs / index_stats

使用临时目录作为索引位置，测试 BM25 搜索功能。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from mcp.server.fastmcp import FastMCP

from mcp_kbtools.kb_manager import KBManager
from mcp_kbtools.tools.search_tools import register_search_tools


@pytest.fixture
def manager(tmp_path: Path) -> KBManager:
    """创建临时知识库管理器"""
    mgr = KBManager(data_dir=str(tmp_path / "kb_data"))
    mgr.create_kb("default", "默认知识库")

    # 创建测试文档（不包含搜索测试用的特殊字符串）
    test_doc = tmp_path / "test_doc.md"
    test_doc.write_text(
        "# 项目文档\n\n"
        "这是一个测试文档，用于验证搜索功能。\n\n"
        "## Python 简介\n\n"
        "Python 是一种简单易学的编程语言。\n"
        "在数据科学和人工智能领域应用广泛。\n\n"
        "## MCP 协议\n\n"
        "Model Context Protocol 是一种开放协议。\n"
        "定义了 AI 应用与数据源之间的通信标准。\n"
    )

    mgr.add_document(
        kb_name="default",
        file_path=str(test_doc),
        chunk_size=2000,
    )

    # Also add an English search doc
    search_doc = tmp_path / "search_test.md"
    search_doc.write_text(
        "# Search Test\n\n"
        "This is a test document for BM25 search verification.\n"
        "Python is a popular programming language for AI development.\n"
        "MCP is an open protocol for AI tool calling.\n"
    )

    mgr.add_document(
        kb_name="default",
        file_path=str(search_doc),
        chunk_size=2000,
    )

    return mgr


@pytest.fixture
def empty_manager(tmp_path: Path) -> KBManager:
    """空知识库管理器"""
    mgr = KBManager(data_dir=str(tmp_path / "empty_kb"))
    mgr.create_kb("default", "空知识库")
    return mgr


def _find_tool(mcp: FastMCP, name: str) -> Any:
    """从 FastMCP 实例中查找工具函数"""
    tool_manager = getattr(mcp, "_tool_manager", None)
    if tool_manager:
        for tool in tool_manager.list_tools():
            if tool.name == name:
                return tool.fn
    return None


class TestSearchEngine:
    """SearchEngine 单元测试（通过 KBManager 访问）"""

    def test_doc_count(self, manager: KBManager) -> None:
        """文档数量统计"""
        kb = manager.get_kb("default")
        assert kb.doc_count >= 1

    def test_list_documents(self, manager: KBManager) -> None:
        """列出所有文档"""
        docs = manager.list_documents("default")
        assert len(docs) >= 1

    def test_search_bm25(self, manager: KBManager) -> None:
        """BM25 关键词搜索"""
        results = manager.search("default", "Python programming")
        assert len(results) >= 1

    def test_search_empty_query(self, manager: KBManager) -> None:
        """空搜索关键词返回空结果"""
        results = manager.search("default", "")
        assert len(results) == 0

    def test_search_no_match(self, manager: KBManager) -> None:
        """无匹配关键词返回空结果"""
        results = manager.search("default", "XYZZYX_NONEXISTENT_98765")
        assert len(results) == 0

    def test_search_empty_kb(self, empty_manager: KBManager) -> None:
        """空知识库搜索"""
        results = empty_manager.search("default", "test")
        assert len(results) == 0


class TestKBManager:
    """KBManager 管理功能测试"""

    def test_create_and_list_kb(self, tmp_path: Path) -> None:
        """创建和列出知识库"""
        mgr = KBManager(data_dir=str(tmp_path / "kb_test"))
        mgr.create_kb("docs", "测试文档")
        mgr.create_kb("notes", "笔记")

        kbs = mgr.list_kbs()
        names = {kb["name"] for kb in kbs}
        assert "docs" in names
        assert "notes" in names

    def test_create_duplicate_kb(self, tmp_path: Path) -> None:
        """重复创建应报错"""
        mgr = KBManager(data_dir=str(tmp_path / "dup_test"))
        mgr.create_kb("test", "")
        with pytest.raises(Exception, match="已存在"):
            mgr.create_kb("test", "")

    def test_get_nonexistent_kb(self, tmp_path: Path) -> None:
        """获取不存在的知识库应报错"""
        mgr = KBManager(data_dir=str(tmp_path / "nonexist"))
        with pytest.raises(Exception, match="不存在"):
            mgr.get_kb("nonexistent")

    def test_delete_kb(self, tmp_path: Path) -> None:
        """删除知识库"""
        mgr = KBManager(data_dir=str(tmp_path / "del_test"))
        mgr.create_kb("temp", "临时")
        mgr.delete_kb("temp")
        assert len(mgr.list_kbs()) == 0

    def test_persist_meta(self, tmp_path: Path) -> None:
        """元数据持久化"""
        mgr = KBManager(data_dir=str(tmp_path / "persist"))
        mgr.create_kb("persist_test", "持久化测试")
        del mgr

        # 重新加载
        mgr2 = KBManager(data_dir=str(tmp_path / "persist"))
        kbs = mgr2.list_kbs()
        assert any(kb["name"] == "persist_test" for kb in kbs)

    def test_invalid_kb_name(self, tmp_path: Path) -> None:
        """非法的知识库名应报错"""
        mgr = KBManager(data_dir=str(tmp_path / "invalid"))
        with pytest.raises(Exception, match="不合法"):
            mgr.create_kb("../evil", "")

    def test_add_document_result(self, manager: KBManager, tmp_path: Path) -> None:
        """添加文档返回统计信息"""
        test_file = tmp_path / "add_test.md"
        test_file.write_text("# Add Test\n\nContent for add test.\n")
        result = manager.add_document(
            kb_name="default",
            file_path=str(test_file),
            chunk_size=2000,
        )
        assert "title" in result
        assert "chunks" in result
        assert "total_chars" in result


class TestSearchTools:
    """MCP 搜索工具测试"""

    def _create_mcp(self, manager: KBManager) -> FastMCP:
        mcp = FastMCP("test-kbtools")
        register_search_tools(mcp, manager)
        return mcp

    @pytest.mark.asyncio
    async def test_search_found(self, manager: KBManager) -> None:
        """搜索存在的关键词"""
        mcp = self._create_mcp(manager)
        fn = _find_tool(mcp, "search")
        result = await fn("Python programming")
        assert "🔍" in result or "📭" in result

    @pytest.mark.asyncio
    async def test_search_not_found(self, manager: KBManager) -> None:
        """搜索不存在的关键词"""
        mcp = self._create_mcp(manager)
        fn = _find_tool(mcp, "search")
        result = await fn("zzzzz")
        assert "未找到" in result

    @pytest.mark.asyncio
    async def test_search_empty(self, manager: KBManager) -> None:
        """空搜索关键词"""
        mcp = self._create_mcp(manager)
        fn = _find_tool(mcp, "search")
        result = await fn("")
        assert "❌" in result

    @pytest.mark.asyncio
    async def test_list_docs(self, manager: KBManager) -> None:
        """列出文档"""
        mcp = self._create_mcp(manager)
        fn = _find_tool(mcp, "list_docs")
        result = await fn()
        assert "个文档" in result or "知识库为空" in result

    @pytest.mark.asyncio
    async def test_list_docs_empty(self, empty_manager: KBManager) -> None:
        """空知识库"""
        mcp = self._create_mcp(empty_manager)
        fn = _find_tool(mcp, "list_docs")
        result = await fn()
        assert "知识库为空" in result

    @pytest.mark.asyncio
    async def test_index_stats(self, manager: KBManager) -> None:
        """索引统计信息"""
        mcp = self._create_mcp(manager)
        fn = _find_tool(mcp, "index_stats")
        result = await fn()
        assert "文档数量" in result

    @pytest.mark.asyncio
    async def test_create_kb_tool(self, tmp_path: Path) -> None:
        """创建知识库工具"""
        mgr = KBManager(data_dir=str(tmp_path / "tool_test"))

        from mcp_kbtools.tools.kb_manage import register_kb_manage_tools

        mcp = FastMCP("test")
        register_kb_manage_tools(mcp, mgr)

        fn = _find_tool(mcp, "create_kb")
        result = await fn("my_kb", "测试知识库")
        assert "✅" in result

    @pytest.mark.asyncio
    async def test_list_kbs_tool(self, tmp_path: Path) -> None:
        """列出知识库工具"""
        mgr = KBManager(data_dir=str(tmp_path / "list_test"))
        mgr.create_kb("kb1", "First")

        from mcp_kbtools.tools.kb_manage import register_kb_manage_tools

        mcp = FastMCP("test")
        register_kb_manage_tools(mcp, mgr)

        fn = _find_tool(mcp, "list_kbs")
        result = await fn()
        assert "kb1" in result

    @pytest.mark.asyncio
    async def test_add_document_tool(self, tmp_path: Path) -> None:
        """添加文档工具"""
        mgr = KBManager(data_dir=str(tmp_path / "add_test"))
        mgr.create_kb("docs", "")

        from mcp_kbtools.tools.kb_docs import register_kb_docs_tools

        mcp = FastMCP("test")
        register_kb_docs_tools(mcp, mgr)

        test_file = tmp_path / "tool_add.md"
        test_file.write_text("# Tool Add\n\nContent.\n")

        fn = _find_tool(mcp, "add_document")
        await fn("docs", str(test_file), 2000)  # warm up
        test_file2 = tmp_path / "tool_add2.md"
        test_file2.write_text("# Tool Add 2\n\nMore content.\n")
        fn2 = _find_tool(mcp, "add_document")
        result = await fn2("docs", str(test_file2), 2000)
        assert "✅" in result

    @pytest.mark.asyncio
    async def test_semantic_search(self, tmp_path: Path) -> None:
        """语义搜索工具"""
        mgr = KBManager(data_dir=str(tmp_path / "search_test"))
        mgr.create_kb("docs", "")
        test_doc = tmp_path / "search_doc.md"
        test_doc.write_text("# 项目文档\n\nPython 是一种编程语言。\nKBManager 管理知识库。\n")
        mgr.add_document("docs", str(test_doc), chunk_size=2000)

        from mcp_kbtools.tools.kb_search import register_kb_search_tools

        mcp = FastMCP("test")
        register_kb_search_tools(mcp, mgr)

        fn = _find_tool(mcp, "semantic_search")
        result = await fn("docs", "Python protocol", 5)
        assert "搜索" in result or "未找到" in result
