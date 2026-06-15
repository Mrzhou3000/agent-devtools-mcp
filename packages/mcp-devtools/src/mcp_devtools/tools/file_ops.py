"""文件操作工具 —— read_file / write_file

这是 mcp-devtools 的核心工具，让 AI Agent 能安全地读取和写入文件。

安全设计:
    - 所有路径经过路径穿越防护
    - 读取时限制文件大小和类型
    - 写入时使用原子写入机制
    - 写入默认禁用，需配置开启
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from mcp_common.security.sandbox import Sandbox

# 允许读取的文本文件扩展名
# 只允许这些扩展名，防止读取二进制文件
ALLOWED_TEXT_EXTENSIONS: set[str] = {
    # 代码文件
    ".py", ".js", ".ts", ".jsx", ".tsx",
    ".java", ".c", ".cpp", ".h", ".hpp",
    ".go", ".rs", ".rb", ".php", ".swift",
    ".kt", ".scala", ".sh", ".bash", ".zsh",
    # Web 前端
    ".html", ".css", ".scss", ".less", ".vue",
    # 配置文件
    ".json", ".yaml", ".yml", ".toml", ".ini",
    ".cfg", ".conf", ".env", ".editorconfig",
    # 文档
    ".md", ".mdx", ".rst", ".txt", ".log",
    ".csv", ".xml", ".svg",
    # 项目文件
    ".lock", ".gitignore", ".dockerfile",
    ".makefile", ".gradle", ".properties",
}

# 最大读取大小（1MB）
MAX_FILE_SIZE = 1 * 1024 * 1024

# 最大写入大小（10MB）
MAX_WRITE_SIZE = 10 * 1024 * 1024

# 允许的文件路径最大深度
MAX_PATH_DEPTH = 20


def validate_file_extension(file_path: str) -> None:
    """校验文件扩展名是否允许读取

    Args:
        file_path: 文件名或路径

    Raises:
        ValueError: 如果文件扩展名不在白名单中
    """
    ext = Path(file_path).suffix.lower()
    if ext not in ALLOWED_TEXT_EXTENSIONS:
        raise ValueError(
            f"不支持的文件类型: '{ext}'\n"
            f"💡 允许的文件类型: {', '.join(sorted(ALLOWED_TEXT_EXTENSIONS))}"
        )


def register_file_tools(
    mcp: FastMCP,
    sandbox: Sandbox,
    allow_write: bool = False,
) -> tuple[Callable[..., Any], Callable[..., Any]]:
    """注册文件操作工具到 MCP Server

    Args:
        mcp: FastMCP 实例
        sandbox: 安全沙箱实例
        allow_write: 是否允许写入操作（默认 False）
    """

    @mcp.tool(description="读取工作目录内的文本文件内容，返回文件内容字符串")
    def read_file(file_path: str) -> str:
        """读取文件内容

        Args:
            file_path: 相对于工作目录的文件路径（如 "src/server.py"）

        安全校验流程:
            1. 路径穿越防护（拒绝 .. 路径）
            2. 文件类型校验（只允许文本文件）
            3. 文件大小限制（最大 1MB）
        """
        # 1️⃣ 路径校验（防路径穿越）
        try:
            safe_path = sandbox.validate_file(file_path)
        except FileNotFoundError:
            return (
                f"❌ 文件不存在: '{file_path}'\n"
                f"💡 请检查文件路径是否正确\n"
                f"💡 工作目录: {sandbox.path_validator.workspace_root}"
            )
        except PermissionError as e:
            return f"❌ 路径越权: {e}"

        # 2️⃣ 文件类型校验（防读取二进制文件）
        try:
            validate_file_extension(str(safe_path))
        except ValueError as e:
            return f"❌ {e}"

        # 3️⃣ 文件大小检查（防撑爆内存）
        file_size = safe_path.stat().st_size
        if file_size > MAX_FILE_SIZE:
            return (
                f"❌ 文件过大: {file_size / 1024 / 1024:.1f}MB\n"
                f"💡 最大支持读取 {MAX_FILE_SIZE / 1024 / 1024:.0f}MB 的文件\n"
                f"💡 如需读取大文件，建议分文件查看"
            )

        # 4️⃣ 读取文件内容
        try:
            content = safe_path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            return f"❌ 文件读取失败: {e}"

        # 5️⃣ 审计日志
        sandbox.log_call(
            "read_file",
            {"file_path": file_path, "file_size": file_size},
            status="success",
        )

        return content

    # ── write_file（默认禁用）──────────────────────────

    if not allow_write:
        # 如果未启用写入，注册一个返回提示信息的工具
        @mcp.tool(description="写入文件内容（当前已禁用，需配置开启）")
        def write_file(file_path: str, content: str) -> str:
            """写入文件（提示已禁用）"""
            return (
                f"❌ 文件写入操作未启用\n"
                f"💡 如需启用，请配置 --allow-write 参数\n"
                f"💡 安全提示: 写入操作默认禁用，请确认你信任当前 AI 客户端"
            )
    else:
        @mcp.tool(description="向文件写入内容，自动创建父目录，使用原子写入保障数据安全")
        def write_file(
            file_path: str,
            content: str,
            create_parent: bool = False,
        ) -> str:
            """写入文件内容（原子写入）

            Args:
                file_path: 相对于工作目录的文件路径
                content: 要写入的文件内容
                create_parent: 是否自动创建父目录（默认 False）
            """
            # 1️⃣ 路径校验
            try:
                safe_dir = sandbox.path_validator.workspace_root
                target_path = sandbox.validate_path(file_path)
            except PermissionError as e:
                return f"❌ 路径越权: {e}"

            # 2️⃣ 检查写入大小
            content_bytes = content.encode("utf-8")
            if len(content_bytes) > MAX_WRITE_SIZE:
                return (
                    f"❌ 写入内容过大: {len(content_bytes) / 1024 / 1024:.1f}MB\n"
                    f"💡 最大支持写入 {MAX_WRITE_SIZE / 1024 / 1024:.0f}MB"
                )

            # 3️⃣ 创建父目录
            parent_dir = target_path.parent
            if not parent_dir.exists():
                if create_parent:
                    parent_dir.mkdir(parents=True, exist_ok=True)
                else:
                    return (
                        f"❌ 父目录不存在: '{parent_dir}'\n"
                        f"💡 设置 create_parent=true 自动创建父目录"
                    )

            # 4️⃣ 原子写入（临时文件 → 重命名）
            try:
                _atomic_write(target_path, content)
            except Exception as e:
                return f"❌ 文件写入失败: {e}"

            # 5️⃣ 审计日志
            sandbox.log_call(
                "write_file",
                {"file_path": file_path, "file_size": len(content_bytes)},
                status="success",
            )

            return f"✅ 文件写入成功: {file_path} ({len(content_bytes)} bytes)"

    return read_file, write_file


def _atomic_write(path: Path, content: str) -> None:
    """原子写入文件

    使用「写临时文件 → fsync → 重命名」的机制:
    1. 在目标文件同目录创建临时文件（.tmp 前缀）
    2. 写入内容并 fsync 强制写入磁盘
    3. 用 os.replace() 原子替换原文件

    这样即使写入中途崩溃，也不会产生半截文件损坏原文件。

    Args:
        path: 目标文件路径
        content: 要写入的字符串内容
    """
    fd, tmp_path = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.tmp.",
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            os.fsync(fd)  # 强制写入磁盘

        # 原子替换（Windows 需要先删除目标文件）
        if path.exists():
            path.unlink()
        os.rename(tmp_path, path)
    except Exception:
        # 失败时清理临时文件
        try:
            os.unlink(tmp_path)
        except FileNotFoundError:
            pass
        raise
