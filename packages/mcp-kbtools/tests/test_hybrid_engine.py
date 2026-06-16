"""混合搜索引擎测试 —— HybridSearchEngine（RRF 融合）

测试策略:
    1. 单元测试 RRF 融合算法
    2. mock BM25 和向量引擎，测试三种搜索模式
    3. 边界情况（空结果、单引擎结果）
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from mcp_kbtools.retrieval import SearchResult
from mcp_kbtools.retrieval.hybrid_engine import (
    HybridSearchEngine,
    _rrf_merge,
    _to_search_results,
)
from mcp_kbtools.retrieval.vector_engine import VectorSearchResult


# ── 辅助函数 ────────────────────────────────────────────────────


def make_bm25_result(path: str, score: float = 1.0) -> SearchResult:
    """创建 BM25 搜索结果"""
    return SearchResult(
        path=path,
        title=f"Title: {path}",
        content=f"Content of {path}",
        score=score,
        highlights="",
    )


def make_vector_result(path: str, score: float = 1.0) -> VectorSearchResult:
    """创建向量搜索结果"""
    return VectorSearchResult(
        path=path,
        title=f"Title: {path}",
        content=f"Content of {path}",
        score=score,
    )


# ── RRF 融合算法单元测试 ────────────────────────────────────────


class TestRRFMerge:
    """RRF 融合算法"""

    def test_rrf_identical_results(self) -> None:
        """相同结果在两个列表中排名一致"""
        bm25 = [make_bm25_result(f"doc{i}.md") for i in range(3)]
        vector = [make_bm25_result(f"doc{i}.md") for i in range(3)]

        merged = _rrf_merge(bm25, vector)
        # 顺序应基本保持
        assert len(merged) == 3
        assert merged[0].path == "doc0.md"

    def test_rrf_different_results(self) -> None:
        """不同结果在两个列表中的融合"""
        bm25 = [
            make_bm25_result("doc1.md"),
            make_bm25_result("doc2.md"),
            make_bm25_result("doc3.md"),
        ]
        vector = [
            make_bm25_result("doc4.md", 0.9),
            make_bm25_result("doc1.md", 0.8),
            make_bm25_result("doc2.md", 0.7),
        ]

        merged = _rrf_merge(bm25, vector)
        # doc1 在两个列表中都排名靠前 → 应排第一
        assert merged[0].path == "doc1.md"
        assert len(merged) == 4  # doc1,2,3,4

    def test_rrf_only_bm25(self) -> None:
        """只有 BM25 结果"""
        bm25 = [make_bm25_result(f"doc{i}.md") for i in range(3)]
        merged = _rrf_merge(bm25, [])
        assert len(merged) == 3

    def test_rrf_only_vector(self) -> None:
        """只有向量结果"""
        vector = [make_bm25_result(f"doc{i}.md") for i in range(3)]
        merged = _rrf_merge([], vector)
        assert len(merged) == 3

    def test_rrf_empty(self) -> None:
        """两个列表都为空"""
        merged = _rrf_merge([], [])
        assert merged == []

    def test_rrf_single_overlap(self) -> None:
        """只有一个重叠结果"""
        bm25 = [make_bm25_result("shared.md")]
        vector = [make_bm25_result("shared.md")]
        merged = _rrf_merge(bm25, vector)
        assert len(merged) == 1
        assert merged[0].path == "shared.md"

    def test_rrf_no_overlap(self) -> None:
        """无重叠结果"""
        bm25 = [make_bm25_result("doc1.md")]
        vector = [make_bm25_result("doc2.md")]
        merged = _rrf_merge(bm25, vector)
        assert len(merged) == 2

    def test_rrf_custom_k(self) -> None:
        """自定义 k 值"""
        bm25 = [make_bm25_result("doc1.md")]
        vector = [make_bm25_result("doc1.md")]
        merged_small = _rrf_merge(bm25, vector, k=1)
        merged_large = _rrf_merge(bm25, vector, k=100)
        assert len(merged_small) == 1
        assert len(merged_large) == 1


# ── 转换函数测试 ────────────────────────────────────────────────


class TestToSearchResults:
    """VectorSearchResult → SearchResult 转换"""

    def test_conversion(self) -> None:
        """基本转换"""
        vec_results = [
            make_vector_result("doc1.md", 0.85),
            make_vector_result("doc2.md", 0.72),
        ]
        results = _to_search_results(vec_results)
        assert len(results) == 2
        assert results[0].path == "doc1.md"
        assert results[0].score == 0.85
        assert results[0].highlights == ""

    def test_empty(self) -> None:
        """空列表转换"""
        assert _to_search_results([]) == []


# ── HybridSearchEngine 集成测试 ─────────────────────────────────


class TestHybridSearchEngine:
    """混合搜索引擎功能测试"""

    @pytest.fixture
    def bm25_engine(self) -> MagicMock:
        """模拟 BM25 引擎"""
        mock = MagicMock()
        mock.search.return_value = [
            make_bm25_result("doc1.md", 2.0),
            make_bm25_result("doc2.md", 1.5),
        ]
        return mock

    @pytest.fixture
    def vector_engine(self) -> MagicMock:
        """模拟向量引擎"""
        mock = MagicMock()
        mock.available = True
        mock.doc_count = 2
        mock.search.return_value = [
            make_vector_result("doc2.md", 0.9),
            make_vector_result("doc3.md", 0.8),
        ]
        return mock

    @pytest.fixture
    def disabled_vector_engine(self) -> MagicMock:
        """模拟不可用的向量引擎"""
        mock = MagicMock()
        mock.available = False
        mock.doc_count = 0
        return mock

    def test_bm25_mode(self, bm25_engine: MagicMock) -> None:
        """纯 BM25 模式"""
        hybrid = HybridSearchEngine(bm25_engine)
        results = hybrid.search("test", mode="bm25")
        assert len(results) == 2
        assert results[0].path == "doc1.md"
        bm25_engine.search.assert_called_once_with("test", limit=10)

    def test_vector_mode(self, bm25_engine: MagicMock, vector_engine: MagicMock) -> None:
        """纯向量模式"""
        hybrid = HybridSearchEngine(bm25_engine, vector_engine)
        results = hybrid.search("test", mode="vector")
        assert len(results) == 2
        assert results[0].path == "doc2.md"

    def test_vector_mode_not_available(
        self, bm25_engine: MagicMock, disabled_vector_engine: MagicMock
    ) -> None:
        """向量模式但向量引擎不可用"""
        hybrid = HybridSearchEngine(bm25_engine, disabled_vector_engine)
        results = hybrid.search("test", mode="vector")
        assert results == []

    def test_hybrid_mode(self, bm25_engine: MagicMock, vector_engine: MagicMock) -> None:
        """混合模式（RRF）"""
        hybrid = HybridSearchEngine(bm25_engine, vector_engine)
        results = hybrid.search("test", mode="hybrid")

        # doc2 在两个引擎中都出现了 → RRF 分数最高
        assert len(results) >= 2
        assert results[0].path == "doc2.md"

    def test_hybrid_mode_no_vector(self, bm25_engine: MagicMock) -> None:
        """混合模式但无向量引擎 → 回退 BM25"""
        hybrid = HybridSearchEngine(bm25_engine)
        results = hybrid.search("test", mode="hybrid")
        assert len(results) == 2
        # 应该是 BM25 的原始排序
        assert results[0].path == "doc1.md"

    def test_hybrid_mode_vector_disabled(
        self, bm25_engine: MagicMock, disabled_vector_engine: MagicMock
    ) -> None:
        """混合模式但向量引擎不可用 → 回退 BM25"""
        hybrid = HybridSearchEngine(bm25_engine, disabled_vector_engine)
        results = hybrid.search("test", mode="hybrid")
        assert len(results) == 2

    def test_limit_applied(self, bm25_engine: MagicMock, vector_engine: MagicMock) -> None:
        """limit 参数正确生效"""
        hybrid = HybridSearchEngine(bm25_engine, vector_engine)
        results = hybrid.search("test", limit=1, mode="hybrid")
        assert len(results) == 1

    def test_empty_bm25_results(self, vector_engine: MagicMock) -> None:
        """BM25 无结果但有向量结果"""
        bm25_mock = MagicMock()
        bm25_mock.search.return_value = []

        hybrid = HybridSearchEngine(bm25_mock, vector_engine)
        results = hybrid.search("test", mode="hybrid")
        assert len(results) > 0
