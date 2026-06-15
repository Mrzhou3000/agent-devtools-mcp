"""Trace ID 生成与透传测试"""

from __future__ import annotations

from mcp_common.logging.trace import (
    generate_trace_id,
    get_trace_id,
    reset_trace_id,
    set_trace_id,
)


class TestTraceId:
    """Trace ID 功能测试"""

    def test_generate_trace_id_format(self) -> None:
        """Trace ID 格式应为 trace_xxxxxxxxxxxx"""
        trace_id = generate_trace_id()
        assert trace_id.startswith("trace_")
        assert len(trace_id) == 6 + 12  # "trace_" + 12 hex chars

    def test_generate_trace_id_unique(self) -> None:
        """每次生成的 Trace ID 应唯一"""
        ids = {generate_trace_id() for _ in range(100)}
        assert len(ids) == 100

    def test_set_and_get_trace_id(self) -> None:
        """设置后应能正确获取"""
        trace_id = generate_trace_id()
        set_trace_id(trace_id)
        assert get_trace_id() == trace_id
        reset_trace_id()

    def test_get_trace_id_default(self) -> None:
        """未设置时返回空字符串"""
        reset_trace_id()
        assert get_trace_id() == ""

    def test_reset_trace_id(self) -> None:
        """重置后应返回空"""
        set_trace_id(generate_trace_id())
        reset_trace_id()
        assert get_trace_id() == ""

    def test_context_isolation(self) -> None:
        """不同上下文互不干扰"""
        import threading

        results: list[str] = []

        def worker() -> None:
            set_trace_id(generate_trace_id())
            results.append(get_trace_id())
            reset_trace_id()

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 每个线程应有不同的 Trace ID
        assert len(set(results)) == 10
