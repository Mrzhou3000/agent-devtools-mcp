"""mcp-kbtools MCP Server 入口

知识库 MCP Server，提供知识库管理和 BM25 关键词搜索能力。

符合开发规范（DEVELOPMENT_SPECIFICATION.md 5.4 节）:
    - create_kb / list_kbs / delete_kb — 知识库管理
    - add_document / delete_document / list_kb_docs — 文档管理
    - semantic_search — BM25 关键词搜索
"""

from __future__ import annotations

from pathlib import Path

import typer
from mcp.server.fastmcp import FastMCP

from .kb_manager import KBManager

# 创建 CLI 应用
cli = typer.Typer(help="mcp-kbtools: 知识库搜索 MCP Server")


def create_server(data_dir: str, enable_vector: bool = False) -> FastMCP:
    """创建并配置 MCP Server

    Args:
        data_dir: 知识库数据目录（所有 KB 索引存储在此）
        enable_vector: 是否启用向量搜索（需安装 sentence-transformers）
    """
    manager = KBManager(data_dir=data_dir, enable_vector=enable_vector)

    mcp = FastMCP(
        "mcp-kbtools",
        instructions=(
            "知识库 MCP Server —— 知识库管理、文档索引、"
            "BM25 关键词搜索 + 向量语义搜索 + 混合搜索（RRF 融合）"
        ),
    )

    # 注册知识库管理工具（create_kb / list_kbs / delete_kb）
    from .tools.kb_manage import register_kb_manage_tools

    register_kb_manage_tools(mcp, manager)

    # 注册文档管理工具（add_document / delete_document / list_kb_docs）
    from .tools.kb_docs import register_kb_docs_tools

    register_kb_docs_tools(mcp, manager)

    # 注册搜索工具（semantic_search）
    from .tools.kb_search import register_kb_search_tools

    register_kb_search_tools(mcp, manager)

    # 兼容旧版工具（search / list_docs / index_stats）
    # 这些工具使用 "default" 知识库
    from .tools.search_tools import register_search_tools

    register_search_tools(mcp, manager)

    # 把 manager 挂在 server 上（方便测试时获取）
    mcp._manager = manager  # type: ignore[attr-defined]

    return mcp


@cli.command()
def run(
    data_dir: str = typer.Option(
        "kb_data",
        "--data-dir",
        "-d",
        help="知识库数据目录（默认 ./kb_data）",
    ),
    enable_vector: bool = typer.Option(
        False,
        "--enable-vector",
        help="启用语义向量搜索（需安装 sentence-transformers）",
    ),
    host: str = typer.Option(
        "localhost",
        "--host",
        help="监听地址（仅 SSE 模式使用）",
    ),
    port: int = typer.Option(
        8080,
        "--port",
        "-p",
        help="监听端口（仅 SSE 模式使用）",
    ),
    transport: str = typer.Option(
        "stdio",
        "--transport",
        "-t",
        help="传输模式: stdio (本地) 或 sse (网络)",
    ),
) -> None:
    """启动 mcp-kbtools MCP Server"""
    data_path = Path(data_dir).resolve()
    data_path.mkdir(parents=True, exist_ok=True)

    typer.echo("🔧 mcp-kbtools starting...")
    typer.echo(f"  数据目录: {data_path}")
    typer.echo(f"  传输模式: {transport}")
    typer.echo(f"  向量搜索: {'已启用' if enable_vector else '未启用'}")

    server = create_server(
        data_dir=str(data_path),
        enable_vector=enable_vector,
    )

    if transport == "sse":
        typer.echo(f"  监听地址: {host}:{port}")
        server.run(transport="sse")
    else:
        server.run(transport="stdio")


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
