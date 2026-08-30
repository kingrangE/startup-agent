from __future__ import annotations

from lean_canvas.models import LeanCanvas
from separk.agent.models import GroundedClaim, ResearchDraft, SearchResult
from separk.agent.validator import EvidenceValidator, sanitize_draft


def source() -> SearchResult:
    return SearchResult(
        "google",
        "투약 기록 조사",
        "https://example.com",
        "보호자는 투약 기록 관리에 어려움을 겪는다",
        source_id="S1",
    )


def test_validator_accepts_supported_fact_and_explicit_hypothesis():
    draft = ResearchDraft(
        LeanCanvas(
            interest="펫",
            problem=["보호자는 투약 기록 관리에 어려움을 겪는다"],
            solution=["(가설) 알림 제공"],
        ),
        (
            GroundedClaim(
                "problem", "보호자는 투약 기록 관리에 어려움을 겪는다", "fact", ("S1",)
            ),
            GroundedClaim("solution", "(가설) 알림 제공", "hypothesis"),
        ),
    )
    report = EvidenceValidator().validate(draft, (source(),))
    assert report.valid
    assert report.hallucination_rate == 0


def test_validator_rejects_and_sanitizes_unsupported_fact():
    unsupported = "시장은 매년 정확히 73% 성장한다"
    draft = ResearchDraft(
        LeanCanvas(interest="펫", problem=[unsupported]),
        (GroundedClaim("problem", unsupported, "fact", ("S1",)),),
    )
    validator = EvidenceValidator(min_token_overlap=0.3)
    report = validator.validate(draft, (source(),))
    assert not report.valid
    assert report.hallucination_rate == 1

    sanitized = sanitize_draft(draft, report)
    final = validator.validate(sanitized, (source(),))
    assert final.valid
    assert unsupported not in sanitized.canvas.problem


def test_validator_rejects_canvas_statement_missing_from_claims():
    draft = ResearchDraft(LeanCanvas(interest="펫", problem=["등록되지 않은 문장"]), ())
    report = EvidenceValidator().validate(draft, (source(),))
    assert {issue.code for issue in report.issues} == {"unregistered_statement"}
