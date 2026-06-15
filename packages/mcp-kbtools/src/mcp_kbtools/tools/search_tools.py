"""知识库搜索工具（旧版兼容）—— search / list_docs / index_stats

兼容旧版 API：操作默认的 "default" 知识库。
新用户推荐使用 create_kb / add_document / semantic_search 系列工具。
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from ..kb_manager import KBManager

# 旧版兼容使用的默认知识库名
DEFAULT_KB_NAME = "default"


def _ensure_default_kb(manager: KBManager) -> str:
    """确保默认知识库存在"""
    try:
        manager.get_kb(DEFAULT_KB_NAME)
    except Exception:
        manager.create_kb(DEFAULT_KB_NAME, "默认知识库（旧版兼容）")
    return DEFAULT_KB_NAME


def register_search_tools(
    mcp: FastMCP,
    manager: KBManager,
) -> None:
    """注册搜索工具到 MCP Server（旧版兼容）"""

    @mcp.tool(description="对知识库进行关键词搜索，返回匹配的文档片段及出处")
    async def search(
        query: str,
        limit: int = 10,
    ) -> str:
        """搜索知识库

        Args:
            query: 搜索关键词
            limit: 返回结果数量上限（默认 10）
        """
        if not query.strip():
            return "❌ 搜索关键词不能为空"

        try:
            kb_name = _ensure_default_kb(manager)
            results = manager.search(kb_name, query, top_k=limit)
        except Exception as e:
            return f"❌ 搜索失败: {e}"

        if not results:
            return (
                f"📭 未找到匹配 '{query}' 的结果\n"
                f"💡 试试其他关键词，或先使用 add_document 添加文档"
            )

        lines = [f"🔍 搜索 '{query}' 共找到 {len(results)} 条结果\n"]
        for i, r in enumerate(results, 1):
            lines.append(f"  [{i}] {r.title}")
            lines.append(f"      来源: {r.path}")
            lines.append(f"      相关度: {r.score:.2f}")
            if r.highlights:
                lines.append(f"      摘要: {r.highlights}")
            lines.append("")

        return "\n".join(lines).strip()

    @mcp.tool(description="列出知识库中所有已索引的文档")
    async def list_docs() -> str:
        """列出所有已索引文档"""
        try:
            kb_name = _ensure_default_kb(manager)
            docs = manager.list_documents(kb_name)
        except Exception as e:
            return f"❌ 获取文档列表失败: {e}"

        if not docs:
            return "📭 知识库为空，请先使用 add_document 添加文档"

        total_size = sum(d.size for d in docs)
        lines = [f"📚 共 {len(docs)} 个文档（总计 {total_size / 1024:.1f}KB）\n"]
        for d in docs:
            size_str = f"{d.size / 1024:.1f}KB" if d.size > 1024 else f"{d.size}B"
            lines.append(f"  📄 {d.title}")
            lines.append(f"      路径: {d.path}")
            lines.append(f"      大小: {size_str}")
            lines.append("")

        return "\n".join(lines).strip()

    @mcp.tool(description="查看知识库索引的统计信息（文档数、索引位置等）")
    async def index_stats() -> str:
        """查看知识库统计信息"""
        try:
            kb_name = _ensure_default_kb(manager)
            kb = manager.get_kb(kb_name)
            index_dir = kb.index_dir
        except Exception as e:
            return f"❌ 获取统计信息失败: {e}"

        total_size = sum(
            f.stat().st_size for f in index_dir.rglob("*") if f.is_file()
        )

        return (
            f"📊 知识库统计\n"
            f"  ────────────\n"
            f"  文档数量: {kb.doc_count}\n"
            f"  索引路径: {index_dir.resolve()}\n"
            f"  索引大小: {total_size / 1024:.1f}KB\n"
        )
