"""Immutable contracts shared by retrieval, generation, and validation."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from lean_canvas.models import LeanCanvas

BLOCK_KEYS = tuple(LeanCanvas.block_titles())
ClaimKind = Literal["fact", "hypothesis"]


@dataclass(frozen=True)
class SearchResult:
    provider: str
    title: str
    url: str
    snippet: str
    query: str = ""
    source_id: str = ""
    score: float | None = None

    def with_rank(self, source_id: str, score: float | None = None) -> SearchResult:
        return SearchResult(
            provider=self.provider,
            title=self.title,
            url=self.url,
            snippet=self.snippet,
            query=self.query,
            source_id=source_id,
            score=score,
        )


@dataclass(frozen=True)
class GroundedClaim:
    block: str
    text: str
    kind: ClaimKind
    source_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class ResearchDraft:
    canvas: LeanCanvas
    claims: tuple[GroundedClaim, ...]


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str
    block: str = ""
    text: str = ""
    claim_index: int | None = None


@dataclass(frozen=True)
class ValidationReport:
    issues: tuple[ValidationIssue, ...]
    factual_claims: int
    unsupported_claims: int

    @property
    def valid(self) -> bool:
        return not self.issues

    @property
    def hallucination_rate(self) -> float:
        if self.factual_claims == 0:
            return 0.0
        return self.unsupported_claims / self.factual_claims


@dataclass(frozen=True)
class AgentResult:
    draft: ResearchDraft
    sources: tuple[SearchResult, ...]
    validation: ValidationReport
    revision_count: int
    timings_ms: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["validation"]["valid"] = self.validation.valid
        data["validation"]["hallucination_rate"] = self.validation.hallucination_rate
        return data
