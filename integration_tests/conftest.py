"""集成测试公共配置"""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def test_data_dir(tmp_path: Path) -> Path:
    """创建临时测试数据目录"""
    data_dir = tmp_path / "test_data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir
