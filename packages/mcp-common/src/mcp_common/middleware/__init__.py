"""拦截器链模块 —— 统一的横切关注点处理

所有工具调用前/后自动执行拦截器逻辑。
每个拦截器可以实现 before() 和 after() 方法。

用法:
    from mcp_common.middleware.chain import InterceptorChain, Interceptor

    class LoggingInterceptor(Interceptor):
        async def before(self, tool_name: str, args: dict) -> None:
            trace_id = generate_trace_id()
            set_trace_id(trace_id)

    chain = InterceptorChain()
    chain.add(LoggingInterceptor())
    await chain.run_before("read_file", {"path": "test.txt"})
"""

from .chain import Interceptor, InterceptorChain

__all__ = ["Interceptor", "InterceptorChain"]
