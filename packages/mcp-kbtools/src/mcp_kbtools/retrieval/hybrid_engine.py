"""混合搜索引擎 —— BM25 关键词 + 向量语义搜索（RRF 融合）

使用 Reciprocal Rank Fusion (RRF) 算法融合两种搜索结果，
兼顾精确的关键词匹配和语义相似度。

搜索模式:
    bm25    — 纯 BM25 关键词搜索（Whoosh）
    vector  — 纯语义向量搜索（sentence-transformers）
    hybrid  — RRF 融合（默认推荐）
"""

from __future__ import annotations

from collections.abc import Sequence

from .engine import SearchEngine, SearchResult
from .vector_engine import VectorEngine, VectorSearchResult


class HybridSearchEngine:
    """混合搜索引擎

    包装 BM25 和向量两个引擎，提供统一搜索接口。

    用法:
        hybrid = HybridSearchEngine(bm25_engine, vector_engine)
        results = hybrid.search("查询", mode="hybrid")
    """

    def __init__(
        self,
        bm25_engine: SearchEngine,
        vector_engine: VectorEngine | None = None,
    ) -> None:
        """
        Args:
            bm25_engine: BM25 检索引擎（必须）
            vector_engine: 向量检索引擎（可选）
        """
        self._bm25 = bm25_engine
        self._vector = vector_engine

    def _get_vector(self) -> VectorEngine:
        """获取向量引擎实例（确保可用）

        Returns:
            VectorEngine 实例

        Raises:
            RuntimeError: 向量引擎不可用
        """
        if self._vector is None or not self._vector.available:
            raise RuntimeError("向量搜索引擎不可用")
        return self._vector

    def _vector_available(self) -> bool:
        """向量引擎是否就绪"""
        return self._vector is not None and self._vector.available and self._vector.doc_count > 0

    def search(
        self,
        query_str: str,
        limit: int = 10,
        mode: str = "hybrid",
    ) -> list[SearchResult]:
        """混合搜索

        Args:
            query_str: 搜索关键词
            limit: 返回结果数量上限
            mode: 搜索模式
                - "bm25":  纯 BM25 关键词搜索
                - "vector": 纯语义向量搜索
                - "hybrid": RRF 融合（默认）

        Returns:
            按相关性排序的结果列表（统一使用 SearchResult 类型）
        """
        # 纯 BM25
        if mode == "bm25":
            return self._bm25.search(query_str, limit=limit)

        # 纯向量搜索
        if mode == "vector":
            if not self._vector_available():
                return []
            vec_results = self._get_vector().search(query_str, limit=limit)
            return _to_search_results(vec_results)

        # 混合模式: RRF 融合
        # 两大引擎各取 2x 结果，再融合排序
        bm25_results = self._bm25.search(query_str, limit=limit * 2)

        vector_results: list[SearchResult] = []
        if self._vector_available():
            vec_results = self._get_vector().search(query_str, limit=limit * 2)
            vector_results = _to_search_results(vec_results)

        # 如果只有 BM25 结果，直接返回
        if not vector_results:
            return bm25_results[:limit]

        # RRF 融合
        return _rrf_merge(bm25_results, vector_results)[:limit]


# ── RRF 融合 ────────────────────────────────────────────────────


def _rrf_merge(
    bm25_results: Sequence[SearchResult],
    vector_results: Sequence[SearchResult],
    k: int = 60,
) -> list[SearchResult]:
    """Reciprocal Rank Fusion 融合排序

    RRF 对每个结果在多个排序中的倒数排名求和:
        score(r) = SUM(1 / (k + rank_i(r)))

    k 是平滑常数（默认 60），越大越平均，越小越偏向高排名。

    Args:
        bm25_results: BM25 搜索结果（按 BM25 排序）
        vector_results: 向量搜索结果（按向量相似度排序）
        k: RRF 平滑常数

    Returns:
        RRF 重排序后的结果列表（按融合分数降序）
    """
    # 收集所有路径的排名
    bm25_ranks = {r.path: idx + 1 for idx, r in enumerate(bm25_results)}
    vector_ranks = {r.path: idx + 1 for idx, r in enumerate(vector_results)}

    # 所有结果的并集路径
    all_paths = set(bm25_ranks) | set(vector_ranks)

    # 计算结果查找表和 RRF 分数
    result_map: dict[str, SearchResult] = {}
    for r in bm25_results:
        result_map[r.path] = r
    for r in vector_results:
        if r.path not in result_map:
            result_map[r.path] = r

    path_scores: list[tuple[str, float]] = []
    for path in all_paths:
        bm25_score = 1.0 / (k + bm25_ranks.get(path, len(bm25_results) + 1))
        vec_score = 1.0 / (k + vector_ranks.get(path, len(vector_results) + 1))
        rrf_score = bm25_score + vec_score
        path_scores.append((path, rrf_score))

    # 按 RRF 分数降序排列
    path_scores.sort(key=lambda x: x[1], reverse=True)

    return [result_map[path] for path, _ in path_scores if path in result_map]


def _to_search_results(
    vec_results: Sequence[VectorSearchResult],
) -> list[SearchResult]:
    """将 VectorSearchResult 转为 SearchResult

    VectorSearchResult 没有 highlights，所以留空。
    """
    return [
        SearchResult(
            path=r.path,
            title=r.title,
            content=r.content[:500],  # 截断以保持一致性
            score=r.score,
            highlights="",
        )
        for r in vec_results
    ]
