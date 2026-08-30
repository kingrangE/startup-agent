from __future__ import annotations

from separk.agent.models import SearchResult
from separk.agent.reranker import BGEReranker


class FakeCrossEncoder:
    def predict(self, pairs):
        assert len(pairs) == 3
        return [0.2, 0.9, 0.5]


def test_bge_reranker_orders_scores_and_assigns_source_ids():
    rows = [
        SearchResult("p", "a", "https://a", "a"),
        SearchResult("p", "b", "https://b", "b"),
        SearchResult("p", "c", "https://c", "c"),
    ]
    ranked = BGEReranker(model=FakeCrossEncoder()).rerank("query", rows, top_k=2)
    assert [row.title for row in ranked] == ["b", "c"]
    assert [row.source_id for row in ranked] == ["S1", "S2"]
    assert ranked[0].score == 0.9
