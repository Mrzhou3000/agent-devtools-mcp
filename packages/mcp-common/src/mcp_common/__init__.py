"""mcp-common: 公共基础库

为所有 MCP 服务模块提供安全、日志、错误码、配置管理、拦截器等通用能力。

核心模块:
    - security:   🔒 三层安全防御体系（路径校验/命令校验/SQL 校验）
    - logging:    📝 结构化日志 + Trace ID 透传
    - errors:     ❌ 统一错误码 + 错误处理
    - config:     ⚙️ 多级配置加载（文件 + 环境变量）
    - middleware:  🔗 拦截器链（日志/审计/鉴权）
    - models:     📐 公共数据模型
"""

from __future__ import annotations

__version__ = "0.1.0"
