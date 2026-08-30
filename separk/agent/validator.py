"""Evidence validator used as an explicit LangGraph node."""

from __future__ import annotations

import re
from dataclasses import replace

from lean_canvas.models import LeanCanvas
from separk.agent.models import (
    BLOCK_KEYS,
    ResearchDraft,
    SearchResult,
    ValidationIssue,
    ValidationReport,
)


def _tokens(text: str) -> set[str]:
    return {
        token.lower()
        for token in re.findall(r"[가-힣A-Za-z0-9]{2,}", text)
        if token.lower() not in {"그리고", "대한", "위한", "있는", "한다", "통한"}
    }


def _canvas_statements(canvas: LeanCanvas) -> list[tuple[str, str]]:
    statements: list[tuple[str, str]] = []
    for block in BLOCK_KEYS:
        value = getattr(canvas, block)
        rows = value if isinstance(value, list) else [value]
        statements.extend((block, row.strip()) for row in rows if row.strip())
    return statements


class EvidenceValidator:
    """Reject uncited facts and citations whose snippets do not support a claim."""

    def __init__(self, min_token_overlap: float = 0.15) -> None:
        if not 0 <= min_token_overlap <= 1:
            raise ValueError("min_token_overlap은 0과 1 사이여야 합니다.")
        self.min_token_overlap = min_token_overlap

    def validate(
        self, draft: ResearchDraft, sources: tuple[SearchResult, ...]
    ) -> ValidationReport:
        source_map = {source.source_id: source for source in sources}
        issues: list[ValidationIssue] = []
        registered = {
            (claim.block, claim.text): index for index, claim in enumerate(draft.claims)
        }

        for block, text in _canvas_statements(draft.canvas):
            if (block, text) not in registered:
                issues.append(
                    ValidationIssue(
                        code="unregistered_statement",
                        message=f"{block} 문장이 claims에 등록되지 않았습니다: {text}",
                        block=block,
                        text=text,
                    )
                )

        factual_claims = 0
        unsupported_indexes: set[int] = set()
        for index, claim in enumerate(draft.claims):
            if claim.block not in BLOCK_KEYS:
                issues.append(
                    ValidationIssue(
                        "invalid_block",
                        "알 수 없는 블록입니다.",
                        claim.block,
                        claim.text,
                        index,
                    )
                )
                unsupported_indexes.add(index)
                continue
            if claim.kind == "hypothesis":
                if not claim.text.startswith("(가설)") or claim.source_ids:
                    issues.append(
                        ValidationIssue(
                            "invalid_hypothesis",
                            "가설은 '(가설)'로 시작하고 출처를 사용하지 않아야 합니다.",
                            claim.block,
                            claim.text,
                            index,
                        )
                    )
                    unsupported_indexes.add(index)
                continue

            factual_claims += 1
            valid_sources = [
                source_map[sid] for sid in claim.source_ids if sid in source_map
            ]
            if not claim.source_ids or len(valid_sources) != len(claim.source_ids):
                issues.append(
                    ValidationIssue(
                        "missing_source",
                        "사실 주장에 존재하는 검색 출처가 연결되지 않았습니다.",
                        claim.block,
                        claim.text,
                        index,
                    )
                )
                unsupported_indexes.add(index)
                continue

            claim_tokens = _tokens(claim.text)
            evidence_tokens = _tokens(
                " ".join(f"{s.title} {s.snippet}" for s in valid_sources)
            )
            overlap = len(claim_tokens & evidence_tokens) / max(1, len(claim_tokens))
            if overlap < self.min_token_overlap:
                issues.append(
                    ValidationIssue(
                        "unsupported_claim",
                        "검색 스니펫과 주장 토큰 중첩률 "
                        f"{overlap:.0%}가 기준 미만입니다.",
                        claim.block,
                        claim.text,
                        index,
                    )
                )
                unsupported_indexes.add(index)

        return ValidationReport(
            issues=tuple(issues),
            factual_claims=factual_claims,
            unsupported_claims=len(unsupported_indexes),
        )


def sanitize_draft(draft: ResearchDraft, report: ValidationReport) -> ResearchDraft:
    """Remove statements that remain unsupported after the revision budget."""

    removals = {
        (issue.block, issue.text)
        for issue in report.issues
        if issue.block and issue.text
    }
    canvas_values: dict[str, object] = {}
    for block in BLOCK_KEYS:
        value = getattr(draft.canvas, block)
        if isinstance(value, list):
            canvas_values[block] = [
                row for row in value if (block, row) not in removals
            ]
        else:
            canvas_values[block] = "" if (block, value) in removals else value

    kept_claims = tuple(
        claim for claim in draft.claims if (claim.block, claim.text) not in removals
    )
    return replace(
        draft,
        canvas=LeanCanvas.from_dict(draft.canvas.interest, canvas_values),
        claims=kept_claims,
    )
