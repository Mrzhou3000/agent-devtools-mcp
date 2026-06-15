"""配置管理模块 —— 多级配置加载

支持三种配置来源，优先级从高到低：
1. 环境变量（最高优先级）
2. 配置文件（YAML 格式）
3. 默认值

配置加载流程:
    loader = ConfigLoader()
    config = loader.load(["config.yaml", ".env"])
"""

from __future__ import annotations

from .loader import ConfigLoader
from .schema import AppConfig, DatabaseConfig, DevToolsConfig, KnowledgeBaseConfig

__all__ = [
    "ConfigLoader",
    "AppConfig",
    "DevToolsConfig",
    "DatabaseConfig",
    "KnowledgeBaseConfig",
]
