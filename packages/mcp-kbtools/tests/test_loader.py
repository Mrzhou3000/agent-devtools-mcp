"""文档加载器测试"""

from __future__ import annotations

from pathlib import Path

import pytest

from mcp_kbtools.ingestion.loader import (
    UnsupportedFileTypeError,
    is_supported_file,
    load_document,
)


class TestLoadDocument:
    """文档加载功能测试"""

    def test_load_markdown(self, tmp_path: Path) -> None:
        """加载 Markdown 文件"""
        md_file = tmp_path / "test.md"
        md_file.write_text("# Hello World\n\nThis is a test document.\n")
        doc = load_document(str(md_file))
        assert "Hello World" in doc.content
        assert doc.title == "Hello World"  # 从 H1 推断
        assert doc.meta["extension"] == ".md"

    def test_load_txt(self, tmp_path: Path) -> None:
        """加载纯文本文件"""
        txt_file = tmp_path / "notes.txt"
        txt_file.write_text("Some notes here\n")
        doc = load_document(str(txt_file))
        assert "Some notes" in doc.content
        assert doc.title == "notes"  # 用文件名

    def test_load_python(self, tmp_path: Path) -> None:
        """加载 Python 文件"""
        py_file = tmp_path / "hello.py"
        py_file.write_text('''"""Greeting module"""\n\ndef greet(name: str) -> str:\n    return f"Hello {name}"\n''')
        doc = load_document(str(py_file))
        assert "def greet" in doc.content
        assert doc.meta["extension"] == ".py"

    def test_file_not_found(self) -> None:
        """文件不存在应报错"""
        with pytest.raises(FileNotFoundError, match="不存在"):
            load_document("/nonexistent/path/file.py")

    def test_unsupported_file_type(self, tmp_path: Path) -> None:
        """不支持的文件类型应报错"""
        exe_file = tmp_path / "test.exe"
        exe_file.write_text("dummy content")
        with pytest.raises(UnsupportedFileTypeError, match="不支持"):
            load_document(str(exe_file))

    def test_unsupported_extension_message(self, tmp_path: Path) -> None:
        """错误信息应包含支持的格式列表"""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_text("dummy")
        try:
            load_document(str(pdf_file))
        except UnsupportedFileTypeError as e:
            assert ".md" in str(e)
            assert ".py" in str(e)

    def test_meta_includes_size_lines(self, tmp_path: Path) -> None:
        """元数据应包含大小和行数"""
        md_file = tmp_path / "doc.md"
        md_file.write_text("Line 1\nLine 2\nLine 3\n")
        doc = load_document(str(md_file))
        assert doc.meta["size"] == 21
        assert doc.meta["lines"] == 3

    def test_title_from_docstring(self, tmp_path: Path) -> None:
        """从 docstring 推断标题"""
        py_file = tmp_path / "module.py"
        py_file.write_text('"""This is a module.\n\nMore description here.\n"""\n\nVERSION = "1.0"\n')
        doc = load_document(str(py_file))
        assert doc.title == "This is a module."


class TestIsSupportedFile:
    """文件类型检测测试"""

    def test_supported_extensions(self) -> None:
        """支持的扩展名应返回 True"""
        assert is_supported_file("readme.md") is True
        assert is_supported_file("main.py") is True
        assert is_supported_file("config.json") is True
        assert is_supported_file("index.html") is True

    def test_unsupported_extensions(self) -> None:
        """不支持的扩展名应返回 False"""
        assert is_supported_file("file.exe") is False
        assert is_supported_file("image.png") is False
        assert is_supported_file("archive.zip") is False
        assert is_supported_file("document.pdf") is False
