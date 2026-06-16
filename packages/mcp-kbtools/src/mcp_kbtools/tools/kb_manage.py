"""知识库管理工具 —— create_kb / list_kbs / delete_kb

根据开发规范（DEVELOPMENT_SPECIFICATION.md 5.4 节）实现。
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from ..kb_manager import KBManager, KnowledgeBaseError


def register_kb_manage_tools(mcp: FastMCP, manager: KBManager) -> None:
    """注册知识库管理工具"""

    @mcp.tool(description="创建一个新的知识库，用于存储和检索文档")
    async def create_kb(
        name: str,
        description: str = "",
    ) -> str:
        """创建知识库

        Args:
            name: 知识库名称（字母数字下划线）
            description: 知识库描述（可选）
        """
        try:
            manager.create_kb(name, description)
            return (
                f"✅ 知识库创建成功: '{name}'\n"
                f"💡 描述: {description or '无'}\n"
                f"💡 下一步: 使用 add_document 添加文档"
            )
        except KnowledgeBaseError as e:
            return f"❌ 创建失败: {e}"

    @mcp.tool(description="列出所有已创建的知识库及其文档数量")
    async def list_kbs() -> str:
        """列出所有知识库"""
        kbs = manager.list_kbs()

        if not kbs:
            return "📭 暂无知识库\n💡 使用 create_kb 创建一个新的知识库"

        lines = [f"📚 共 {len(kbs)} 个知识库\n"]
        for kb in kbs:
            doc_str = f"{kb['doc_count']} 个文档" if kb["doc_count"] > 0 else "空"
            lines.append(f"  📂 {kb['name']}")
            lines.append(f"     描述: {kb['description'] or '无'}")
            lines.append(f"     文档: {doc_str}")
            lines.append("")

        return "\n".join(lines).strip()

    @mcp.tool(description="删除一个知识库及其所有索引数据（不可恢复）")
    async def delete_kb(name: str) -> str:
        """删除知识库

        Args:
            name: 知识库名称
        """
        try:
            manager.delete_kb(name)
            return f"✅ 知识库 '{name}' 已删除"
        except KnowledgeBaseError as e:
            return f"❌ 删除失败: {e}"
