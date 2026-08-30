"""LangGraph workflow for retrieval-grounded Lean Canvas generation."""

from __future__ import annotations

from time import perf_counter
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from lean_canvas.llm.base import LLMClient
from separk.agent.models import (
    AgentResult,
    ResearchDraft,
    SearchResult,
    ValidationReport,
)
from separk.agent.parsing import parse_research_draft
from separk.agent.prompts import generation_messages, revision_messages
from separk.agent.reranker import Reranker
from separk.agent.search import CompositeSearchProvider
from separk.agent.validator import EvidenceValidator, sanitize_draft


class AgentValidationError(RuntimeError):
    """The final sanitized result still violated the evidence contract."""


class AgentState(TypedDict, total=False):
    interest: str
    instructions: tuple[str, ...]
    queries: tuple[str, ...]
    sources: tuple[SearchResult, ...]
    draft: ResearchDraft
    validation: ValidationReport
    revision_count: int
    timings_ms: dict[str, float]


class ResearchAgent:
    """Compile and run the full search → rerank → generate → validate graph."""

    def __init__(
        self,
        *,
        llm_client: LLMClient,
        search_provider: CompositeSearchProvider,
        reranker: Reranker,
        validator: EvidenceValidator | None = None,
        results_per_provider: int = 5,
        top_k: int = 8,
        max_revisions: int = 2,
    ) -> None:
        if results_per_provider < 1 or top_k < 1 or max_revisions < 0:
            raise ValueError(
                "검색 수와 top_k는 양수이고 max_revisions는 0 이상이어야 합니다."
            )
        self.llm_client = llm_client
        self.search_provider = search_provider
        self.reranker = reranker
        self.validator = validator or EvidenceValidator()
        self.results_per_provider = results_per_provider
        self.top_k = top_k
        self.max_revisions = max_revisions
        self.graph = self._build_graph()

    @staticmethod
    def _record_timing(
        state: AgentState, name: str, started: float, update: AgentState
    ) -> AgentState:
        timings = dict(state.get("timings_ms", {}))
        timings[name] = timings.get(name, 0.0) + (perf_counter() - started) * 1000
        update["timings_ms"] = timings
        return update

    def _plan_queries(self, state: AgentState) -> AgentState:
        started = perf_counter()
        interest = state["interest"].strip()
        queries = (
            f"{interest} 한국 시장 규모 통계",
            f"{interest} 고객 문제 설문 사례",
            f"{interest} 경쟁 서비스 가격 대안",
            f"{interest} 산업 동향 규제",
        )
        return self._record_timing(state, "plan_queries", started, {"queries": queries})

    def _search(self, state: AgentState) -> AgentState:
        started = perf_counter()
        rows = self.search_provider.search_many(
            state["queries"], max_results=self.results_per_provider
        )
        return self._record_timing(state, "search", started, {"sources": tuple(rows)})

    def _rerank(self, state: AgentState) -> AgentState:
        started = perf_counter()
        query = " ".join(state["queries"])
        ranked = self.reranker.rerank(query, list(state["sources"]), self.top_k)
        return self._record_timing(state, "rerank", started, {"sources": tuple(ranked)})

    def _generate(self, state: AgentState) -> AgentState:
        started = perf_counter()
        raw = self.llm_client.complete_json(
            generation_messages(
                state["interest"], state["instructions"], state["sources"]
            )
        )
        draft = parse_research_draft(state["interest"], raw)
        return self._record_timing(
            state, "generate", started, {"draft": draft, "revision_count": 0}
        )

    def _validate(self, state: AgentState) -> AgentState:
        started = perf_counter()
        report = self.validator.validate(state["draft"], state["sources"])
        return self._record_timing(state, "validate", started, {"validation": report})

    def _route_after_validation(self, state: AgentState) -> str:
        if state["validation"].valid:
            return "valid"
        if state.get("revision_count", 0) < self.max_revisions:
            return "revise"
        return "sanitize"

    def _revise(self, state: AgentState) -> AgentState:
        started = perf_counter()
        raw = self.llm_client.complete_json(
            revision_messages(state["draft"], state["validation"], state["sources"])
        )
        draft = parse_research_draft(state["interest"], raw)
        return self._record_timing(
            state,
            "revise",
            started,
            {"draft": draft, "revision_count": state.get("revision_count", 0) + 1},
        )

    def _sanitize(self, state: AgentState) -> AgentState:
        started = perf_counter()
        draft = sanitize_draft(state["draft"], state["validation"])
        return self._record_timing(state, "sanitize", started, {"draft": draft})

    def _final_validate(self, state: AgentState) -> AgentState:
        started = perf_counter()
        report = self.validator.validate(state["draft"], state["sources"])
        if not report.valid:
            messages = "; ".join(issue.message for issue in report.issues)
            raise AgentValidationError(
                f"최종 결과가 근거 검증을 통과하지 못했습니다: {messages}"
            )
        return self._record_timing(
            state, "final_validate", started, {"validation": report}
        )

    def _build_graph(self):
        builder = StateGraph(AgentState)
        builder.add_node("plan_queries", self._plan_queries)
        builder.add_node("search", self._search)
        builder.add_node("rerank", self._rerank)
        builder.add_node("generate", self._generate)
        builder.add_node("validate", self._validate)
        builder.add_node("revise", self._revise)
        builder.add_node("sanitize", self._sanitize)
        builder.add_node("final_validate", self._final_validate)

        builder.add_edge(START, "plan_queries")
        builder.add_edge("plan_queries", "search")
        builder.add_edge("search", "rerank")
        builder.add_edge("rerank", "generate")
        builder.add_edge("generate", "validate")
        builder.add_conditional_edges(
            "validate",
            self._route_after_validation,
            {"valid": END, "revise": "revise", "sanitize": "sanitize"},
        )
        builder.add_edge("revise", "validate")
        builder.add_edge("sanitize", "final_validate")
        builder.add_edge("final_validate", END)
        return builder.compile()

    def run(self, interest: str, instructions: tuple[str, ...] = ()) -> AgentResult:
        if not interest or not interest.strip():
            raise ValueError("창업 관심사를 입력해 주세요.")
        final = self.graph.invoke(
            {
                "interest": interest.strip(),
                "instructions": instructions,
                "revision_count": 0,
                "timings_ms": {},
            }
        )
        return AgentResult(
            draft=final["draft"],
            sources=final["sources"],
            validation=final["validation"],
            revision_count=final.get("revision_count", 0),
            timings_ms=final.get("timings_ms", {}),
        )
