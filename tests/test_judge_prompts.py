"""judge 채점 프롬프트 검증 — rubric 앵커 / few-shot / 스키마 포함 여부 검증"""

from __future__ import annotations

import pytest

from lean_canvas.evaluation.judge_prompts import JudgePromptBuilder
from lean_canvas.evaluation.rubric import DIMENSION_TITLES_KO, DIMENSIONS, RUBRIC
from lean_canvas.models import LeanCanvas


def test_system_prompt_contains_full_rubric_anchors():
    """시스템 프롬프트에 4차원 x 1~5점 앵커표가 전부 들어가는지 확인"""
    system = JudgePromptBuilder().build_system_prompt()
    for dim in DIMENSIONS:
        assert DIMENSION_TITLES_KO[dim] in system
        for score in range(1, 6):
            assert RUBRIC[dim][score] in system


def test_system_prompt_contains_anti_authority_bias_instruction():
    """구체성,권위 편향 대응 — 출처 사실성 검증 지시가 포함되는지 검증"""
    system = JudgePromptBuilder().build_system_prompt()
    assert "사실성" in system


def test_few_shot_examples_included():
    builder = JudgePromptBuilder().with_few_shot("예시 답안 → specificity 5점")
    assert "예시 답안 → specificity 5점" in builder.build_system_prompt()


def test_user_prompt_contains_canvas_and_schema(fake_canvas):
    """사용자 프롬프트에 관심사/9블록 키/출력 스키마가 모두 들어가는지 검증"""
    user = JudgePromptBuilder().with_canvas(fake_canvas).build_user_prompt()
    assert fake_canvas.interest in user
    for key in LeanCanvas.block_titles():
        assert f'"{key}"' in user  # 출력 스키마의 블록 키
        assert f"[{key}]" in user  # 채점 대상 본문의 블록 표기
    for dim in DIMENSIONS:
        assert dim in user


def test_user_prompt_without_canvas_raises():
    with pytest.raises(ValueError):
        JudgePromptBuilder().build_user_prompt()


def test_retry_feedback_appended(fake_canvas):
    """재시도 시 직전 위반 내용이 사용자 프롬프트에 붙는지"""
    builder = (
        JudgePromptBuilder()
        .with_canvas(fake_canvas)
        .with_retry_feedback("'problem.evidence' 점수가 정수가 아닙니다")
    )
    user = builder.build_user_prompt()
    assert "스키마를 위반했습니다" in user
    assert "'problem.evidence' 점수가 정수가 아닙니다" in user


def test_build_returns_system_and_user_messages(fake_canvas):
    """build()가 기존 LeanCanvasPromptBuilder와 동일한 메시지 형식을 따르는지 확인"""
    messages = JudgePromptBuilder().with_canvas(fake_canvas).build()
    assert [m["role"] for m in messages] == ["system", "user"]
