"""文档处理模块 —— 加载、分块"""

from .loader import (
    TEXT_EXTENSIONS,
    LoadedDocument,
    UnsupportedFileTypeError,
    is_supported_file,
    load_document,
)
from .splitter import (
    DocumentChunk,
    split_document,
    split_text,
)

__all__ = [
    "load_document",
    "is_supported_file",
    "LoadedDocument",
    "UnsupportedFileTypeError",
    "TEXT_EXTENSIONS",
    "split_text",
    "split_document",
    "DocumentChunk",
]
