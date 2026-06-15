"""拦截器链 —— 统一的横切关注点处理

拦截器模式（Interceptor Pattern）让日志、鉴权、限流等
横切关注点（Cross-cutting Concerns）通过统一的机制处理，
避免在每个工具中重复实现。

用法:
    from mcp_common.middleware.chain import InterceptorChain, Interceptor

    class AuditInterceptor(Interceptor):
        async def before(self, tool_name: str, args: dict) -> None:
            log_audit(tool_name, args)

        async def after(self, tool_name: str, args: dict, result: Any) -> None:
            log_audit_result(tool_name, result)

    chain = InterceptorChain()
    chain.add(AuditInterceptor())
    await chain.run_before("read_file", {"path": "test.txt"})
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any


class Interceptor(ABC):
    """拦截器基类

    所有拦截器继承此类，实现 before() 和/或 after() 方法。
    """

    @abstractmethod
    async def before(self, tool_name: str, args: dict[str, Any]) -> None:
        """工具调用前执行

        Args:
            tool_name: 调用的工具名
            args: 工具参数

        Raises:
            PermissionError: 如果请求被拦截（拒绝调用）
        """
        ...

    @abstractmethod
    async def after(
        self,
        tool_name: str,
        args: dict[str, Any],
        result: Any,
        duration_ms: float,
    ) -> None:
        """工具调用后执行

        Args:
            tool_name: 调用的工具名
            args: 工具参数
            result: 工具返回结果
            duration_ms: 执行耗时（毫秒）
        """
        ...


class LoggingInterceptor(Interceptor):
    """日志拦截器 —— 记录每次工具调用的开始和结束

    自动注入 Trace ID，记录调用耗时。
    """

    async def before(self, tool_name: str, args: dict[str, Any]) -> None:
        from ..logging.logger import get_logger
        from ..logging.trace import generate_trace_id, set_trace_id

        trace_id = generate_trace_id()
        set_trace_id(trace_id)

        logger = get_logger("mcp-interceptor")
        # 记录脱敏后的参数（不记录文件内容等敏感数据）
        safe_args = self._sanitize_args(args)
        logger.info("tool_call_start", tool=tool_name, args=safe_args)

    async def after(
        self,
        tool_name: str,
        args: dict[str, Any],
        result: Any,
        duration_ms: float,
    ) -> None:
        from ..logging.logger import get_logger

        logger = get_logger("mcp-interceptor")
        logger.info(
            "tool_call_end",
            tool=tool_name,
            duration_ms=f"{duration_ms:.1f}ms",
            result_length=len(str(result)) if result else 0,
        )

    @staticmethod
    def _sanitize_args(args: dict[str, Any]) -> dict[str, Any]:
        """脱敏参数：不记录文件内容等敏感数据"""
        SENSITIVE_KEYS = {"content", "body", "data"}
        safe: dict[str, Any] = {}
        for k, v in args.items():
            if k in SENSITIVE_KEYS and isinstance(v, str):
                safe[k] = v[:50] + "..." if len(v) > 50 else v
            else:
                safe[k] = v
        return safe


class AuditInterceptor(Interceptor):
    """审计拦截器 —— 记录所有危险操作的审计日志

    写入类操作（write_file、run_command 等）强制记录完整审计信息。
    审计日志不可关闭，以 JSON 格式输出。
    """

    DANGEROUS_TOOLS = {"write_file", "run_command", "run_async_command"}

    async def before(self, tool_name: str, args: dict[str, Any]) -> None:
        if tool_name in self.DANGEROUS_TOOLS:
            from ..logging.logger import get_audit_logger

            auditor = get_audit_logger()
            safe_args = LoggingInterceptor._sanitize_args(args)
            auditor.info("dangerous_operation_start", tool=tool_name, args=safe_args)

    async def after(
        self,
        tool_name: str,
        args: dict[str, Any],
        result: Any,
        duration_ms: float,
    ) -> None:
        if tool_name in self.DANGEROUS_TOOLS:
            from ..logging.logger import get_audit_logger

            auditor = get_audit_logger()
            auditor.info(
                "dangerous_operation_end",
                tool=tool_name,
                duration_ms=f"{duration_ms:.1f}ms",
                result_ok=not (isinstance(result, str) and "❌" in result),
            )


class InterceptorChain:
    """拦截器链 —— 管理并执行多个拦截器

    按添加顺序执行 before()，反向执行 after()。
    """

    def __init__(self) -> None:
        self._interceptors: list[Interceptor] = []

    def add(self, interceptor: Interceptor) -> None:
        """添加拦截器到链中"""
        if not isinstance(interceptor, Interceptor):
            raise TypeError(f"Expected Interceptor, got {type(interceptor)}")
        self._interceptors.append(interceptor)

    def remove(self, interceptor: Interceptor) -> None:
        """从链中移除拦截器"""
        self._interceptors.remove(interceptor)

    def clear(self) -> None:
        """清空所有拦截器"""
        self._interceptors.clear()

    @property
    def interceptors(self) -> list[Interceptor]:
        """获取拦截器列表"""
        return list(self._interceptors)

    async def run_before(self, tool_name: str, args: dict[str, Any]) -> None:
        """顺序执行所有拦截器的 before 方法

        Args:
            tool_name: 工具名
            args: 工具参数

        Raises:
            PermissionError: 如果任一拦截器拒绝请求
        """
        for interceptor in self._interceptors:
            await interceptor.before(tool_name, args)

    async def run_after(
        self,
        tool_name: str,
        args: dict[str, Any],
        result: Any,
    ) -> None:
        """反向执行所有拦截器的 after 方法"""
        duration_ms = 0.0
        start = time.monotonic()
        try:
            for interceptor in reversed(self._interceptors):
                await interceptor.after(tool_name, args, result, duration_ms)
        finally:
            duration_ms = (time.monotonic() - start) * 1000
