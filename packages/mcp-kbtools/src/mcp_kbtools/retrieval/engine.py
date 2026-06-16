"""知识库检索引擎 —— BM25 关键词搜索 + 可选向量语义搜索

使用 Whoosh 实现 BM25 关键词搜索（开箱即用），
可选的 sentence-transformers 实现语义向量搜索。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from whoosh.analysis import StandardAnalyzer  # type: ignore[import-untyped]
from whoosh.fields import ID, TEXT, Schema  # type: ignore[import-untyped]
from whoosh.index import Index, create_in, open_dir  # type: ignore[import-untyped]
from whoosh.qparser import QueryParser  # type: ignore[import-untyped]


@dataclass
class SearchResult:
    """搜索结果"""

    path: str
    title: str
    content: str
    score: float
    highlights: str = ""


@dataclass
class DocInfo:
    """文档信息"""

    path: str
    title: str
    size: int


class SearchEngine:
    """知识库检索引擎

    使用示例:
        engine = SearchEngine(index_dir="kb_index")
        engine.index_document("doc1.txt", "文档标题", "文档内容...")
        results = engine.search("关键词")
    """

    def __init__(self, index_dir: str | Path) -> None:
        self._index_dir = Path(index_dir)
        self._schema = Schema(
            path=ID(stored=True, unique=True),
            title=TEXT(stored=True, analyzer=StandardAnalyzer()),
            content=TEXT(stored=True, analyzer=StandardAnalyzer()),
        )
        self._index = self._open_or_create_index()

    def _open_or_create_index(self) -> Index:
        """打开或创建 Whoosh 索引"""
        self._index_dir.mkdir(parents=True, exist_ok=True)
        try:
            return open_dir(str(self._index_dir), schema=self._schema)
        except Exception:
            return create_in(str(self._index_dir), self._schema)

    # ── 文档管理 ──────────────────────────────────────

    def index_document(
        self,
        path: str,
        title: str,
        content: str,
    ) -> None:
        """索引一个文档

        Args:
            path: 文档唯一路径标识
            title: 文档标题
            content: 文档内容
        """
        writer = self._index.writer()
        writer.update_document(
            path=path,
            title=title,
            content=content,
        )
        writer.commit()

    def index_documents(self, docs: list[dict[str, str]]) -> int:
        """批量索引多个文档

        Args:
            docs: 文档列表，每项含 path/title/content

        Returns:
            索引的文档数量
        """
        writer = self._index.writer()
        for doc in docs:
            writer.update_document(
                path=doc["path"],
                title=doc.get("title", ""),
                content=doc.get("content", ""),
            )
        writer.commit()
        return len(docs)

    def remove_document(self, path: str) -> None:
        """删除索引中的文档"""
        writer = self._index.writer()
        writer.delete_by_term("path", path)
        writer.commit()

    def list_documents(self) -> list[DocInfo]:
        """列出所有已索引文档"""
        with self._index.searcher() as searcher:
            results = []
            for fields in searcher.all_stored_fields():
                content = fields.get("content", "")
                results.append(
                    DocInfo(
                        path=fields.get("path", ""),
                        title=fields.get("title", ""),
                        size=len(content),
                    )
                )
            return results

    def get_document(self, path: str) -> dict[str, Any] | None:
        """按路径获取单个文档"""
        from whoosh.query import Term  # type: ignore[import-untyped]

        with self._index.searcher() as searcher:
            results = searcher.search(Term("path", path), limit=1)
            if results:
                return dict(results[0].fields())
            return None

    @property
    def doc_count(self) -> int:
        """已索引文档数量"""
        with self._index.searcher() as searcher:
            return searcher.doc_count()  # type: ignore[no-any-return]

    # ── 搜索 ─────────────────────────────────────────

    def search(
        self,
        query_str: str,
        limit: int = 10,
        field: str = "content",
    ) -> list[SearchResult]:
        """BM25 关键词搜索

        Args:
            query_str: 搜索关键词
            limit: 返回结果数量上限
            field: 搜索字段（content / title）

        Returns:
            按相关性排序的搜索结果列表
        """
        with self._index.searcher() as searcher:
            parser = QueryParser(field, self._index.schema)
            query = parser.parse(query_str)
            results = searcher.search(query, limit=limit)

            search_results = []
            for hit in results:
                search_results.append(
                    SearchResult(
                        path=hit["path"],
                        title=hit["title"],
                        content=hit["content"],
                        score=hit.score,
                        highlights=hit.highlights("content", top=3) or "",
                    )
                )
            return search_results
