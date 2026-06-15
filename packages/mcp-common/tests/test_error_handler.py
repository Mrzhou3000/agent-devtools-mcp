"""错误处理模块测试 —— 错误码、ToolError、格式化"""

from __future__ import annotations

from mcp_common.errors.codes import (
    COM_CFG_001,
    COM_EXE_003,
    COM_NFO_001,
    COM_SEC_001,
    ALL_ERROR_CODES,
    ErrorCategory,
    ErrorCode,
    get_error_code,
)
from mcp_common.errors.handler import ToolError, format_error, is_security_error


class TestErrorCode:
    """错误码功能测试"""

    def test_error_code_attributes(self) -> None:
        """错误码应有 code/category/message/suggestion"""
        assert COM_SEC_001.code == "COM_SEC_001"
        assert COM_SEC_001.category == ErrorCategory.SECURITY
        assert "路径越权" in COM_SEC_001.message

    def test_error_code_str(self) -> None:
        """字符串表示应有 code 和 message"""
        s = str(COM_SEC_001)
        assert "COM_SEC_001" in s
        assert "路径越权" in s

    def test_all_error_codes_unique(self) -> None:
        """所有错误码的 code 应唯一"""
        codes = [ec.code for ec in ALL_ERROR_CODES]
        assert len(codes) == len(set(codes))

    def test_get_error_code_found(self) -> None:
        """查找存在的错误码"""
        ec = get_error_code("COM_SEC_001")
        assert ec is not None
        assert ec.code == "COM_SEC_001"

    def test_get_error_code_not_found(self) -> None:
        """查找不存在的错误码返回 None"""
        assert get_error_code("NONEXISTENT") is None

    def test_error_code_to_dict(self) -> None:
        """to_dict 应包含所有字段"""
        d = COM_SEC_001.to_dict()
        assert d["code"] == "COM_SEC_001"
        assert d["category"] == "security"
        assert "message" in d
        assert "suggestion" in d


class TestToolError:
    """ToolError 功能测试"""

    def test_tool_error_basic(self) -> None:
        """基本错误"""
        err = ToolError("文件不存在", code="COM_NFO_001")
        assert err.message == "文件不存在"
        assert err.code == "COM_NFO_001"

    def test_tool_error_with_suggestion(self) -> None:
        """带建议的错误"""
        err = ToolError("文件不存在", code="COM_NFO_001",
                        suggestion="请检查文件路径")
        assert "文件不存在" in str(err)
        assert "请检查文件路径" in str(err)

    def test_tool_error_default_suggestion(self) -> None:
        """已知错误码自动填充建议"""
        err = ToolError("路径越权", code="COM_SEC_001")
        assert "路径越权" in str(err)
        assert ".." in str(err)  # 默认建议里有提示

    def test_tool_error_to_dict(self) -> None:
        """to_dict 包含全部字段"""
        d = ToolError("错误", code="COM_EXE_003",
                      suggestion="增加 timeout").to_dict()
        assert d["code"] == "COM_EXE_003"
        assert d["message"] == "错误"
        assert d["suggestion"] == "增加 timeout"


class TestFormatError:
    """错误格式化测试"""

    def test_format_tool_error(self) -> None:
        """ToolError 直接返回自身"""
        err = ToolError("文件不存在", code="COM_NFO_001")
        result = format_error(err)
        assert "文件不存在" in result

    def test_format_permission_error(self) -> None:
        """PermissionError 应有权限相关提示"""
        result = format_error(PermissionError("不允许的操作"))
        assert "权限错误" in result

    def test_format_file_not_found(self) -> None:
        """FileNotFoundError 应有文件路径提示"""
        result = format_error(FileNotFoundError("test.txt"))
        assert "文件不存在" in result

    def test_format_timeout_error(self) -> None:
        """TimeoutError 应有超时提示"""
        result = format_error(TimeoutError("操作超时"))
        assert "超时" in result

    def test_format_generic_error(self) -> None:
        """通用异常应有基础错误提示"""
        result = format_error(ValueError("无效参数"))
        assert "操作失败" in result


class TestSecurityError:
    """安全错误判断测试"""

    def test_security_error_code(self) -> None:
        """安全类错误码应被识别"""
        err = ToolError("路径越权", code="COM_SEC_001")
        assert is_security_error(err)

    def test_non_security_error_code(self) -> None:
        """非安全类错误码不应被识别"""
        err = ToolError("文件不存在", code="COM_NFO_001")
        assert not is_security_error(err)

    def test_permission_error_is_security(self) -> None:
        """PermissionError 应被识别为安全错误"""
        assert is_security_error(PermissionError("拒绝"))
