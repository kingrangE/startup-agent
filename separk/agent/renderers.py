"""Human-readable output for grounded agent results."""

from __future__ import annotations

from lean_canvas.renderers import MarkdownRenderer
from separk.agent.models import AgentResult


def render_markdown(result: AgentResult) -> str:
    sections = [MarkdownRenderer().render(result.draft.canvas), "\n## 근거 주장"]
    for claim in result.draft.claims:
        citations = ", ".join(f"[{sid}]" for sid in claim.source_ids) or "가설"
        sections.append(f"- **{claim.block}**: {claim.text} — {citations}")
    sections.append("\n## 검색 출처")
    sections.extend(
        f"- [{source.source_id}] [{source.title}]({source.url}) ({source.provider})"
        for source in result.sources
    )
    sections.append(
        "\n## 검증\n"
        f"- 통과: {result.validation.valid}\n"
        f"- 최종 환각률: {result.validation.hallucination_rate:.1%}\n"
        f"- 수정 횟수: {result.revision_count}\n"
        f"- 단계별 지연(ms): {result.timings_ms}"
    )
    return "\n".join(sections) + "\n"
