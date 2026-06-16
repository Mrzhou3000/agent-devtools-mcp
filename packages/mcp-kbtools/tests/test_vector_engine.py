"""向量搜索引擎测试 —— VectorEngine

测试策略:
    1. 无 sentence-transformers 时的优雅降级（available=False）
    2. 模拟 sentence-transformers 测试完整功能
    3. 持久化（save/load）测试
    4. 边界情况
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Generator
from unittest.mock import MagicMock, patch

import pytest

from mcp_kbtools.retrieval.vector_engine import VectorEngine


@pytest.fixture
def vector_engine_no_st(tmp_path: Path) -> Generator[VectorEngine, None, None]:
    """无 sentence-transformers 的向量引擎（降级模式）"""
    with patch("mcp_kbtools.retrieval.vector_engine._HAS_SENTENCE_TRANSFORMERS", False):
        engine = VectorEngine(index_dir=str(tmp_path / "vectors"))
        yield engine


@pytest.fixture
def mock_model() -> MagicMock:
    """模拟 sentence-transformers 模型（需要 numpy，否则跳过）"""
    np = pytest.importorskip("numpy", reason="需要 numpy 来生成模拟向量")

    model = MagicMock()
    # encode 返回归一化的 4 维向量
    model.encode.side_effect = (
        lambda texts, **kwargs: np.array(
            [
                [1.0, 0.0, 0.0, 0.0],  # doc 1
                [0.0, 1.0, 0.0, 0.0],  # doc 2
                [0.0, 0.0, 1.0, 0.0],  # doc 3
            ][: len(texts)],
            dtype=np.float32,
        )
    )
    return model


@pytest.fixture
def vector_engine(tmp_path: Path, mock_model: MagicMock) -> Generator[VectorEngine, None, None]:
    """功能完整的向量引擎"""
    import numpy as np

    fake_st = MagicMock()
    fake_st.SentenceTransformer.return_value = mock_model

    # 使用 create=True 创建模块中不存在的属性（try/except 模式导入）
    with patch.multiple(
        "mcp_kbtools.retrieval.vector_engine",
        _HAS_SENTENCE_TRANSFORMERS=True,
        sentence_transformers=fake_st,
        np=np,
        create=True,
    ):
        engine = VectorEngine(index_dir=str(tmp_path / "vectors"))
        yield engine


class TestVectorEngineAvailability:
    """无 sentence-transformers 时的降级行为"""

    def test_available_false_when_not_installed(self, vector_engine_no_st: VectorEngine) -> None:
        """无依赖时 available 返回 False"""
        assert not vector_engine_no_st.available

    def test_index_document_noop_when_not_available(
        self, vector_engine_no_st: VectorEngine
    ) -> None:
        """无依赖时 index_document 无操作"""
        vector_engine_no_st.index_document("test.md", "标题", "内容")
        assert vector_engine_no_st.doc_count == 0

    def test_index_documents_noop_when_not_available(
        self, vector_engine_no_st: VectorEngine
    ) -> None:
        """无依赖时 index_documents 返回 0"""
        count = vector_engine_no_st.index_documents(
            [{"path": "test.md", "title": "标题", "content": "内容"}]
        )
        assert count == 0

    def test_search_empty_when_not_available(self, vector_engine_no_st: VectorEngine) -> None:
        """无依赖时 search 返回空列表"""
        results = vector_engine_no_st.search("test")
        assert results == []

    def test_remove_document_noop_when_not_available(
        self, vector_engine_no_st: VectorEngine
    ) -> None:
        """无依赖时 remove_document 不抛异常"""
        vector_engine_no_st.remove_document("test.md")  # 不应抛异常


class TestVectorEngineWithDeps:
    """完整功能测试（模拟 sentence-transformers）"""

    def test_available_true_when_installed(self, vector_engine: VectorEngine) -> None:
        """有依赖时 available 返回 True"""
        assert vector_engine.available

    def test_index_document(self, vector_engine: VectorEngine) -> None:
        """索引单个文档"""
        vector_engine.index_document("doc1.md", "第一篇文章", "这是第一篇文章的内容")
        assert vector_engine.doc_count == 1

    def test_index_documents(self, vector_engine: VectorEngine) -> None:
        """批量索引文档"""
        docs = [
            {"path": "doc1.md", "title": "文章1", "content": "内容1"},
            {"path": "doc2.md", "title": "文章2", "content": "内容2"},
        ]
        count = vector_engine.index_documents(docs)
        assert count == 2
        assert vector_engine.doc_count == 2

    def test_index_document_update(self, vector_engine: VectorEngine) -> None:
        """更新已存在的文档"""
        vector_engine.index_document("doc1.md", "原始标题", "原始内容")
        vector_engine.index_document("doc1.md", "更新标题", "更新内容")
        assert vector_engine.doc_count == 1  # 数量不变，内容更新

    def test_remove_document(self, vector_engine: VectorEngine) -> None:
        """删除文档"""
        vector_engine.index_document("doc1.md", "文章1", "内容1")
        vector_engine.index_document("doc2.md", "文章2", "内容2")
        assert vector_engine.doc_count == 2

        vector_engine.remove_document("doc1.md")
        assert vector_engine.doc_count == 1

    def test_search_returns_results(self, vector_engine: VectorEngine) -> None:
        """搜索返回结果"""
        docs = [
            {"path": "doc1.md", "title": "Python", "content": "Python 编程"},
            {"path": "doc2.md", "title": "Java", "content": "Java 编程"},
            {"path": "doc3.md", "title": "Rust", "content": "Rust 编程"},
        ]
        vector_engine.index_documents(docs)

        results = vector_engine.search("Python", limit=2)
        assert len(results) > 0
        assert all(r.score > 0 for r in results)

    def test_search_respects_limit(self, vector_engine: VectorEngine) -> None:
        """搜索遵循 limit 参数"""
        docs = [{"path": f"doc{i}.md", "title": f"Doc {i}", "content": "内容"} for i in range(5)]
        vector_engine.index_documents(docs)

        results = vector_engine.search("test", limit=3)
        assert len(results) <= 3

    def test_search_empty_query(self, vector_engine: VectorEngine) -> None:
        """空查询返回结果"""
        docs = [
            {"path": "doc1.md", "title": "标题", "content": "内容"},
        ]
        vector_engine.index_documents(docs)

        results = vector_engine.search("", limit=5)
        # 空查询也会返回结果（模型可能对空字符串也有输出）
        assert isinstance(results, list)

    def test_search_no_documents(self, vector_engine: VectorEngine) -> None:
        """无文档时搜索返回空"""
        results = vector_engine.search("test")
        assert results == []

    def test_result_fields(self, vector_engine: VectorEngine) -> None:
        """搜索结果包含正确的字段"""
        vector_engine.index_document(
            "path/to/doc.md",
            "文档标题",
            "文档内容正文",
        )
        results = vector_engine.search("test", limit=1)
        if results:
            r = results[0]
            assert r.path == "path/to/doc.md"
            assert r.title == "文档标题"
            assert r.content == "文档内容正文"
            assert isinstance(r.score, float)


class TestVectorEnginePersistence:
    """持久化测试"""

    def test_save_and_load(self, tmp_path: Path, mock_model: MagicMock) -> None:
        """save → 重新加载 → 数据一致"""
        import numpy as np

        index_dir = tmp_path / "vectors"

        fake_st = MagicMock()
        fake_st.SentenceTransformer.return_value = mock_model

        # 第一阶段: 创建引擎并索引文档
        with patch.multiple(
            "mcp_kbtools.retrieval.vector_engine",
            _HAS_SENTENCE_TRANSFORMERS=True,
            sentence_transformers=fake_st,
            np=np,
            create=True,
        ):
            engine = VectorEngine(index_dir=str(index_dir))
            engine.index_document("doc1.md", "Python", "Python 编程语言")
            engine.index_document("doc2.md", "Rust", "Rust 系统编程")

        assert (index_dir / "meta.json").exists()
        assert (index_dir / "embeddings.npy").exists()

        # 第二阶段: 重新加载（新实例）
        with patch.multiple(
            "mcp_kbtools.retrieval.vector_engine",
            _HAS_SENTENCE_TRANSFORMERS=True,
            sentence_transformers=fake_st,
            np=np,
            create=True,
        ):
            reloaded = VectorEngine(index_dir=str(index_dir))

        assert reloaded.doc_count == 2
        # 验证元数据
        meta_path = index_dir / "meta.json"
        with open(meta_path, encoding="utf-8") as f:
            meta: dict[str, Any] = json.load(f)
        assert len(meta["documents"]) == 2

    def test_load_corrupted_meta(self, tmp_path: Path) -> None:
        """损坏的 meta.json 不抛异常"""
        index_dir = tmp_path / "vectors"
        index_dir.mkdir(parents=True, exist_ok=True)

        # 写损坏的 JSON
        with open(index_dir / "meta.json", "w") as f:
            f.write("这不是 JSON{{")

        with patch(
            "mcp_kbtools.retrieval.vector_engine._HAS_SENTENCE_TRANSFORMERS",
            False,
        ):
            engine = VectorEngine(index_dir=str(index_dir))
            assert engine.doc_count == 0


class TestVectorEngineEdgeCases:
    """边界情况"""

    def test_index_empty_content(self, vector_engine: VectorEngine) -> None:
        """空内容的文档"""
        vector_engine.index_document("empty.md", "", "")
        assert vector_engine.doc_count == 1

    def test_remove_nonexistent(self, vector_engine: VectorEngine) -> None:
        """删除不存在的文档"""
        # 不抛异常
        vector_engine.remove_document("nonexistent.md")

    def test_duplicate_paths_in_batch(self, vector_engine: VectorEngine) -> None:
        """批量索引中重复路径去重"""
        docs = [
            {"path": "doc1.md", "title": "V1", "content": "内容1"},
            {"path": "doc1.md", "title": "V2", "content": "内容2"},
        ]
        vector_engine.index_documents(docs)
        assert vector_engine.doc_count == 1
