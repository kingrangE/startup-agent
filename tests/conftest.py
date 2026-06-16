"""pytest 공용 fixture"""

from __future__ import annotations

import pytest

from lean_canvas.models import LeanCanvas


@pytest.fixture
def fake_canvas() -> LeanCanvas:
    """채점 대상 고정 캔버스"""
    return LeanCanvas(
        interest="반려동물 헬스케어",
        problem=["만성질환 반려동물의 투약 누락", "보호자-수의사 간 기록 단절"],
        customer_segments=["만성질환 반려동물 보호자", "동네 동물병원 수의사"],
        unique_value_proposition="투약·식이 기록을 수의사와 실시간 공유",
        solution=["투약 알림 및 기록", "수의사 공유 리포트"],
        channels=["동물병원 제휴", "반려인 커뮤니티"],
        revenue_streams=["월 구독", "병원 B2B 라이선스"],
        cost_structure=["개발 인건비", "서버 비용"],
        key_metrics=["주간 기록률", "병원 연동 수"],
        unfair_advantage="병원 제휴망 기반 진료 데이터 연동",
    )
