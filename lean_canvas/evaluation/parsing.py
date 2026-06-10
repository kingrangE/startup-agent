"""judge JSON 응답 검증·파싱 — 36개 점수(9블록 x 4차원)의 schema 검증"""

from __future__ import annotations

from lean_canvas.evaluation.models import JudgeScore
from lean_canvas.evaluation.rubric import DIMENSIONS, SCORE_MAX, SCORE_MIN
from lean_canvas.models import LeanCanvas


class JudgeParseError(Exception):
    """judge 응답이 채점 스키마를 위반했을 때 — 위반 위치를 메시지에 삽입"""


def parse_judge_response(raw: dict) -> dict[str, JudgeScore]:
    """judge JSON 응답을 검증하고 블록키 -> JudgeScore 매핑으로 변환한다.

    검증 규칙:
    - 9개 블록 키가 모두 존재
    - 각 블록에 4차원 점수가 모두 존재
    - 각 점수는 1~5 범위의 정수

    Raises:
        JudgeParseError: 위반 시 — 어느 블록·차원이 문제인지 명시.
    """
    if not isinstance(raw, dict):
        raise JudgeParseError(f"judge 응답이 JSON 객체가 아닙니다: {type(raw).__name__}")

    block_keys = list(LeanCanvas.block_titles())
    missing = [k for k in block_keys if k not in raw]
    if missing:
        raise JudgeParseError(f"누락된 블록: {', '.join(missing)}")

    result: dict[str, JudgeScore] = {}
    for key in block_keys:
        entry = raw[key]
        if not isinstance(entry, dict):
            raise JudgeParseError(f"'{key}' 블록 값이 객체가 아닙니다: {entry!r}")

        scores: dict[str, int] = {}
        for dim in DIMENSIONS:
            if dim not in entry:
                raise JudgeParseError(f"'{key}' 블록에 '{dim}' 점수가 없습니다.")
            value = entry[dim]
            # bool은 int의 서브클래스이므로 별도로 거부한다.
            if isinstance(value, bool) or not isinstance(value, int):
                raise JudgeParseError(
                    f"'{key}.{dim}' 점수가 정수가 아닙니다: {value!r}"
                )
            if not (SCORE_MIN <= value <= SCORE_MAX):
                raise JudgeParseError(
                    f"'{key}.{dim}' 점수가 {SCORE_MIN}~{SCORE_MAX} 범위를 벗어났습니다: {value}"
                )
            scores[dim] = value

        result[key] = JudgeScore(rationale=str(entry.get("rationale", "")), **scores)
    return result
