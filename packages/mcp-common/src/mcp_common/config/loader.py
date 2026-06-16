"""配置加载器 —— 支持多级配置源

配置加载优先级（高 → 低）:
1. 环境变量（最高，以 MCP_ 前缀开头）
2. 配置文件（YAML 格式）
3. 默认值（最低）

用法:
    from mcp_common.config.loader import ConfigLoader

    loader = ConfigLoader()
    config = loader.load(["config.yaml"])

    # 环境变量覆盖：MCP_DEVTOOLS_ALLOW_WRITE=true 会覆盖配置文件
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any


class ConfigLoader:
    """配置加载器

    支持从 YAML 文件和环境变量加载配置。
    环境变量以 MCP_ 前缀开头，用双下划线表示层级。

    示例:
        # 环境变量 MCP_DEVTOOLS_ALLOW_WRITE=true
        # 等价于配置文件中的:
        # devtools:
        #   allow_write: true
    """

    def __init__(self) -> None:
        self._loaded_files: list[str] = []

    @property
    def loaded_files(self) -> list[str]:
        """已加载的配置文件列表"""
        return list(self._loaded_files)

    def load(self, config_files: list[str] | None = None) -> dict[str, Any]:
        """加载配置（配置文件 + 环境变量覆盖）

        Args:
            config_files: YAML 配置文件路径列表（可选）

        Returns:
            合并后的配置字典
        """
        config: dict[str, Any] = {}

        # 1. 加载默认配置
        config.update(self._get_defaults())

        # 2. 加载 YAML 配置文件
        if config_files:
            for cf in config_files:
                file_config = self._load_yaml_file(cf)
                if file_config:
                    self._deep_merge(config, file_config)
                    self._loaded_files.append(str(Path(cf).resolve()))

        # 3. 加载环境变量覆盖（最高优先级）
        env_config = self._load_from_env()
        self._deep_merge(config, env_config)

        return config

    def _get_defaults(self) -> dict[str, Any]:
        """获取默认配置"""
        return {
            "devtools": {
                "workspace_root": ".",
                "allow_write": False,
                "allow_command": False,
                "allowed_commands": [
                    "git",
                    "python",
                    "uv",
                    "pip",
                    "ls",
                    "cat",
                    "grep",
                    "find",
                    "pwd",
                    "echo",
                    "node",
                    "npm",
                    "npx",
                ],
                "command_timeout": 30,
            },
            "database": {
                "read_only": True,
                "max_rows": 1000,
                "query_timeout": 30,
            },
            "knowledge_base": {
                "default_top_k": 5,
                "chunk_size": 500,
                "chunk_overlap": 50,
            },
        }

    def _load_yaml_file(self, path: str) -> dict[str, Any] | None:
        """加载 YAML 配置文件

        使用内置的简单解析，避免引入 pyyaml 依赖。
        支持基本的 key: value 和嵌套结构。
        如果文件不存在，返回 None。
        """
        file_path = Path(path)
        if not file_path.exists():
            return None

        try:
            import yaml  # type: ignore[import-untyped]

            with open(file_path, encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except ImportError:
            # 没有 pyyaml 时用简单解析
            return self._parse_simple_yaml(file_path)
        except Exception:
            return None

    def _parse_simple_yaml(self, file_path: Path) -> dict[str, Any]:
        """简易 YAML 解析（无 pyyaml 时的回退）"""
        config: dict[str, Any] = {}
        current_section: str | None = None

        with open(file_path, encoding="utf-8") as f:
            for line in f:
                stripped = line.rstrip()
                if not stripped or stripped.startswith("#"):
                    continue

                # 检测顶层 key（如 "devtools:"）
                section_match = re.match(r"^([a-zA-Z_]+):\s*$", stripped)
                if section_match:
                    current_section = section_match.group(1)
                    if current_section not in config:
                        config[current_section] = {}
                    continue

                # 检测嵌套 key（如 "  allow_write: true"）
                if current_section and stripped.startswith("  "):
                    kv_match = re.match(r"  ([a-zA-Z_]+):\s*(.*)", stripped)
                    if kv_match:
                        key = kv_match.group(1)
                        value = kv_match.group(2).strip()
                        value = self._parse_yaml_value(value)
                        config[current_section][key] = value

        return config

    @staticmethod
    def _parse_yaml_value(value: str) -> Any:
        """解析 YAML 值的类型"""
        if value.lower() in ("true", "yes", "on"):
            return True
        if value.lower() in ("false", "no", "off"):
            return False
        if value == "~" or value.lower() == "null":
            return None
        try:
            return int(value)
        except ValueError:
            pass
        try:
            return float(value)
        except ValueError:
            pass
        # 去除引号
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            return value[1:-1]
        return value

    def _load_from_env(self) -> dict[str, Any]:
        """从环境变量加载配置

        约定:
            - 前缀: MCP_
            - 层级分隔: 双下划线
            - 示例: MCP_DEVTOOLS_ALLOW_WRITE=true
                    → {"devtools": {"allow_write": True}}
        """
        config: dict[str, Any] = {}
        prefix = "MCP_"

        for key, value in os.environ.items():
            if not key.startswith(prefix):
                continue

            # 去除前缀并分割层级
            path = key[len(prefix) :].lower().split("__")

            # 设置嵌套值
            current = config
            for part in path[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]

            # 解析值类型
            parsed_value = self._parse_yaml_value(value)
            current[path[-1]] = parsed_value

        return config

    @staticmethod
    def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> None:
        """深度合并字典（override 覆盖 base）"""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                ConfigLoader._deep_merge(base[key], value)
            else:
                base[key] = value
