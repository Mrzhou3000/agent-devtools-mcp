"""知识库搜索工具 —— semantic_search 支持 BM25 / 向量 / 混合搜索

根据开发规范（DEVELOPMENT_SPECIFICATION.md 5.4 节）实现。
提供三种搜索模式:
    - bm25:   纯 BM25 关键词搜索（Whoosh）
    - vector: 纯语义向量搜索（sentence-transformers）
    - hybrid: RRF 混合搜索（默认推荐）
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from ..kb_manager import KBManager, KnowledgeBaseError


def register_kb_search_tools(mcp: FastMCP, manager: KBManager) -> None:
    """注册知识库搜索工具"""

    @mcp.tool(
        description=(
            "在知识库中搜索与查询最相关的文档内容。"
            "支持三种搜索模式: bm25（关键词）、vector（语义）、hybrid（混合，推荐）"
        )
    )
    async def semantic_search(
        kb_name: str,
        query: str,
        top_k: int = 5,
        search_mode: str = "hybrid",
    ) -> str:
        """搜索知识库

        Args:
            kb_name: 知识库名称
            query: 搜索关键词
            top_k: 返回结果数量（默认 5，最大 20）
            search_mode: 搜索模式
                - "bm25":   纯 BM25 关键词搜索（Whoosh 引擎）
                - "vector": 纯语义向量搜索（sentence-transformers）
                - "hybrid": RRF 混合搜索（默认推荐，融合 BM25 + 向量）
        """
        if not query.strip():
            return "❌ 搜索关键词不能为空"

        # 校验搜索模式
        valid_modes = {"bm25", "vector", "hybrid"}
        if search_mode not in valid_modes:
            return (
                f"❌ 不支持的搜索模式: '{search_mode}'\n"
                f"💡 可选模式: {', '.join(sorted(valid_modes))}"
            )

        # 限制 top_k
        top_k = min(max(1, top_k), 20)

        try:
            results = manager.search(kb_name, query, top_k=top_k, mode=search_mode)
        except KnowledgeBaseError as e:
            return f"❌ {e}"
        except Exception as e:
            return f"❌ 搜索失败: {e}"

        if not results:
            mode_hint = {
                "bm25": "试试其他关键词",
                "vector": (
                    "向量搜索无结果。可能原因:\n"
                    "  - 未安装 sentence-transformers（安装: uv sync --extra vector）\n"
                    "  - 知识库中没有文档\n"
                    "  💡 试试 search_mode='bm25' 使用关键词搜索"
                ),
                "hybrid": (
                    "混合搜索无结果。试试其他关键词，\n" "或安装 sentence-transformers 启用语义搜索"
                ),
            }
            return (
                f"📭 在知识库 '{kb_name}' 中使用 '{search_mode}' 模式"
                f"未找到匹配 '{query}' 的结果\n"
                f"💡 {mode_hint.get(search_mode, '试试其他关键词')}"
            )

        mode_labels = {
            "bm25": "BM25 关键词",
            "vector": "语义向量",
            "hybrid": "混合 (BM25 + 向量)",
        }
        label = mode_labels.get(search_mode, search_mode)

        # 解析路径，提取文件名和行号
        lines = [
            f"🔍 搜索 '{query}' 在 '{kb_name}' 中" f"（{label}模式，共 {len(results)} 条结果）\n"
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

    @mcp.tool(description="查询知识库当前已启用的搜索能力（BM25 / 向量 / 混合）")
    async def get_search_capabilities(kb_name: str) -> str:
        """查询知识库的搜索能力

        Args:
            kb_name: 知识库名称
        """
        try:
            kb = manager.get_kb(kb_name)
        except KnowledgeBaseError as e:
            return f"❌ {e}"

        lines = [f"🔧 知识库 '{kb_name}' 搜索能力\n"]

        # BM25 总是可用
        lines.append("  ✅ BM25 关键词搜索（Whoosh）")
        lines.append("     始终可用，无需额外安装")

        # 向量搜索
        if kb.vector_available:
            lines.append("  ✅ 语义向量搜索（sentence-transformers）")
            lines.append(f"     已就绪，文档数: {kb.vector_engine.doc_count}")  # type: ignore[union-attr]
        else:
            lines.append("  ❌ 语义向量搜索（sentence-transformers）")
            lines.append("     未安装或未启用")
            lines.append("     💡 安装: uv sync --extra vector")
            lines.append("     💡 或在启动时添加 --enable-vector 参数")

        # 推荐模式
        lines.append("")
        lines.append("💡 推荐: search_mode='hybrid'（混合模式）")
        lines.append("   融合 BM25 关键词 + 语义向量，兼顾精度和召回")

        return "\n".join(lines).strip()
