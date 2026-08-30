"""Production dependency assembly for the research-backed agent."""

from __future__ import annotations

import os

from lean_canvas.llm.base import LLMClient
from lean_canvas.llm.openai_client import OpenAILLMClient
from separk.agent.graph import ResearchAgent
from separk.agent.reranker import BGEReranker, Reranker
from separk.agent.search import CompositeSearchProvider, create_search_provider
from separk.agent.validator import EvidenceValidator
from separk.llm.ax_client import AXModelClient


def create_agent_llm(
    provider: str | None = None, model: str | None = None
) -> LLMClient:
    resolved = (provider or os.getenv("SEPARK_LLM_PROVIDER", "ax")).lower()
    if resolved == "ax":
        return AXModelClient(model_id=model)
    if resolved == "openai":
        return OpenAILLMClient(model=model or os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
    raise ValueError(f"지원하지 않는 LLM provider입니다: {resolved}")


def create_research_agent(
    *,
    provider: str | None = None,
    model: str | None = None,
    llm_client: LLMClient | None = None,
    search_provider: CompositeSearchProvider | None = None,
    reranker: Reranker | None = None,
    validator: EvidenceValidator | None = None,
    require_google: bool = False,
    results_per_provider: int = 5,
    top_k: int = 8,
    max_revisions: int = 2,
) -> ResearchAgent:
    return ResearchAgent(
        llm_client=llm_client or create_agent_llm(provider, model),
        search_provider=search_provider
        or create_search_provider(require_google=require_google),
        reranker=reranker or BGEReranker(),
        validator=validator or EvidenceValidator(),
        results_per_provider=results_per_provider,
        top_k=top_k,
        max_revisions=max_revisions,
    )
