"""judge JSON 응답 검증/파싱 테스트 — 36개 점수 스키마의 엄격함을 고정"""

from __future__ import annotations

import pytest

from lean_canvas.evaluation.parsing import JudgeParseError, parse_judge_response

from helpers import make_judge_response


def test_valid_response_parses():
    """정상 응답은 9개 블록의 JudgeScore로 변환, rationale이 보존"""
    result = parse_judge_response(make_judge_response(score=3, rationale="근거 문장"))
    assert len(result) == 9
    assert result["problem"].evidence == 3
    assert result["problem"].rationale == "근거 문장"


def test_missing_block_rejected():
    """블록 누락 시 어느 블록인지 메시지에 명시"""
    response = make_judge_response()
    del response["channels"]
    with pytest.raises(JudgeParseError, match="channels"):
        parse_judge_response(response)


def test_missing_dimension_rejected():
    """차원 누락 시 블록/차원을 메시지에 명시"""
    response = make_judge_response()
    del response["solution"]["coherence"]
    with pytest.raises(JudgeParseError, match="solution.*coherence"):
        parse_judge_response(response)


@pytest.mark.parametrize("bad_value", [0, 6, "4", 4.5, True, None])
def test_invalid_score_values_rejected(bad_value):
    """자료형이 맞지 않는 score 입력 시 에러 레이즈 검증"""
    response = make_judge_response(
        overrides={"problem": {"evidence": bad_value}}
    )
    with pytest.raises(JudgeParseError, match="problem.*evidence"):
        parse_judge_response(response)


def test_non_dict_block_rejected():
    response = make_judge_response()
    response["key_metrics"] = [4, 4, 4, 4]
    with pytest.raises(JudgeParseError, match="key_metrics"):
        parse_judge_response(response)


def test_non_dict_response_rejected():
    with pytest.raises(JudgeParseError):
        parse_judge_response([])  # type: ignore[arg-type]


def test_missing_rationale_defaults_to_empty():
    """rationale은 선택 항목이므로 없어도 빈 문자열로 파싱되는지 검증"""
    response = make_judge_response()
    del response["problem"]["rationale"]
    result = parse_judge_response(response)
    assert result["problem"].rationale == ""
