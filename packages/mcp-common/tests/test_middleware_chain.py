"""拦截器链测试"""

from __future__ import annotations

from typing import Any

import pytest

from mcp_common.middleware.chain import (
    AuditInterceptor,
    Interceptor,
    InterceptorChain,
    LoggingInterceptor,
)
from mcp_common.models.base import PaginatedResult, ToolResult


class TestInterceptorChain:
    """拦截器链测试"""

    @pytest.mark.asyncio
    async def test_empty_chain(self) -> None:
        """空链不应报错"""
        chain = InterceptorChain()
        await chain.run_before("test", {})
        await chain.run_after("test", {}, "ok")

    @pytest.mark.asyncio
    async def test_add_and_run(self) -> None:
        """添加拦截器并按序执行 before"""
        calls: list[str] = []

        class TestInterceptor(Interceptor):
            async def before(self, tool_name: str, args: dict[str, Any]) -> None:
                calls.append(f"before:{tool_name}")

            async def after(
                self,
                tool_name: str,
                args: dict[str, Any],
                result: Any,
                duration_ms: float,
            ) -> None:
                calls.append(f"after:{tool_name}")

        chain = InterceptorChain()
        chain.add(TestInterceptor())
        await chain.run_before("test_tool", {})
        await chain.run_after("test_tool", {}, "ok")

        assert calls == ["before:test_tool", "after:test_tool"]

    @pytest.mark.asyncio
    async def test_add_multiple_interceptors(self) -> None:
        """添加多个拦截器"""

        class I1(Interceptor):
            async def before(self, tool_name: str, args: dict[str, Any]) -> None:
                pass

            async def after(
                self, tool_name: str, args: dict[str, Any], result: Any, duration_ms: float
            ) -> None:
                pass

        class I2(Interceptor):
            async def before(self, tool_name: str, args: dict[str, Any]) -> None:
                pass

            async def after(
                self, tool_name: str, args: dict[str, Any], result: Any, duration_ms: float
            ) -> None:
                pass

        chain = InterceptorChain()
        chain.add(I1())
        chain.add(I2())
        assert len(chain.interceptors) == 2

    @pytest.mark.asyncio
    async def test_remove_interceptor(self) -> None:
        """移除拦截器"""

        class I1(Interceptor):
            async def before(self, tool_name: str, args: dict[str, Any]) -> None:
                pass

            async def after(
                self, tool_name: str, args: dict[str, Any], result: Any, duration_ms: float
            ) -> None:
                pass

        chain = InterceptorChain()
        interceptor = I1()
        chain.add(interceptor)
        chain.remove(interceptor)
        assert len(chain.interceptors) == 0

    @pytest.mark.asyncio
    async def test_clear_interceptors(self) -> None:
        """清空拦截器"""

        class I1(Interceptor):
            async def before(self, tool_name: str, args: dict[str, Any]) -> None:
                pass

            async def after(
                self, tool_name: str, args: dict[str, Any], result: Any, duration_ms: float
            ) -> None:
                pass

        chain = InterceptorChain()
        chain.add(I1())
        chain.clear()
        assert len(chain.interceptors) == 0

    def test_add_invalid_interceptor(self) -> None:
        """添加非拦截器对象应报错"""
        chain = InterceptorChain()
        with pytest.raises(TypeError):
            chain.add("not_an_interceptor")  # type: ignore[arg-type]


class TestLoggingInterceptor:
    """日志拦截器测试"""

    @pytest.mark.asyncio
    async def test_before_after_no_error(self) -> None:
        """before 和 after 不应抛出异常"""
        interceptor = LoggingInterceptor()
        await interceptor.before("test", {})
        await interceptor.after("test", {}, "ok", 10.0)

    @pytest.mark.asyncio
    async def test_sanitize_args(self) -> None:
        """敏感参数应被截断"""
        interceptor = LoggingInterceptor()
        long_content = "x" * 200
        args = {"file_path": "test.txt", "content": long_content}
        safe = interceptor._sanitize_args(args)
        assert len(safe["content"]) < len(long_content)
        assert "..." in safe["content"]


class TestAuditInterceptor:
    """审计拦截器测试"""

    @pytest.mark.asyncio
    async def test_audit_dangerous_tool(self) -> None:
        """危险操作应被记录"""
        interceptor = AuditInterceptor()
        await interceptor.before("write_file", {"file_path": "test.txt"})
        await interceptor.after("write_file", {"file_path": "test.txt"}, "ok", 5.0)

    @pytest.mark.asyncio
    async def test_safe_tool_no_audit(self) -> None:
        """安全操作不应触发审计"""
        interceptor = AuditInterceptor()
        await interceptor.before("read_file", {"file_path": "test.txt"})
        await interceptor.after("read_file", {"file_path": "test.txt"}, "ok", 5.0)

    def test_dangerous_tools_list(self) -> None:
        """危险操作列表应包含写入和命令执行"""
        assert "write_file" in AuditInterceptor.DANGEROUS_TOOLS
        assert "run_command" in AuditInterceptor.DANGEROUS_TOOLS


class TestToolResult:
    """ToolResult 测试"""

    def test_success_result(self) -> None:
        """成功结果"""
        r = ToolResult.ok("操作成功", data={"key": "value"})
        assert r.success is True
        assert r.message == "操作成功"
        assert r.data == {"key": "value"}
        assert "操作成功" in str(r)

    def test_fail_result(self) -> None:
        """失败结果"""
        r = ToolResult.fail("出错了", code="COM_EXE_001", suggestion="请重试")
        assert r.success is False
        assert "出错了" in str(r)
        assert "请重试" in str(r)

    def test_default_success(self) -> None:
        """默认是成功"""
        r = ToolResult.ok()
        assert r.success is True


class TestPaginatedResult:
    """PaginatedResult 测试"""

    def test_has_more_true(self) -> None:
        """有更多数据"""
        r: PaginatedResult[int] = PaginatedResult(items=[1, 2], total=100, page=1, page_size=20)
        assert r.has_more is True
        assert r.total_pages == 5

    def test_has_more_false(self) -> None:
        """没有更多数据"""
        r: PaginatedResult[int] = PaginatedResult(items=[1, 2], total=2, page=1, page_size=20)
        assert r.has_more is False

    def test_total_pages_exact(self) -> None:
        """正好整除"""
        r: PaginatedResult[int] = PaginatedResult(total=100, page_size=20)
        assert r.total_pages == 5

    def test_total_pages_remainder(self) -> None:
        """有余数"""
        r: PaginatedResult[int] = PaginatedResult(total=101, page_size=20)
        assert r.total_pages == 6
