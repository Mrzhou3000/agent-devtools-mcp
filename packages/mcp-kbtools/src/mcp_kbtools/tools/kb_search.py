"""知识库搜索工具 —— semantic_search

根据开发规范（DEVELOPMENT_SPECIFICATION.md 5.4 节）实现。
使用 BM25 关键词搜索（Whoosh 引擎）。
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from ..kb_manager import KBManager, KnowledgeBaseError


def register_kb_search_tools(mcp: FastMCP, manager: KBManager) -> None:
    """注册知识库搜索工具"""

    @mcp.tool(description="在知识库中搜索与查询最相关的文档内容（BM25 关键词搜索）")
    async def semantic_search(
        kb_name: str,
        query: str,
        top_k: int = 5,
    ) -> str:
        """搜索知识库

        Args:
            kb_name: 知识库名称
            query: 搜索关键词
            top_k: 返回结果数量（默认 5，最大 20）
        """
        if not query.strip():
            return "❌ 搜索关键词不能为空"

        # 限制 top_k
        top_k = min(max(1, top_k), 20)

        try:
            results = manager.search(kb_name, query, top_k=top_k)
        except KnowledgeBaseError as e:
            return f"❌ {e}"
        except Exception as e:
            return f"❌ 搜索失败: {e}"

        if not results:
            return (
                f"📭 在知识库 '{kb_name}' 中未找到匹配 '{query}' 的结果\n"
                f"💡 试试其他关键词，或使用 add_document 添加更多文档"
            )

        # 解析路径，提取文件名和行号
        lines = [
            f"🔍 搜索 '{query}' 在 '{kb_name}' 中共找到 "
            f"{len(results)} 条结果\n"
        ]
        for i, r in enumerate(results, 1):
            # 解析路径如 "README.md#L10" → 文件名:行号
            location = r.path.replace("#L", " 第 ").replace("L", " 第 ")
            lines.append(f"  [{i}] {r.title}")
            lines.append(f"      位置: {location}")
            lines.append(f"      相关度: {r.score:.2f}")
            if r.highlights:
                lines.append(f"      摘要: {r.highlights}")
            lines.append("")

        return "\n".join(lines).strip()
