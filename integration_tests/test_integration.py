"""跨模块集成测试 —— 验证三个 MCP 模块的核心流程

这些测试不直接启动 MCP Server，而是直接调用工具函数，
验证跨模块的功能完整性。
"""

from __future__ import annotations

from pathlib import Path

import pytest

# ═══════════════════════════════════════════════════════════════
# 集成测试 1: 安全模块 → 文件操作
# ═══════════════════════════════════════════════════════════════


class TestSecurityToFileOps:
    """安全模块与文件操作集成"""

    def test_path_validator_and_read(self, test_data_dir: Path):
        """路径校验 + 文件读取"""
        from pathlib import Path as _Path
        from mcp_common.security.path_validator import PathValidator

        validator = PathValidator(str(test_data_dir))

        # 创建测试文件
        test_file = test_data_dir / "hello.txt"
        test_file.write_text("Hello World")

        # 路径校验通过后读取
        safe_path = validator.validate("hello.txt")
        assert safe_path.exists()
        content = safe_path.read_text(encoding="utf-8")
        assert "Hello World" in content

    def test_path_traversal_blocked(self, test_data_dir: Path):
        """路径穿越被安全模块拦截"""
        from mcp_common.security.path_validator import PathValidator

        validator = PathValidator(str(test_data_dir))

        with pytest.raises((PermissionError, ValueError)):
            validator.validate("../../etc/passwd")


# ═══════════════════════════════════════════════════════════════
# 集成测试 2: 数据库查询
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_dbtools_list_and_query():
    """数据库模块：建表 → 插入 → 列表 → 查询"""
    from mcp_dbtools.adapters.sqlite import SQLiteAdapter

    db = SQLiteAdapter(database=":memory:")
    await db.connect()

    # 建表
    await db.execute_query(
        "CREATE TABLE products ("
        "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "  name TEXT NOT NULL,"
        "  price REAL"
        ")"
    )
    await db.execute_query(
        "INSERT INTO products (name, price) VALUES (?, ?)",
        ("Widget", 9.99),
    )
    await db.execute_query(
        "INSERT INTO products (name, price) VALUES (?, ?)",
        ("Gadget", 24.99),
    )

    # 列出表
    tables = await db.list_tables()
    table_names = [t.name for t in tables]
    assert "products" in table_names

    # 描述表
    info = await db.describe_table("products")
    assert any(col.name == "name" for col in info.columns)
    assert any(col.name == "price" for col in info.columns)

    # 查询
    rows = await db.execute_query("SELECT * FROM products ORDER BY id")
    assert len(rows) == 2
    assert rows[0]["name"] == "Widget"

    # 安全拦截
    from mcp_common.security.sql_validator import validate_readonly_query

    with pytest.raises((PermissionError, ValueError)):
        validate_readonly_query("DROP TABLE products")

    await db.disconnect()


# ═══════════════════════════════════════════════════════════════
# 集成测试 3: 知识库文档加载 → 分块 → 搜索
# ═══════════════════════════════════════════════════════════════


def test_kbtools_ingest_and_search(tmp_path: Path):
    """知识库模块：创建 KB → 添加文档 → 搜索"""
    from mcp_kbtools.kb_manager import KBManager

    manager = KBManager(data_dir=str(tmp_path / "kb_integration"))

    # 创建文档
    doc_file = tmp_path / "integrated_doc.md"
    doc_file.write_text(
        "# Integrated Test Document\n\n"
        "This document is used for integration testing.\n"
        "It contains multiple paragraphs to test the full pipeline.\n\n"
        "## BM25 Search\n\n"
        "The BM25 algorithm is great for keyword search.\n"
        "It ranks documents based on term frequency.\n"
    )

    # 创建知识库并添加文档
    manager.create_kb("integration_test", "集成测试知识库")
    result = manager.add_document("integration_test", str(doc_file))

    assert result["chunks"] >= 1
    assert result["title"] is not None

    # 搜索
    results = manager.search("integration_test", "BM25 algorithm")
    assert len(results) >= 1
    assert results[0].score > 0


# ═══════════════════════════════════════════════════════════════
# 集成测试 4: 错误处理模块
# ═══════════════════════════════════════════════════════════════


class TestErrorHandlingIntegration:
    """错误处理与各模块集成"""

    def test_security_error_formatted(self):
        """安全错误被统一格式化"""
        from mcp_common.errors.handler import ToolError, format_error

        err = ToolError(
            "路径越权",
            code="COM_SEC_001",
            suggestion="请检查文件路径",
        )
        msg = format_error(err)
        assert "路径越权" in msg
        assert "请检查" in msg

    def test_trace_id_propagation(self):
        """Trace ID 在调用链中透传"""
        from mcp_common.logging.trace import (
            generate_trace_id,
            get_trace_id,
            set_trace_id,
        )

        trace_id = generate_trace_id()
        set_trace_id(trace_id)

        # 模拟调用链
        def inner_function():
            return get_trace_id()

        propagated = inner_function()
        assert propagated == trace_id


# ═══════════════════════════════════════════════════════════════
# 集成测试 5: 配置模块
# ═══════════════════════════════════════════════════════════════


def test_config_loading_and_schema():
    """配置加载 + schema 验证"""
    from mcp_common.config.loader import ConfigLoader
    from mcp_common.config.schema import AppConfig

    loader = ConfigLoader()
    raw_config = loader.load()
    config = AppConfig.from_dict(raw_config)

    assert config.devtools.allow_write is False
    assert config.database.read_only is True
    assert config.knowledge_base.default_top_k == 5
