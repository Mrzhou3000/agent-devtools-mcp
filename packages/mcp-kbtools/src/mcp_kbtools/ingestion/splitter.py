"""文本分块器 —— 将长文档切分成适合搜索的块

分块策略:
1. 优先按段落分割（连续空行分隔）
2. 每个块大小控制在 chunk_size 字符左右
3. 相邻块有 overlap 字符的重叠（保持上下文连贯）
4. 代码文件按函数/类定义分割

用法:
    from mcp_kbtools.ingestion.splitter import split_text, split_document

    # 直接切文本
    chunks = split_text(content, chunk_size=500, overlap=50)

    # 切 LoadedDocument
    chunks = split_document(loaded_doc, chunk_size=500, overlap=50)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class DocumentChunk:
    """文档块

    Attributes:
        path: 源文档路径
        title: 源文档标题
        content: 块内容
        chunk_index: 块序号（从 0 开始）
        start_line: 在源文档中的起始行号
        end_line: 在源文档中的结束行号
        meta: 额外元数据
    """

    path: str
    title: str
    content: str
    chunk_index: int = 0
    start_line: int = 0
    end_line: int = 0
    meta: dict[str, Any] = field(default_factory=dict)


# ── 预处理 ────────────────────────────────────────────────────


def preprocess_content(content: str) -> str:
    """预处理文本内容

    1. 移除多余空行（最多保留一个空行）
    2. 移除行尾空白
    3. 统一换行符为 \n
    """
    # 统一换行符
    text = content.replace("\r\n", "\n").replace("\r", "\n")
    # 移除多余空行（最多保留两个连续换行 = 一个空行）
    text = re.sub(r"\n{3,}", "\n\n", text)
    # 行尾去空格
    lines = [line.rstrip() for line in text.split("\n")]
    return "\n".join(lines).strip()


# ── 段落分割 ──────────────────────────────────────────────────


def split_by_paragraphs(content: str) -> list[dict[str, Any]]:
    """按段落分割文本

    Returns:
        list of {text, start_line, end_line}
    """
    lines = content.split("\n")
    paragraphs: list[dict[str, Any]] = []
    current_lines: list[str] = []
    current_start = 0

    for i, line in enumerate(lines):
        if line.strip() == "" and current_lines:
            # 空行结束一个段落
            paragraphs.append(
                {
                    "text": "\n".join(current_lines),
                    "start_line": current_start,
                    "end_line": i - 1,
                }
            )
            current_lines = []
            current_start = i + 1
        elif line.strip() != "":
            current_lines.append(line)

    # 最后一个段落
    if current_lines:
        paragraphs.append(
            {
                "text": "\n".join(current_lines),
                "start_line": current_start,
                "end_line": len(lines) - 1,
            }
        )

    return paragraphs


# ── 代码分割 ──────────────────────────────────────────────────


def split_code(content: str, language: str = "") -> list[dict[str, Any]]:
    """按函数/类定义分割代码文件

    对于代码文件，优先按逻辑块（函数/类）分割，
    而不是按段落分割。

    Args:
        content: 代码内容
        language: 编程语言（用于选择合适的分割模式）

    Returns:
        list of {text, start_line, end_line}
    """
    # 函数/类定义的正则（Python / JS / TS / Java / Rust / Go 等）
    # 注意: 所有 pattern 必须从具体关键字开始，不含前导 \s*
    def_patterns = [
        r"^def\s+\w+",  # Python
        r"^class\s+\w+",  # Python/Java/JS
        r"^async\s+def\s+\w+",  # Python async def
        r"^function\s+\w+",  # JS/TS
        r"^const\s+\w+",  # JS/TS const
        r"^(?:public|private|protected)\s+(?:static\s+)?(?:def|fun|fn|func|function|class|interface|enum|struct)\s+\w+",  # Java/Kotlin with modifier
        r"^(?:static\s+|abstract\s+|final\s+)?(?:def|fun|fn|func|function|class|interface|enum|struct)\s+\w+",  # with other modifier
    ]
    combined = re.compile("|".join(def_patterns), re.MULTILINE)

    lines = content.split("\n")
    chunks: list[dict[str, Any]] = []
    chunk_start = 0

    for match in combined.finditer(content):
        chunk_line = content[: match.start()].count("\n")
        if chunk_line > chunk_start:
            chunks.append(
                {
                    "text": "\n".join(lines[chunk_start:chunk_line]),
                    "start_line": chunk_start,
                    "end_line": chunk_line - 1,
                }
            )
        chunk_start = chunk_line

    # 剩余部分
    if chunk_start < len(lines):
        chunks.append(
            {
                "text": "\n".join(lines[chunk_start:]),
                "start_line": chunk_start,
                "end_line": len(lines) - 1,
            }
        )

    # 如果分割结果不合理（太少），退回段落分割
    if len(chunks) <= 1:
        return split_by_paragraphs(content)

    return chunks


def _is_code_file(path: str) -> bool:
    """判断是否为代码文件"""
    code_extensions = {
        ".py",
        ".js",
        ".ts",
        ".jsx",
        ".tsx",
        ".java",
        ".rs",
        ".go",
        ".c",
        ".h",
        ".cpp",
        ".hpp",
        ".rb",
        ".php",
        ".swift",
        ".kt",
        ".scala",
        ".lua",
        ".sh",
        ".bash",
    }
    ext = path.rsplit(".", 1)[-1].lower() if "." in path else ""
    return f".{ext}" in code_extensions


# ── 合并小块 ──────────────────────────────────────────────────


def merge_small_chunks(
    chunks: list[dict[str, Any]],
    min_size: int = 100,
    max_size: int = 2000,
) -> list[dict[str, Any]]:
    """合并过小的文本块

    将太小的段落合并到前一个段落中。
    避免产生大量只有几个字的碎片块。

    Args:
        chunks: 段落列表
        min_size: 最小字符数，小于此值的段落会合并
        max_size: 最大字符数，合并后不应超过此值

    Returns:
        合并后的段落列表
    """
    if not chunks:
        return chunks

    merged = [chunks[0]]
    for chunk in chunks[1:]:
        last = merged[-1]
        if len(last["text"]) < min_size and len(last["text"]) + len(chunk["text"]) <= max_size:
            # 合并到前一个
            last["text"] += "\n" + chunk["text"]
            last["end_line"] = chunk["end_line"]
        else:
            merged.append(chunk)
    return merged


# ── 主分割函数 ──────────────────────────────────────────────


def split_text(
    content: str,
    chunk_size: int = 500,
    overlap: int = 50,
    path: str = "",
) -> list[dict[str, Any]]:
    """将文本切分成适合搜索的块

    分块策略的完整流程:
    1. 预处理（清理空白）
    2. 按段落或代码逻辑分割
    3. 合并过小的块
    4. 将过大的块进一步切分

    Args:
        content: 文本内容
        chunk_size: 每个块的目标字符数（默认 500）
        overlap: 相邻块的重叠字符数（默认 50）
        path: 文件路径（用于代码检测）

    Returns:
        list of {text, start_line, end_line}
    """
    content = preprocess_content(content)

    # 代码文件优先按函数/类分割
    if _is_code_file(path):
        chunks = split_code(content)
    else:
        chunks = split_by_paragraphs(content)

    # 合并过小的块
    chunks = merge_small_chunks(chunks, min_size=chunk_size // 5)

    # 进一步切分过大的块
    final_chunks: list[dict[str, Any]] = []
    for chunk in chunks:
        if len(chunk["text"]) > chunk_size * 1.5:
            final_chunks.extend(_split_large_chunk(chunk, chunk_size, overlap))
        else:
            final_chunks.append(chunk)

    return final_chunks


def _split_large_chunk(
    chunk: dict[str, Any],
    chunk_size: int,
    overlap: int,
) -> list[dict[str, Any]]:
    """将过大的文本块按大小切分"""
    text = chunk["text"]
    if len(text) <= chunk_size:
        return [chunk]

    sub_chunks: list[dict[str, Any]] = []
    start_pos = 0
    chunk_index = 0

    while start_pos < len(text):
        end_pos = min(start_pos + chunk_size, len(text))

        # 在 end_pos 附近找最近的换行符（避免从单词中间截断）
        if end_pos < len(text):
            newline_pos = text.rfind("\n", start_pos, end_pos)
            if newline_pos > start_pos + chunk_size // 2:
                end_pos = newline_pos + 1

        sub_text = text[start_pos:end_pos]
        start_line = chunk["start_line"] + text[:start_pos].count("\n")
        end_line = chunk["start_line"] + text[:end_pos].count("\n")

        sub_chunks.append(
            {
                "text": sub_text.strip(),
                "start_line": start_line,
                "end_line": end_line,
            }
        )

        # 移动位置（带重叠）
        start_pos = end_pos - overlap if end_pos < len(text) else len(text)
        chunk_index += 1

        # 避免死循环
        if chunk_index > 100:
            break

    return sub_chunks


# ── 高级 API ─────────────────────────────────────────────────


def split_document(
    doc: Any,
    chunk_size: int = 500,
    overlap: int = 50,
) -> list[DocumentChunk]:
    """将 LoadedDocument 切分成 DocumentChunk 列表

    Args:
        doc: LoadedDocument 实例
        chunk_size: 每个块的目标字符数
        overlap: 相邻块重叠字符数

    Returns:
        DocumentChunk 列表
    """
    chunks = split_text(
        content=doc.content,
        chunk_size=chunk_size,
        overlap=overlap,
        path=doc.path,
    )

    result: list[DocumentChunk] = []
    for i, chunk in enumerate(chunks):
        result.append(
            DocumentChunk(
                path=doc.path,
                title=doc.title,
                content=chunk["text"],
                chunk_index=i,
                start_line=chunk["start_line"],
                end_line=chunk["end_line"],
                meta=doc.meta,
            )
        )

    return result
