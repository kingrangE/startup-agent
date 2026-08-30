"""Strict parsing for research-backed canvas responses."""

from __future__ import annotations

from typing import Any

from lean_canvas.models import LeanCanvas
from separk.agent.models import BLOCK_KEYS, GroundedClaim, ResearchDraft


class DraftParseError(ValueError):
    """Raised when a generation or revision response violates the contract."""


_LIST_BLOCKS = {
    "problem",
    "customer_segments",
    "solution",
    "channels",
    "revenue_streams",
    "cost_structure",
    "key_metrics",
}


def parse_research_draft(interest: str, raw: dict[str, Any]) -> ResearchDraft:
    if not isinstance(raw, dict) or not isinstance(raw.get("canvas"), dict):
        raise DraftParseError("응답에 canvas JSON 객체가 없습니다.")

    canvas_data = raw["canvas"]
    missing = [key for key in BLOCK_KEYS if key not in canvas_data]
    if missing:
        raise DraftParseError(f"canvas 블록 누락: {', '.join(missing)}")

    for key in BLOCK_KEYS:
        value = canvas_data[key]
        if key in _LIST_BLOCKS:
            if not isinstance(value, list) or not all(
                isinstance(v, str) for v in value
            ):
                raise DraftParseError(f"canvas.{key}는 문자열 배열이어야 합니다.")
        elif not isinstance(value, str):
            raise DraftParseError(f"canvas.{key}는 문자열이어야 합니다.")

    raw_claims = raw.get("claims")
    if not isinstance(raw_claims, list):
        raise DraftParseError("claims는 배열이어야 합니다.")

    claims: list[GroundedClaim] = []
    for index, item in enumerate(raw_claims):
        if not isinstance(item, dict):
            raise DraftParseError(f"claims[{index}]는 객체여야 합니다.")
        block = item.get("block")
        text = item.get("text")
        kind = item.get("kind")
        source_ids = item.get("source_ids", [])
        if block not in BLOCK_KEYS:
            raise DraftParseError(
                f"claims[{index}].block이 유효하지 않습니다: {block!r}"
            )
        if not isinstance(text, str) or not text.strip():
            raise DraftParseError(f"claims[{index}].text가 비어 있습니다.")
        if kind not in ("fact", "hypothesis"):
            raise DraftParseError(
                f"claims[{index}].kind는 fact 또는 hypothesis여야 합니다."
            )
        if not isinstance(source_ids, list) or not all(
            isinstance(v, str) for v in source_ids
        ):
            raise DraftParseError(
                f"claims[{index}].source_ids는 문자열 배열이어야 합니다."
            )
        claims.append(
            GroundedClaim(
                block=block,
                text=text.strip(),
                kind=kind,
                source_ids=tuple(dict.fromkeys(source_ids)),
            )
        )

    return ResearchDraft(
        canvas=LeanCanvas.from_dict(interest=interest.strip(), data=canvas_data),
        claims=tuple(claims),
    )
