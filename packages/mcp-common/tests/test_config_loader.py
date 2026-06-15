"""配置加载器测试"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mcp_common.config.loader import ConfigLoader
from mcp_common.config.schema import AppConfig, DevToolsConfig


class TestConfigLoader:
    """配置加载器功能测试"""

    def test_default_config(self) -> None:
        """默认配置应包含所有必要字段"""
        loader = ConfigLoader()
        config = loader.load()
        assert "devtools" in config
        assert "database" in config
        assert "knowledge_base" in config
        assert "git" in config["devtools"]["allowed_commands"]

    def test_load_yaml_file(self, tmp_path: Path) -> None:
        """加载 YAML 配置文件"""
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text(
            "devtools:\n"
            "  allow_write: true\n"
            "  command_timeout: 60\n"
        )
        loader = ConfigLoader()
        config = loader.load([str(yaml_file)])
        assert config["devtools"]["allow_write"] is True
        assert config["devtools"]["command_timeout"] == 60

    def test_load_yaml_file_not_exist(self) -> None:
        """不存在的配置文件应被忽略"""
        loader = ConfigLoader()
        config = loader.load(["nonexistent.yaml"])
        assert len(loader.loaded_files) == 0
        assert config["devtools"]["allow_write"] is False  # 默认值

    def test_simple_yaml_parser(self, tmp_path: Path) -> None:
        """简易 YAML 解析"""
        yaml_file = tmp_path / "simple.yaml"
        yaml_file.write_text(
            "devtools:\n"
            "  allow_write: true\n"
            "  allow_command: false\n"
        )
        loader = ConfigLoader()
        # 临时模拟没有 pyyaml
        original = loader._load_yaml_file
        try:
            loader._load_yaml_file = lambda p: loader._parse_simple_yaml(Path(p))  # type: ignore[method-assign, assignment]
            config = loader.load([str(yaml_file)])
            assert config["devtools"]["allow_write"] is True
            assert config["devtools"]["allow_command"] is False
        finally:
            loader._load_yaml_file = original  # type: ignore[method-assign]

    def test_env_variable_override(self, monkeypatch: Any) -> None:
        """环境变量应覆盖配置文件"""
        monkeypatch.setenv("MCP_DEVTOOLS__ALLOW_WRITE", "true")
        monkeypatch.setenv("MCP_DATABASE__MAX_ROWS", "500")

        loader = ConfigLoader()
        config = loader.load()

        assert config["devtools"]["allow_write"] is True
        assert config["database"]["max_rows"] == 500

    def test_deep_merge(self) -> None:
        """深度合并"""
        base = {"devtools": {"allow_write": False, "timeout": 30}}
        override = {"devtools": {"allow_write": True}}

        ConfigLoader._deep_merge(base, override)
        assert base["devtools"]["allow_write"] is True
        assert base["devtools"]["timeout"] == 30  # 未被覆盖

    def test_config_loaded_files_tracking(self, tmp_path: Path) -> None:
        """跟踪已加载的配置文件"""
        yaml_file = tmp_path / "track.yaml"
        yaml_file.write_text("devtools:\n  allow_write: false\n")

        loader = ConfigLoader()
        loader.load([str(yaml_file)])
        assert len(loader.loaded_files) == 1
        assert str(yaml_file.resolve()) in loader.loaded_files[0]


class TestAppConfig:
    """AppConfig 模型测试"""

    def test_from_dict_full(self) -> None:
        """完整配置"""
        config = AppConfig.from_dict({
            "devtools": {"allow_write": True, "command_timeout": 60},
            "database": {"max_rows": 500},
            "knowledge_base": {"default_top_k": 10},
        })
        assert config.devtools.allow_write is True
        assert config.devtools.command_timeout == 60
        assert config.database.max_rows == 500
        assert config.knowledge_base.default_top_k == 10

    def test_from_dict_empty(self) -> None:
        """空配置使用默认值"""
        config = AppConfig.from_dict({})
        assert config.devtools.allow_write is False
        assert config.database.read_only is True
        assert config.knowledge_base.chunk_size == 500

    def test_devtools_config_defaults(self) -> None:
        """DevToolsConfig 默认值"""
        config = DevToolsConfig()
        assert config.allow_write is False
        assert config.command_timeout == 30
        assert "git" in config.allowed_commands
