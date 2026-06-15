"""文本分块器测试"""

from __future__ import annotations

from mcp_kbtools.ingestion.splitter import (
    DocumentChunk,
    split_by_paragraphs,
    split_document,
    split_text,
)
from mcp_kbtools.ingestion.loader import LoadedDocument


class TestSplitByParagraphs:
    """段落分割测试"""

    def test_simple_paragraphs(self) -> None:
        """基本段落分割"""
        text = "Para one.\n\nPara two.\n\nPara three."
        chunks = split_by_paragraphs(text)
        assert len(chunks) == 3
        assert chunks[0]["text"] == "Para one."
        assert chunks[1]["text"] == "Para two."
        assert chunks[2]["text"] == "Para three."

    def test_single_paragraph(self) -> None:
        """只有一段"""
        chunks = split_by_paragraphs("Just one paragraph with no breaks.")
        assert len(chunks) == 1

    def test_empty_content(self) -> None:
        """空内容"""
        chunks = split_by_paragraphs("")
        assert len(chunks) == 0

    def test_trailing_newline(self) -> None:
        """尾部换行不影响"""
        text = "First.\n\nSecond.\n\n"
        chunks = split_by_paragraphs(text)
        assert len(chunks) == 2

    def test_line_tracking(self) -> None:
        """跟踪起始行号"""
        text = "Line 1\nLine 2\n\nLine 4"
        chunks = split_by_paragraphs(text)
        assert chunks[0]["start_line"] == 0
        assert chunks[0]["end_line"] == 1
        assert chunks[1]["start_line"] == 3
        assert chunks[1]["end_line"] == 3


class TestSplitText:
    """文本分块测试"""

    def test_small_text_no_split(self) -> None:
        """小文本不需要分割"""
        text = "Short text."
        chunks = split_text(text, chunk_size=500, overlap=50)
        assert len(chunks) == 1

    def test_split_by_chunk_size(self) -> None:
        """大文本按 chunk_size 分割"""
        text = "word " * 1000
        chunks = split_text(text, chunk_size=200, overlap=20)
        assert len(chunks) >= 2
        for c in chunks:
            assert len(c["text"]) <= 250  # 不应远超 chunk_size

    def test_overlap(self) -> None:
        """相邻块应有重叠"""
        text = "A very long document content " * 200
        chunks = split_text(text, chunk_size=100, overlap=30)
        if len(chunks) >= 2:
            # 前一块的尾部应与后一块的头部重叠
            assert chunks[0]["end_line"] >= chunks[1]["start_line"] - 1

    def test_preprocess_removes_excess_newlines(self) -> None:
        """预处理移除多余空行"""
        text = "A\n\n\n\nB\n\n\n\n\nC"
        chunks = split_by_paragraphs(text)
        # 经过预处理后只有 3 段
        assert len(chunks) == 3

    def test_markdown_paragraphs(self) -> None:
        """Markdown 段落分割"""
        text = "# Title\n\nSome content.\n\n## Subtitle\n\nMore content."
        chunks = split_by_paragraphs(text)
        assert len(chunks) == 4


class TestSplitDocument:
    """Document 分割测试"""

    def test_split_document(self) -> None:
        """完整的文档分割流程"""
        doc = LoadedDocument(
            path="/path/to/doc.md",
            title="Test Doc",
            content=(
                "This is the first paragraph with enough content that it should not "
                "be merged away by the small chunk merger.\n\n"
                "This is the second paragraph, also sufficiently long to stand on "
                "its own as a separate chunk.\n\n"
                "And here is the third paragraph, which completes the trio of chunks "
                "that we expect to see after splitting."
            ),
        )
        chunks = split_document(doc, chunk_size=500, overlap=50)
        assert len(chunks) >= 2  # 至少分成 2-3 个段落
        assert all(isinstance(c, DocumentChunk) for c in chunks)
        assert chunks[0].title == "Test Doc"
        assert chunks[0].path == "/path/to/doc.md"
        assert chunks[0].chunk_index == 0

    def test_chunk_tracking(self) -> None:
        """块序号和行号跟踪"""
        doc = LoadedDocument(
            path="test.md",
            title="Test",
            content="Line 1\nLine 2\n\nLine 4\nLine 5",
        )
        chunks = split_document(doc)
        for i, c in enumerate(chunks):
            assert c.chunk_index == i

    def test_empty_document(self) -> None:
        """空文档返回空"""
        doc = LoadedDocument(path="empty.md", title="Empty", content="")
        chunks = split_document(doc)
        assert len(chunks) == 0


class TestCodeSplit:
    """代码分割测试"""

    def test_python_functions(self) -> None:
        """Python 函数级分割"""
        code = """# License: MIT
# Copyright 2024
# A utility module with various tools

def foo():
    \"\"\"Do the foo operation with all the parameters configured properly.
    This function handles the core logic for processing input data.
    \"\"\"
    result = setup_environment()
    result = transform_data(result, normalize=True)
    result = validate_output(result)
    return result

def bar():
    \"\"\"Bar utility that processes the intermediate results.
    Should be called after foo has completed its work.
    \"\"\"
    items = collect_items()
    processed = [process(item) for item in items]
    return sorted(processed, key=lambda x: x.priority)

class MyClass:
    \"\"\"Main controller class for managing the application state.
    This class provides all the core functionality needed.
    \"\"\"
    def __init__(self, name: str):
        self.name = name
        self.state = {}

    def run(self):
        return self.state.get(self.name)
"""
        chunks = split_text(code, path="test.py")
        assert len(chunks) >= 3

    def test_code_without_functions(self) -> None:
        """没有函数定义的代码按段落分割"""
        code = "# This is\n# a comment file\n# with no functions"
        chunks = split_text(code, path="test.py")
        assert len(chunks) >= 1
