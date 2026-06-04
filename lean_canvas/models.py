"""린 캔버스 도메인 모델."""

from __future__ import annotations

from dataclasses import dataclass, field, fields


@dataclass(frozen=True)
class LeanCanvas:
    """린 캔버스 9개 블록을 표현하는 도메인 모델"""

    interest: str                                                # 사용자가 입력한 창업 관심사 
    problem: list[str] = field(default_factory=list)             # 1. 문제 
    customer_segments: list[str] = field(default_factory=list)   # 2. 고객군
    unique_value_proposition: str = ""                           # 3. 고유 가치 제안
    solution: list[str] = field(default_factory=list)            # 4. 솔루션
    channels: list[str] = field(default_factory=list)            # 5. 채널
    revenue_streams: list[str] = field(default_factory=list)     # 6. 수익원
    cost_structure: list[str] = field(default_factory=list)      # 7. 비용 구조
    key_metrics: list[str] = field(default_factory=list)         # 8. 핵심 지표
    unfair_advantage: str = ""                                   # 9. 경쟁 우위

    # 블록 키 -> 한국어 제목 매핑
    _TITLES = {
        "problem": "문제 (Problem)",
        "customer_segments": "고객군 (Customer Segments)",
        "unique_value_proposition": "고유 가치 제안 (Unique Value Proposition)",
        "solution": "솔루션 (Solution)",
        "channels": "채널 (Channels)",
        "revenue_streams": "수익원 (Revenue Streams)",
        "cost_structure": "비용 구조 (Cost Structure)",
        "key_metrics": "핵심 지표 (Key Metrics)",
        "unfair_advantage": "경쟁 우위 (Unfair Advantage)",
    }

    @classmethod
    def block_titles(cls) -> dict[str, str]:
        return dict(cls._TITLES)

    @classmethod
    def from_dict(cls, interest: str, data: dict) -> "LeanCanvas":
        """JSON dict 검증, 도메인 모델로 변환"""
        valid_keys = {f.name for f in fields(cls) if f.init and f.name != "interest"}
        kwargs = {}
        for key in valid_keys:
            value = data.get(key)
            if value is None:
                continue
            # 문자열 필드에 리스트가 오거나 그 반대인 경우를 보정
            if key in ("unique_value_proposition", "unfair_advantage"):
                kwargs[key] = " ".join(value) if isinstance(value, list) else str(value)
            else:
                kwargs[key] = [str(v) for v in value] if isinstance(value, list) else [str(value)]
        return cls(interest=interest, **kwargs)

    def blocks(self) -> dict[str, list[str] | str]:
        """렌더링을 위해 키->값 순서대로 블록 반환"""
        return {key: getattr(self, key) for key in self._TITLES}
