"""
평가 데이터셋 로딩·검증

YAML 항목 형식:
  - id: good-01
    idea: 아이디어 한 문장
    category: good | ambiguous | bad
    expected_verdict: strong | acceptable | needs_work
    human_scores: null  # 또는 {specificity: 1~5, evidence: ..., coherence: ..., differentiation: ...}
    notes: 라벨 근거 메모
"""

from __future__ import annotations

from pathlib import Path

import yaml

from lean_canvas.evaluation.models import EvalDatasetItem, Verdict
from lean_canvas.evaluation.rubric import DIMENSIONS, SCORE_MAX, SCORE_MIN

VALID_CATEGORIES = ("good", "ambiguous", "bad")


class DatasetError(Exception):
    """데이터셋 스키마 위반 시 발생 — 위반 항목 메시지에 포함"""


def parse_dataset(data: object) -> list[EvalDatasetItem]:
    """YAML에서 읽은 raw 데이터 검증 후 EvalDatasetItem 목록 변환"""
    if not isinstance(data, list) or not data:
        raise DatasetError("데이터셋은 비어 있지 않은 목록이어야 합니다.")

    items: list[EvalDatasetItem] = []
    seen_ids: set[str] = set()
    for index, entry in enumerate(data):
        where = f"항목 #{index + 1}"
        if not isinstance(entry, dict):
            raise DatasetError(f"{where}: 객체가 아닙니다.")

        item_id = str(entry.get("id", "")).strip()
        if not item_id:
            raise DatasetError(f"{where}: id가 비어 있습니다.")
        if item_id in seen_ids:
            raise DatasetError(f"{where}: id '{item_id}'가 중복됩니다.")
        seen_ids.add(item_id)

        idea = str(entry.get("idea", "")).strip()
        if not idea:
            raise DatasetError(f"'{item_id}': idea가 비어 있습니다.")

        category = entry.get("category")
        if category not in VALID_CATEGORIES:
            raise DatasetError(
                f"'{item_id}': category는 {VALID_CATEGORIES} 중 하나여야 합니다: {category!r}"
            )

        try:
            expected_verdict = Verdict(entry.get("expected_verdict"))
        except ValueError:
            raise DatasetError(
                f"'{item_id}': expected_verdict가 유효하지 않습니다: "
                f"{entry.get('expected_verdict')!r}"
            ) from None

        human_scores = _parse_human_scores(item_id, entry.get("human_scores"))

        items.append(
            EvalDatasetItem(
                id=item_id,
                idea=idea,
                category=category,
                expected_verdict=expected_verdict,
                human_scores=human_scores,
                notes=str(entry.get("notes", "")),
            )
        )
    return items


def _parse_human_scores(item_id: str, raw: object) -> dict[str, int] | None:
    """사람 점수 라벨 검증 — 미채점(None) 허용, 있으면 4차원 전부 1~5 정수"""
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise DatasetError(f"'{item_id}': human_scores는 객체 또는 null이어야 합니다.")

    unknown = set(raw) - set(DIMENSIONS)
    if unknown:
        raise DatasetError(f"'{item_id}': 알 수 없는 차원: {sorted(unknown)}")
    missing = [dim for dim in DIMENSIONS if dim not in raw]
    if missing:
        raise DatasetError(f"'{item_id}': human_scores에 누락된 차원: {missing}")

    scores: dict[str, int] = {}
    for dim in DIMENSIONS:
        value = raw[dim]
        if isinstance(value, bool) or not isinstance(value, int):
            raise DatasetError(f"'{item_id}.{dim}': 점수가 정수가 아닙니다: {value!r}")
        if not (SCORE_MIN <= value <= SCORE_MAX):
            raise DatasetError(
                f"'{item_id}.{dim}': 점수가 {SCORE_MIN}~{SCORE_MAX} 범위를 벗어났습니다: {value}"
            )
        scores[dim] = value
    return scores


def load_dataset(path: Path | str) -> list[EvalDatasetItem]:
    """YAML 파일을 읽어 검증된 데이터셋을 반환"""
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return parse_dataset(data)
