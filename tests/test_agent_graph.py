from __future__ import annotations

from helpers import ScriptedLLMClient

from separk.agent.graph import ResearchAgent
from separk.agent.models import SearchResult
from separk.agent.reranker import PassthroughReranker
from separk.agent.search import CompositeSearchProvider
from separk.agent.validator import EvidenceValidator


class StaticSearch:
    name = "duckduckgo"

    def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        return [
            SearchResult(
                provider=self.name,
                title="투약 기록 조사",
                url="https://example.com/research",
                snippet="보호자는 투약 기록 관리에 어려움을 겪는다",
                query=query,
            )
        ]


def payload(statement: str) -> dict:
    return {
        "canvas": {
            "problem": [statement],
            "customer_segments": [],
            "unique_value_proposition": "",
            "solution": [],
            "channels": [],
            "revenue_streams": [],
            "cost_structure": [],
            "key_metrics": [],
            "unfair_advantage": "",
        },
        "claims": [
            {
                "block": "problem",
                "text": statement,
                "kind": "fact",
                "source_ids": ["S1"],
            }
        ],
    }


def make_agent(responses: list[dict], max_revisions: int = 2) -> ResearchAgent:
    return ResearchAgent(
        llm_client=ScriptedLLMClient(responses),
        search_provider=CompositeSearchProvider((StaticSearch(),)),
        reranker=PassthroughReranker(),
        validator=EvidenceValidator(min_token_overlap=0.3),
        max_revisions=max_revisions,
    )


def test_langgraph_revises_unsupported_generation_then_passes():
    agent = make_agent(
        [
            payload("국내 시장은 매년 정확히 73% 성장한다"),
            payload("보호자는 투약 기록 관리에 어려움을 겪는다"),
        ]
    )
    result = agent.run("반려동물 헬스케어")
    assert result.validation.valid
    assert result.validation.hallucination_rate == 0
    assert result.revision_count == 1
    assert result.draft.canvas.problem == ["보호자는 투약 기록 관리에 어려움을 겪는다"]
    assert {
        "search",
        "rerank",
        "generate",
        "validate",
        "revise",
    } <= result.timings_ms.keys()


def test_langgraph_sanitizes_when_revision_budget_is_zero():
    bad_statement = "국내 시장은 매년 정확히 73% 성장한다"
    result = make_agent([payload(bad_statement)], max_revisions=0).run(
        "반려동물 헬스케어"
    )
    assert result.validation.valid
    assert result.validation.hallucination_rate == 0
    assert bad_statement not in result.draft.canvas.problem
    assert "sanitize" in result.timings_ms
    assert "final_validate" in result.timings_ms
