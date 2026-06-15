"""文档加载器 —— 支持从文件系统加载多种格式的文档

支持的格式:
- .md / .markdown — Markdown 文件
- .txt — 纯文本文件
- .py / .js / .ts / .java / .rs / .go / .c / .h — 代码文件
- .json / .yaml / .yml / .toml — 配置文件
- .html / .css — Web 文件

用法:
    from mcp_kbtools.ingestion.loader import load_document

    doc = load_document("README.md")
    print(doc.title)     # "README.md"
    print(doc.content)   # 文件内容
    print(doc.meta)      # 元数据（大小、行数等）
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# 支持的文本文件扩展名
TEXT_EXTENSIONS: set[str] = {
    # 文档
    ".md", ".markdown", ".rst", ".txt",
    # 代码
    ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".rs", ".go",
    ".c", ".h", ".cpp", ".hpp", ".rb", ".php", ".swift", ".kt",
    ".scala", ".lua", ".sh", ".bash", ".zsh", ".ps1",
    # Web
    ".html", ".htm", ".css", ".scss", ".less", ".vue", ".svelte",
    # 配置
    ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf",
    ".xml", ".svg",
    # 其他
    ".sql", ".graphql", ".proto", ".dockerfile",
}

# 二进制文件扩展名（明确拒绝）
BINARY_EXTENSIONS: set[str] = {
    ".exe", ".dll", ".so", ".dylib", ".bin", ".dat",
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".webp",
    ".mp3", ".mp4", ".avi", ".mov", ".wav", ".flac",
    ".zip", ".tar", ".gz", ".bz2", ".7z", ".rar",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".pyc", ".pyo", ".pyd",
    ".ttf", ".otf", ".woff", ".woff2",
    ".o", ".a", ".lib", ".obj",
}


@dataclass
class LoadedDocument:
    """加载的文档

    Attributes:
        path: 文档路径（相对于知识库根目录）
        title: 文档标题（默认使用文件名）
        content: 文档内容
        meta: 元数据（大小、行数、扩展名等）
    """
    path: str
    title: str
    content: str
    meta: dict[str, Any] = field(default_factory=dict)


class UnsupportedFileTypeError(ValueError):
    """不支持的文件类型"""

    def __init__(self, extension: str, path: str = ""):
        self.extension = extension
        self.path = path
        ext_list = ", ".join(sorted(TEXT_EXTENSIONS))
        super().__init__(
            f"不支持的文件类型 '{extension}'。"
            f" 支持的格式: {ext_list}"
        )


def load_document(file_path: str | Path) -> LoadedDocument:
    """加载一个文档文件

    Args:
        file_path: 文件路径

    Returns:
        加载的文档对象

    Raises:
        FileNotFoundError: 文件不存在
        UnsupportedFileTypeError: 不支持的文件类型
    """
    path = Path(file_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {path}")

    suffix = path.suffix.lower()
    if suffix not in TEXT_EXTENSIONS:
        raise UnsupportedFileTypeError(suffix, str(path))

    content = path.read_text(encoding="utf-8", errors="replace")
    lines = content.splitlines()

    # 自动生成标题
    title = _infer_title(content, path)

    # 收集元数据
    meta: dict[str, Any] = {
        "file_name": path.name,
        "extension": suffix,
        "size": len(content),
        "size_kb": round(len(content) / 1024, 1),
        "lines": len(lines),
        "modified_at": path.stat().st_mtime,
    }

    return LoadedDocument(
        path=str(path),
        title=title,
        content=content,
        meta=meta,
    )


def _infer_title(content: str, path: Path) -> str:
    """从文件中推断标题

    优先级:
    1. Markdown 的第一个 H1 标题
    2. Python 的模块 docstring
    3. 文件名（不含扩展名）
    """
    # 尝试 Markdown H1
    h1_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    if h1_match:
        return h1_match.group(1).strip()

    # 尝试 Python docstring
    doc_match = re.search(r'^("{3}|\'{3})\s*(.+?)\s*\1', content, re.DOTALL)
    if doc_match:
        return doc_match.group(2).split("\n")[0].strip()

    # 尝试 // 注释标题（代码文件）
    comment_match = re.search(r"^//\s*(.+?)$", content, re.MULTILINE)
    if comment_match:
        return comment_match.group(1).strip()

    # 使用文件名
    return path.stem


def is_supported_file(file_path: str | Path) -> bool:
    """检查文件类型是否被支持"""
    return Path(file_path).suffix.lower() in TEXT_EXTENSIONS
