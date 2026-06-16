"""mcp-devtools MCP Server 入口

这是 devtools 模块的主入口，负责:
1. 初始化 MCP Server（注册所有工具）
2. 配置安全沙箱
3. 提供 CLI 启动命令

启动方式:
    uv run python -m mcp_devtools
"""

from __future__ import annotations

from pathlib import Path

import typer
from mcp.server.fastmcp import FastMCP

from mcp_common.security.sandbox import Sandbox

# 创建 CLI 应用（用于启动 Server）
cli = typer.Typer(help="mcp-devtools: 开发工具 MCP Server")


def create_server(workspace_root: str, allow_write: bool = False) -> FastMCP:
    """创建并配置 MCP Server

    这是核心工厂函数，所有工具在这里注册。

    Args:
        workspace_root: 工作目录路径（所有文件操作限制在此目录内）
        allow_write: 是否允许写入操作（默认 False，安全考虑）

    Returns:
        配置好的 FastMCP 实例
    """
    # 初始化安全沙箱（三层防御）
    sandbox = Sandbox(workspace_root=workspace_root)

    # 创建 MCP Server
    mcp = FastMCP(
        "mcp-devtools",
        instructions="开发工具 MCP Server —— 文件读写、命令执行、Git 查询",
    )

    # ════════════════════════════════════════════════
    # 注册工具
    # ════════════════════════════════════════════════

    # 注册文件操作工具（read_file / write_file）
    from .tools.file_ops import register_file_tools

    register_file_tools(mcp, sandbox, allow_write)

    # 注册命令执行工具（run_command / git_status / git_diff）
    from .tools.command_ops import register_command_tools

    register_command_tools(mcp, sandbox)

    return mcp


@cli.command()
def run(
    workspace: str = typer.Option(
        ".",
        "--workspace",
        "-w",
        help="工作目录路径（所有文件操作限制在此目录内）",
    ),
    allow_write: bool = typer.Option(
        False,
        "--allow-write",
        help="启用写入操作（默认禁用，安全考虑）",
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
    """启动 mcp-devtools MCP Server

    默认以 stdio 模式运行（用于 Claude Desktop 等本地客户端）。
    也可用 sse 模式运行（用于远端服务调用）。
    """
    workspace_path = Path(workspace).resolve()
    if not workspace_path.exists():
        typer.echo(f"❌ 工作目录不存在: {workspace_path}", err=True)
        raise typer.Exit(1)

    typer.echo("🔧 mcp-devtools starting...")
    typer.echo(f"  工作目录: {workspace_path}")
    typer.echo(f"  允许写入: {allow_write}")
    typer.echo(f"  传输模式: {transport}")

    server = create_server(
        workspace_root=str(workspace_path),
        allow_write=allow_write,
    )

    if transport == "sse":
        typer.echo(f"  监听地址: {host}:{port}")
        server.run(transport="sse")
    else:
        server.run(transport="stdio")


def main() -> None:
    """入口函数"""
    cli()


if __name__ == "__main__":
    main()
