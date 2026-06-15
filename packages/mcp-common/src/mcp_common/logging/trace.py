"""Trace ID 生成与透传

每个请求分配一个唯一的 Trace ID，贯穿整个调用链路，
方便问题排查和审计追溯。

用法:
    from mcp_common.logging.trace import generate_trace_id, get_trace_id, set_trace_id

    trace_id = generate_trace_id()
    set_trace_id(trace_id)
    ...
    current = get_trace_id()  # 在调用链路的任何地方都能获取
"""

from __future__ import annotations

import uuid
from contextvars import ContextVar

# ContextVar 是 Python 3.7+ 的特性
# 它让同一个请求的不同函数之间共享同一个变量
# 而不同请求之间不会互相干扰
_current_trace_id: ContextVar[str] = ContextVar("trace_id", default="")


def generate_trace_id() -> str:
    """生成唯一的 Trace ID

    Returns:
        格式如 "trace_a1b2c3d4e5f6" 的 Trace ID
    """
    return f"trace_{uuid.uuid4().hex[:12]}"


def get_trace_id() -> str:
    """获取当前请求的 Trace ID

    Returns:
        当前 Trace ID，如果没有则返回空字符串
    """
    return _current_trace_id.get()


def set_trace_id(trace_id: str) -> None:
    """设置当前请求的 Trace ID

    Args:
        trace_id: 要设置的 Trace ID
    """
    _current_trace_id.set(trace_id)


def reset_trace_id() -> None:
    """重置 Trace ID（请求结束时调用）"""
    _current_trace_id.set("")
