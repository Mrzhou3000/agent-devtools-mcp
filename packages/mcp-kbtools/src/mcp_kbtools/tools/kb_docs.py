"""知识库文档工具 —— add_document / delete_document

根据开发规范（DEVELOPMENT_SPECIFICATION.md 5.4 节）实现。

处理流程:
    1. 自动从文件系统加载文档
    2. 按段落/代码逻辑分块
    3. 建立 BM25 索引
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from ..ingestion.loader import UnsupportedFileTypeError
from ..kb_manager import KBManager, KnowledgeBaseError


def register_kb_docs_tools(mcp: FastMCP, manager: KBManager) -> None:
    """注册知识库文档管理工具"""

    @mcp.tool(description="向知识库中添加一个文档文件，自动分块并建立索引")
    async def add_document(
        kb_name: str,
        file_path: str,
        chunk_size: int = 500,
    ) -> str:
        """添加文档到知识库

        支持的格式: .md .txt .py .js .ts .json .yaml .html .css 等文本文件

        Args:
            kb_name: 知识库名称
            file_path: 文档文件路径（支持绝对路径或相对路径）
            chunk_size: 分块大小（字符数，默认 500）
        """
        try:
            result = manager.add_document(
                kb_name=kb_name,
                file_path=file_path,
                chunk_size=chunk_size,
                chunk_overlap=chunk_size // 10,
            )
            size_kb = result["total_chars"] / 1024
            return (
                f"✅ 文档添加成功\n"
                f"  📄 文件: {result['file_path']}\n"
                f"  🏷️  标题: {result['title']}\n"
                f"  📦 分块: {result['chunks']} 个\n"
                f"  📏 大小: {size_kb:.1f}KB"
            )
        except FileNotFoundError as e:
            return f"❌ 文件不存在: {e}"
        except UnsupportedFileTypeError as e:
            return f"❌ {e}"
        except KnowledgeBaseError as e:
            return f"❌ {e}"
        except Exception as e:
            return f"❌ 添加文档失败: {e}"

    @mcp.tool(description="从知识库中删除一个文档及其所有索引")
    async def delete_document(
        kb_name: str,
        doc_path: str,
    ) -> str:
        """删除知识库中的文档

        Args:
            kb_name: 知识库名称
            doc_path: 文档路径（添加时使用的路径）
        """
        try:
            manager.delete_document(kb_name, doc_path)
            return f"✅ 文档已删除: {doc_path}"
        except KnowledgeBaseError as e:
            return f"❌ 删除失败: {e}"

    @mcp.tool(description="列出知识库中所有已索引的文档")
    async def list_kb_docs(kb_name: str) -> str:
        """列出知识库中的文档

        Args:
            kb_name: 知识库名称
        """
        try:
            docs = manager.list_documents(kb_name)
        except KnowledgeBaseError as e:
            return f"❌ {e}"

        if not docs:
            return f"📭 知识库 '{kb_name}' 为空\n💡 使用 add_document 添加文档"

        total_size = sum(d.size for d in docs)
        lines = [f"📚 知识库 '{kb_name}' - {len(docs)} 个文档（总计 {total_size / 1024:.1f}KB）\n"]
        for d in docs:
            size_str = f"{d.size / 1024:.1f}KB" if d.size > 1024 else f"{d.size}B"
            lines.append(f"  📄 {d.title}")
            lines.append(f"      路径: {d.path}")
            lines.append(f"      大小: {size_str}")
            lines.append("")

        return "\n".join(lines).strip()
