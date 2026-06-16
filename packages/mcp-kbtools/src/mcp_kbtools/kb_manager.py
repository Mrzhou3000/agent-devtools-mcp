"""知识库管理器 —— 多知识库管理

支持创建和管理多个知识库，每个知识库是一个独立的 Whoosh 索引。

用法:
    from mcp_kbtools.kb_manager import KBManager

    manager = KBManager(data_dir="./kb_data")
    manager.create_kb("my_docs", "项目文档")

    # 添加文档（自动加载 + 分块 + 索引）
    manager.add_document("my_docs", "README.md")

    # 搜索
    results = manager.search("my_docs", "关键词")
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from .ingestion.loader import load_document
from .ingestion.splitter import split_document
from .retrieval import (
    DocInfo,
    HybridSearchEngine,
    SearchEngine,
    SearchResult,
    VectorEngine,
)


class KnowledgeBaseError(Exception):
    """知识库操作异常"""

    pass


class KnowledgeBase:
    """单个知识库实例"""

    def __init__(
        self,
        index_dir: Path,
        meta: dict[str, Any],
        vector_enabled: bool = False,
    ) -> None:
        self.index_dir = index_dir
        self.meta = meta
        self.name: str = meta["name"]
        self.description: str = meta.get("description", "")

        # BM25 检索引擎（Whoosh）
        self.engine = SearchEngine(index_dir=str(index_dir))

        # 向量检索引擎（sentence-transformers，可选）
        self.vector_engine: VectorEngine | None = None
        if vector_enabled:
            vec_dir = index_dir / "vectors"
            self.vector_engine = VectorEngine(index_dir=str(vec_dir))

        # 混合检索引擎（统一接口）
        self.hybrid_engine = HybridSearchEngine(
            bm25_engine=self.engine,
            vector_engine=self.vector_engine,
        )

    @property
    def doc_count(self) -> int:
        return self.engine.doc_count

    @property
    def vector_available(self) -> bool:
        """向量搜索是否已启用且可用"""
        return self.vector_engine is not None and self.vector_engine.available


class KBManager:
    """知识库管理器

    管理多个知识库的创建、文档添加、搜索等操作。
    每个知识库在 data_dir 下有一个子目录，存储 Whoosh 索引。

    目录结构:
        {data_dir}/
            kb_index.json       ← 知识库元数据
            {kb_name}/
                ← Whoosh 索引文件
    """

    def __init__(
        self,
        data_dir: str | Path = "kb_data",
        enable_vector: bool = False,
    ) -> None:
        """
        Args:
            data_dir: 知识库数据根目录
            enable_vector: 是否启用向量搜索（需安装 sentence-transformers）
        """
        self._data_dir = Path(data_dir).resolve()
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._kbs: dict[str, KnowledgeBase] = {}
        self._vector_enabled = enable_vector

        # 加载已有知识库
        self._load_existing()

    # ── 元数据管理 ──────────────────────────────────────────

    def _meta_path(self) -> Path:
        return self._data_dir / "kb_index.json"

    def _load_existing(self) -> None:
        """从磁盘加载已有的知识库列表"""
        meta_path = self._meta_path()
        if not meta_path.exists():
            return

        try:
            with open(meta_path, encoding="utf-8") as f:
                all_meta: list[dict[str, Any]] = json.load(f)
        except Exception:
            return

        for entry in all_meta:
            name = entry.get("name", "")
            if not name:
                continue
            index_dir = self._data_dir / name
            if index_dir.exists():
                try:
                    self._kbs[name] = KnowledgeBase(
                        index_dir,
                        entry,
                        vector_enabled=self._vector_enabled,
                    )
                except Exception:
                    pass  # 索引损坏跳过

    def _save_meta(self) -> None:
        """持久化知识库元数据"""
        meta_list = []
        for name, kb in self._kbs.items():
            meta_list.append(
                {
                    "name": name,
                    "description": kb.description,
                    "doc_count": kb.doc_count,
                    "vector_enabled": kb.vector_engine is not None,
                }
            )
        with open(self._meta_path(), "w", encoding="utf-8") as f:
            json.dump(meta_list, f, ensure_ascii=False, indent=2)

    # ── 知识库管理 ──────────────────────────────────────────

    def create_kb(self, name: str, description: str = "") -> KnowledgeBase:
        """创建知识库

        Args:
            name: 知识库名称（字母数字下划线）
            description: 知识库描述

        Returns:
            创建的 KnowledgeBase 实例

        Raises:
            KnowledgeBaseError: 知识库已存在或名称不合法
        """
        import re

        if not re.match(r"^[a-zA-Z0-9_\-.]+$", name):
            raise KnowledgeBaseError(
                f"知识库名 '{name}' 不合法。只能使用字母、数字、下划线、连字符和点"
            )

        if name in self._kbs:
            raise KnowledgeBaseError(f"知识库 '{name}' 已存在")

        index_dir = self._data_dir / name
        index_dir.mkdir(parents=True, exist_ok=True)

        meta = {"name": name, "description": description}
        kb = KnowledgeBase(
            index_dir,
            meta,
            vector_enabled=self._vector_enabled,
        )
        self._kbs[name] = kb
        self._save_meta()
        return kb

    def list_kbs(self) -> list[dict[str, Any]]:
        """列出所有知识库"""
        result = []
        for name, kb in self._kbs.items():
            result.append(
                {
                    "name": name,
                    "description": kb.description,
                    "doc_count": kb.doc_count,
                    "vector_available": kb.vector_available,
                }
            )
        return result

    def get_kb(self, name: str) -> KnowledgeBase:
        """获取知识库实例

        Raises:
            KnowledgeBaseError: 知识库不存在
        """
        if name not in self._kbs:
            raise KnowledgeBaseError(f"知识库 '{name}' 不存在。请先使用 create_kb 创建")
        return self._kbs[name]

    def delete_kb(self, name: str) -> None:
        """删除知识库

        Args:
            name: 知识库名称
        """
        if name not in self._kbs:
            raise KnowledgeBaseError(f"知识库 '{name}' 不存在")

        # 删除索引文件
        index_dir = self._data_dir / name
        if index_dir.exists():
            shutil.rmtree(index_dir)

        del self._kbs[name]
        self._save_meta()

    # ── 文档管理 ────────────────────────────────────────────

    def add_document(
        self,
        kb_name: str,
        file_path: str,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
    ) -> dict[str, Any]:
        """向知识库添加文档

        处理流程:
        1. 加载文件内容（loader）
        2. 文本分块（splitter）
        3. 索引到 Whoosh（engine）

        Args:
            kb_name: 知识库名称
            file_path: 文档文件路径
            chunk_size: 分块大小（字符数）
            chunk_overlap: 块重叠大小（字符数）

        Returns:
            添加结果统计
        """
        kb = self.get_kb(kb_name)

        # 1. 加载文档
        doc = load_document(file_path)

        # 2. 分块
        chunks = split_document(
            doc,
            chunk_size=chunk_size,
            overlap=chunk_overlap,
        )

        # 3. 索引每个块
        if chunks:
            engine_docs = []
            for chunk in chunks:
                engine_docs.append(
                    {
                        "path": f"{chunk.path}#L{chunk.start_line + 1}",
                        "title": f"{chunk.title} (第 {chunk.start_line + 1} 行)",
                        "content": chunk.content,
                    }
                )
            kb.engine.index_documents(engine_docs)

            # 向量搜索：也将文档块索引到向量引擎
            if kb.vector_engine and kb.vector_engine.available:
                vec_docs = [
                    {
                        "path": d["path"],
                        "title": d["title"],
                        "content": d["content"],
                    }
                    for d in engine_docs
                ]
                kb.vector_engine.index_documents(vec_docs)

        self._save_meta()

        return {
            "file_path": doc.path,
            "title": doc.title,
            "chunks": len(chunks),
            "total_chars": doc.meta.get("size", 0),
        }

    def delete_document(self, kb_name: str, doc_path: str) -> None:
        """从知识库删除文档（及其所有分块）"""
        kb = self.get_kb(kb_name)
        # 删除所有以 doc_path 开头的索引条目
        for existing in kb.engine.list_documents():
            if existing.path.startswith(doc_path):
                kb.engine.remove_document(existing.path)
                # 同步删除向量索引
                if kb.vector_engine and kb.vector_engine.available:
                    kb.vector_engine.remove_document(existing.path)
        self._save_meta()

    def list_documents(self, kb_name: str) -> list[DocInfo]:
        """列出知识库中的文档"""
        kb = self.get_kb(kb_name)
        return kb.engine.list_documents()

    # ── 搜索 ────────────────────────────────────────────────

    def search(
        self,
        kb_name: str,
        query: str,
        top_k: int = 5,
        mode: str = "hybrid",
    ) -> list[SearchResult]:
        """搜索知识库

        Args:
            kb_name: 知识库名称
            query: 搜索关键词
            top_k: 返回结果数量上限
            mode: 搜索模式
                - "bm25":   纯 BM25 关键词搜索
                - "vector": 纯语义向量搜索
                - "hybrid": RRF 混合搜索（默认）

        Returns:
            搜索结果列表
        """
        kb = self.get_kb(kb_name)
        return kb.hybrid_engine.search(query, limit=top_k, mode=mode)
