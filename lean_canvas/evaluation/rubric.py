"""
judge 채점 기준

프롬프트는 이 정보로 빌딩되고, 집계는 이걸로 계산하며, 테스트는 이걸로 채점. 
"""

from __future__ import annotations

# 채점 4개 기준 — 프롬프트·파싱·집계 전반의 기준 순서
DIMENSIONS = ("specificity", "evidence", "coherence", "differentiation")

DIMENSION_TITLES_KO = {
    "specificity": "구체성 (Specificity)",
    "evidence": "근거성 (Evidence)",
    "coherence": "일관성 (Coherence)",
    "differentiation": "차별성 (Differentiation)",
}

# 점수 범위 (1~5)
SCORE_MIN = 1
SCORE_MAX = 5

# 기준 별 점수 가중치
WEIGHTS = {
    "evidence": 0.35,
    "coherence": 0.25,
    "specificity": 0.20,
    "differentiation": 0.20,
}

# 과락 — 어느 한 칸이라도 2.0미만이면 총점 상한을 3.0으로 제한
MIN_GUARD_THRESHOLD = 2.0
MIN_GUARD_CAP = 3.0

# canvas_score -> overall_verdict 매핑 임계값
VERDICT_THRESHOLDS = {
    "strong": 4.0,      # 이상이면 strong
    "acceptable": 2.8,  # 이상이면 acceptable, 미만이면 needs_work
}

# self-consistency 목표 — 동일 입력 N회 채점 시 표준편차 상한
SELF_CONSISTENCY_MAX_STD = 0.3

# 전체 평가 기준
# 양 끝점만 정의하면 중간 점수를 임의적으로 매겨 재현성이 깨지므로 1~5점 전부를 판별 가능한 기준으로 정의
RUBRIC: dict[str, dict[int, str]] = {
    "specificity": {
        1: '추상적 슬로건. 대상·맥락이 없음 ("모두를 위한 혁신 플랫폼")',
        2: '방향만 있음. 대상이 막연함 ("바쁜 직장인을 돕는 앱")',
        3: '대상은 특정되나 측정·검증 불가능한 진술 ("프리랜서 디자이너의 견적 작성을 돕는다")',
        4: '측정 가능한 진술이나 수치·범위가 비어 있음 ("견적 작성 시간을 줄인다")',
        5: '검증 가능한 정량 진술 ("견적 작성을 평균 30분에서 5분으로 단축")',
    },
    "evidence": {
        1: "근거 전무. 순수 추측",
        2: '본인 경험·직관에만 의존 ("내가 불편했으니까")',
        3: "정성적 근거 1개 (지인 1~2명 사례, 일화)",
        4: "외부 데이터 1개로 뒷받침되나 출처가 약함",
        5: "복수의 외부 데이터·사례로 교차 검증됨 (누적된 검색 결과 인용)",
    },
    "coherence": {
        1: "칸 간 직접 모순 (타깃 고객과 채널이 어긋남)",
        2: "명시적 모순은 없으나 칸들이 따로 놂 (논리적 연결 안 보임)",
        3: "절반 정도의 칸이 서로 연결됨",
        4: "대부분 정합하나 1개 칸이 약한 고리",
        5: "9칸이 하나의 가설로 논리적으로 정합 (문제→솔루션→가치→수익이 일관)",
    },
    "differentiation": {
        1: "경쟁사와 구분 안 됨. 기존 제품 그대로",
        2: "차별점 주장은 있으나 모방 쉬움 (가격·UI 정도)",
        3: "차별점이 있으나 지속 가능성 불명",
        4: "명확한 차별점, 단 진입장벽(해자)이 약함",
        5: "명확한 차별점 + 모방 어려운 구조적 우위",
    },
}


def rubric_table_text(dimension: str) -> str:
    """한 차원의 1~5점 앵커표를 프롬프트 삽입용 텍스트로 렌더"""
    lines = [f"### {DIMENSION_TITLES_KO[dimension]}"]
    for score in range(SCORE_MIN, SCORE_MAX + 1):
        lines.append(f"- {score}점: {RUBRIC[dimension][score]}")
    return "\n".join(lines)
