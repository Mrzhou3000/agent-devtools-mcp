"""结构化日志模块

基于 structlog 实现结构化日志输出，自动注入 Trace ID。
支持控制台彩色输出和 JSON 格式输出两种模式。

用法:
    from mcp_common.logging.logger import get_logger

    logger = get_logger("mcp-devtools")
    logger.info("tool_call_start", tool="read_file", trace_id="trace_abc")

    # 也支持简单字符串（自动转为 event 字段）
    logger.info("文件读取成功")
"""

from __future__ import annotations

import logging
import sys
from typing import Any

try:
    import structlog

    HAS_STRUCTLOG = True
except ImportError:  # pragma: no cover
    HAS_STRUCTLOG = False


class _FallbackLogger:
    """structlog 不可用时的回退方案（纯文本日志）"""

    def __init__(self, name: str) -> None:
        self._logger = logging.getLogger(name)
        self._logger.setLevel(logging.DEBUG)
        if not self._logger.handlers:
            handler = logging.StreamHandler(sys.stderr)
            handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                )
            )
            self._logger.addHandler(handler)

    def _log(self, level: int, event: str, **kwargs: Any) -> None:
        extra = kwargs.pop("extra", {})
        self._logger.log(level, event, extra=extra)

    def info(self, event: str, **kwargs: Any) -> None:
        self._log(logging.INFO, event, **kwargs)

    def warning(self, event: str, **kwargs: Any) -> None:
        self._log(logging.WARNING, event, **kwargs)

    def error(self, event: str, **kwargs: Any) -> None:
        self._log(logging.ERROR, event, **kwargs)

    def debug(self, event: str, **kwargs: Any) -> None:
        self._log(logging.DEBUG, event, **kwargs)

    def exception(self, event: str, **kwargs: Any) -> None:
        self._log(logging.ERROR, event, exc_info=True, **kwargs)


def get_logger(name: str = "mcp-common") -> Any:
    """获取一个结构化日志记录器

    Args:
        name: 日志记录器名称（通常用模块名）

    Returns:
        日志记录器实例（structlog 或回退方案）
    """
    if not HAS_STRUCTLOG:  # pragma: no cover
        return _FallbackLogger(name)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.dev.ConsoleRenderer(
                colors=sys.stderr.isatty(),
                sort_keys=False,
            ),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(sys.stderr),
        cache_logger_on_first_use=True,
    )
    return structlog.get_logger(name)


def get_audit_logger() -> Any:
    """获取审计日志记录器（JSON 格式，不可关闭）

    审计日志使用 JSON 格式输出，便于后续导入日志分析系统。
    """
    if not HAS_STRUCTLOG:  # pragma: no cover
        return _FallbackLogger("audit")

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(sys.stderr),
        cache_logger_on_first_use=True,
    )
    return structlog.get_logger("audit")
