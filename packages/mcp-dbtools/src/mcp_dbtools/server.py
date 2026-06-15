"""mcp-dbtools MCP Server 入口

数据库查询 MCP Server，提供只读 SQL 查询能力。
"""

from __future__ import annotations

from pathlib import Path

import typer
from mcp.server.fastmcp import FastMCP

from .adapters import SQLiteAdapter

# 创建 CLI 应用
cli = typer.Typer(help="mcp-dbtools: 数据库查询 MCP Server")


def create_server(database: str) -> FastMCP:
    """创建并配置 MCP Server

    Args:
        database: SQLite 数据库文件路径
    """
    adapter = SQLiteAdapter(database=database)

    mcp = FastMCP(
        "mcp-dbtools",
        instructions="数据库查询 MCP Server —— 只读 SQL 查询、表结构浏览",
    )

    from .tools.query import register_query_tools

    register_query_tools(mcp, adapter)

    # 把 adapter 挂在 server 上（方便测试时获取）
    mcp._adapter = adapter  # type: ignore[attr-defined]

    return mcp


@cli.command()
def run(
    database: str = typer.Option(
        ...,
        "--database",
        "-d",
        help="SQLite 数据库文件路径",
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
    """启动 mcp-dbtools MCP Server"""
    db_path = Path(database).resolve()
    if not db_path.exists():
        typer.echo(f"❌ 数据库文件不存在: {db_path}", err=True)
        raise typer.Exit(1)

    typer.echo(f"🔧 mcp-dbtools starting...")
    typer.echo(f"  数据库: {db_path}")
    typer.echo(f"  传输模式: {transport}")

    server = create_server(database=str(db_path))

    if transport == "sse":
        typer.echo(f"  监听地址: {host}:{port}")
        server.run(transport="sse")
    else:
        server.run(transport="stdio")


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
