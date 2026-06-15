"""路径校验器测试 —— 覆盖所有安全场景（Windows + Linux 兼容）"""

from __future__ import annotations

from pathlib import Path

import pytest

from mcp_common.security.path_validator import PathValidator, PathTraversalError


class TestPathValidator:
    """路径校验器测试"""

    def test_normal_path(self, tmp_path: Path) -> None:
        """正常路径应该通过校验"""
        validator = PathValidator(tmp_path)
        path = validator.validate("src/server.py")
        assert path == tmp_path / "src/server.py"
        assert str(path).startswith(str(tmp_path))

    def test_nested_path(self, tmp_path: Path) -> None:
        """深层嵌套的路径应该通过"""
        validator = PathValidator(tmp_path)
        path = validator.validate("a/b/c/d/file.txt")
        assert path == tmp_path / "a/b/c/d/file.txt"

    def test_root_path(self, tmp_path: Path) -> None:
        """传入空字符串应该报错"""
        validator = PathValidator(tmp_path)
        with pytest.raises(ValueError, match="路径不能为空"):
            validator.validate("")

    # ── 路径穿越攻击拦截 ──────────────────────────────

    @pytest.mark.security
    def test_path_traversal_simple(self, tmp_path: Path) -> None:
        """简单的 .. 路径穿越应该被拒绝"""
        validator = PathValidator(tmp_path)
        with pytest.raises(PathTraversalError):
            validator.validate("../../etc/passwd")

    @pytest.mark.security
    def test_path_traversal_nested(self, tmp_path: Path) -> None:
        """多层 .. 路径穿越应该被拒绝"""
        validator = PathValidator(tmp_path)
        with pytest.raises(PathTraversalError):
            validator.validate("../../../etc/shadow")

    @pytest.mark.security
    def test_path_traversal_mixed(self, tmp_path: Path) -> None:
        """混合路径中的 .. 穿越应该被拒绝"""
        validator = PathValidator(tmp_path)
        with pytest.raises(PathTraversalError):
            validator.validate("project/../../etc/hosts")

    @pytest.mark.security
    def test_path_outside_workspace(self, tmp_path: Path) -> None:
        """工作目录外的绝对路径应该被拒绝"""
        validator = PathValidator(tmp_path)
        with pytest.raises(PathTraversalError):
            validator.validate("C:/Windows/system32")

    def test_path_just_inside(self, tmp_path: Path) -> None:
        """工作目录自身的路径应该通过"""
        validator = PathValidator(tmp_path)
        path = validator.validate(".")
        assert path.resolve() == tmp_path.resolve()

    # ── 特殊场景 ─────────────────────────────────────

    def test_unicode_path(self, tmp_path: Path) -> None:
        """包含 Unicode 字符的路径"""
        validator = PathValidator(tmp_path)
        path = validator.validate("中文文件/文档.txt")
        assert path == tmp_path / "中文文件/文档.txt"

    def test_file_validation(self, tmp_path: Path) -> None:
        """文件不存在时应报 FileNotFoundError"""
        validator = PathValidator(tmp_path)
        with pytest.raises(FileNotFoundError, match="文件不存在"):
            validator.validate_file("nonexistent.py")

    def test_dir_validation(self, tmp_path: Path) -> None:
        """目录不存在时应报 NotADirectoryError"""
        validator = PathValidator(tmp_path)
        with pytest.raises(NotADirectoryError, match="目录不存在"):
            validator.validate_directory("nonexistent_dir")
