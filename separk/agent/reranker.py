"""BGE cross-encoder reranking boundary."""

from __future__ import annotations

import os
from typing import Protocol

from separk.agent.models import SearchResult


class Reranker(Protocol):
    def rerank(
        self, query: str, results: list[SearchResult], top_k: int
    ) -> list[SearchResult]: ...


class BGEReranker:
    """Lazy local BGE reranker so importing SePark never downloads a model."""

    DEFAULT_MODEL = "BAAI/bge-reranker-v2-m3"

    def __init__(
        self, model_name: str | None = None, model: object | None = None
    ) -> None:
        self.model_name = model_name or os.getenv(
            "BGE_RERANKER_MODEL", self.DEFAULT_MODEL
        )
        self._model = model

    def _load(self) -> object:
        if self._model is None:
            try:
                from sentence_transformers import CrossEncoder
            except ImportError as exc:
                raise RuntimeError(
                    "BGE reranker를 사용하려면 local extra를 설치하세요: "
                    '`python -m pip install -e ".[local]"`'
                ) from exc
            self._model = CrossEncoder(self.model_name, max_length=512)
        return self._model

    def rerank(
        self, query: str, results: list[SearchResult], top_k: int = 8
    ) -> list[SearchResult]:
        if not results or top_k <= 0:
            return []
        pairs = [(query, f"{row.title}\n{row.snippet}") for row in results]
        scores = self._load().predict(pairs)
        ranked = sorted(
            zip(results, (float(score) for score in scores), strict=True),
            key=lambda item: item[1],
            reverse=True,
        )[:top_k]
        return [
            row.with_rank(f"S{index}", score)
            for index, (row, score) in enumerate(ranked, 1)
        ]


class PassthroughReranker:
    """Deterministic lightweight implementation for offline tests."""

    def rerank(
        self, query: str, results: list[SearchResult], top_k: int = 8
    ) -> list[SearchResult]:
        return [
            row.with_rank(f"S{index}", None)
            for index, row in enumerate(results[:top_k], 1)
        ]
