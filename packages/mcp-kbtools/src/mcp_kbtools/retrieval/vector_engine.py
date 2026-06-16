"""向量搜索引擎 —— 使用 sentence-transformers 进行语义搜索

可选依赖（需额外安装）:
    uv sync --extra vector

当 sentence-transformers 未安装时，所有操作优雅降级返回空结果。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# ── 检测 sentence-transformers 是否可用 ────────────────────────
_HAS_SENTENCE_TRANSFORMERS = False
try:
    import numpy as np
    import sentence_transformers  # type: ignore[import-not-found]

    _HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    pass


@dataclass
class VectorSearchResult:
    """向量搜索结果"""

    path: str
    title: str
    content: str
    score: float  # cosine similarity [0, 1]


class VectorEngine:
    """向量搜索引擎

    使用 sentence-transformers 将文档编码为稠密向量，
    搜索时通过余弦相似度找到语义最相似的文档。

    当 sentence-transformers 未安装时:
        - available 属性返回 False
        - index_document / search 等方法返回空 / 无操作
        - 不会抛 ImportError

    用法:
        engine = VectorEngine(index_dir="kb_data/my_kb/vectors")
        engine.index_document("doc1.md", "标题", "内容...")
        results = engine.search("查询关键词")
    """

    def __init__(self, index_dir: str | Path) -> None:
        self._index_dir = Path(index_dir)
        self._index_dir.mkdir(parents=True, exist_ok=True)

        # 文档存储: [{path, title, content}]
        self._documents: list[dict[str, str]] = []
        # 嵌入矩阵: shape (n_docs, dim)，已归一化
        self._embeddings: Any | None = None  # np.ndarray | None
        # 模型（延迟加载）
        self._model: Any | None = None

        self._load()

    # ── 状态查询 ───────────────────────────────────────────────

    @property
    def available(self) -> bool:
        """sentence-transformers 是否已安装"""
        return _HAS_SENTENCE_TRANSFORMERS

    @property
    def doc_count(self) -> int:
        """当前索引的文档数量"""
        return len(self._documents)

    def _check_available(self) -> None:
        """检查依赖是否可用，不可用则抛明确提示"""
        if not self.available:
            raise VectorSearchError(
                "向量搜索需要 sentence-transformers\n"
                "  💡 安装: uv sync --extra vector\n"
                "  💡 或: pip install sentence-transformers numpy"
            )

    # ── 模型管理 ───────────────────────────────────────────────

    def _lazy_load_model(self) -> None:
        """延迟加载 sentence-transformers 模型"""
        if self._model is not None or not self.available:
            return
        self._model = sentence_transformers.SentenceTransformer("all-MiniLM-L6-v2")

    def _get_model(self) -> Any:
        """获取编码模型（确保已加载）

        Returns:
            编码模型实例

        Raises:
            VectorSearchError: 模型加载失败
        """
        self._lazy_load_model()
        if self._model is None:
            raise VectorSearchError("sentence-transformers 模型加载失败")
        return self._model

    # ── 文档管理 ───────────────────────────────────────────────

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
        if not self.available:
            return
        self._check_available()
        self._lazy_load_model()

        # 检查是否已存在，存在则更新
        for i, doc in enumerate(self._documents):
            if doc["path"] == path:
                self._documents[i] = {
                    "path": path,
                    "title": title,
                    "content": content,
                }
                self._rebuild_embeddings()
                self._save()
                return

        # 新增
        self._documents.append({"path": path, "title": title, "content": content})
        self._rebuild_embeddings()
        self._save()

    def index_documents(self, docs: list[dict[str, str]]) -> int:
        """批量索引文档

        Args:
            docs: 文档列表，每项含 path/title/content

        Returns:
            索引的文档数量
        """
        if not self.available:
            return 0
        self._check_available()
        self._lazy_load_model()

        for doc in docs:
            found = False
            for i, existing in enumerate(self._documents):
                if existing["path"] == doc["path"]:
                    self._documents[i] = doc
                    found = True
                    break
            if not found:
                self._documents.append(doc)

        self._rebuild_embeddings()
        self._save()
        return len(docs)

    def remove_document(self, path: str) -> None:
        """删除文档及对应的向量

        Args:
            path: 文档路径标识
        """
        self._documents = [d for d in self._documents if d["path"] != path]
        self._rebuild_embeddings()
        self._save()

    # ── 搜索 ───────────────────────────────────────────────────

    def search(
        self,
        query: str,
        limit: int = 10,
    ) -> list[VectorSearchResult]:
        """语义向量搜索

        使用 cosine similarity 找到与查询语义最相似的文档。

        Args:
            query: 查询文本
            limit: 返回结果数量上限

        Returns:
            按相似度降序排列的结果列表
        """
        if not self.available or not self._documents or self._embeddings is None:
            return []

        model = self._get_model()

        # 对查询编码并归一化
        query_emb = model.encode([query], normalize_embeddings=True)

        # 余弦相似度 = dot(normalized_a, normalized_b)
        scores = np.dot(self._embeddings, query_emb.T).flatten()

        # 取 top-k
        top_indices = np.argsort(scores)[::-1][:limit]

        results: list[VectorSearchResult] = []
        for idx in top_indices:
            score = float(scores[idx])
            if score <= 0:
                continue
            results.append(
                VectorSearchResult(
                    path=self._documents[idx]["path"],
                    title=self._documents[idx]["title"],
                    content=self._documents[idx]["content"],
                    score=score,
                )
            )
        return results

    # ── 内部方法 ───────────────────────────────────────────────

    def _rebuild_embeddings(self) -> None:
        """重新计算所有文档的嵌入向量"""
        if not self._documents or not self.available:
            self._embeddings = None
            return

        model = self._get_model()

        # 将 title 和 content 拼接后编码
        texts = [f"{d['title']}\n\n{d['content']}" for d in self._documents]
        self._embeddings = model.encode(texts, normalize_embeddings=True)

    def _save(self) -> None:
        """持久化向量索引到磁盘

        存储格式:
            meta.json     — 文档列表（JSON）
            embeddings.npy — 嵌入矩阵（numpy 二进制）
        """
        meta = {"documents": self._documents}
        with open(self._index_dir / "meta.json", "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        # 保存嵌入矩阵
        if self._embeddings is not None:
            np.save(
                str(self._index_dir / "embeddings.npy"),
                self._embeddings,
            )
        else:
            emb_path = self._index_dir / "embeddings.npy"
            if emb_path.exists():
                emb_path.unlink()

    def _load(self) -> None:
        """从磁盘加载向量索引"""
        meta_path = self._index_dir / "meta.json"
        if meta_path.exists():
            try:
                with open(meta_path, encoding="utf-8") as f:
                    meta: dict[str, Any] = json.load(f)
                self._documents = meta.get("documents", [])
            except Exception:
                self._documents = []

        # 加载嵌入矩阵
        emb_path = self._index_dir / "embeddings.npy"
        if emb_path.exists() and self.available:
            try:
                self._lazy_load_model()
                self._embeddings = np.load(str(emb_path))
            except Exception:
                self._embeddings = None


class VectorSearchError(Exception):
    """向量搜索异常"""

    pass
