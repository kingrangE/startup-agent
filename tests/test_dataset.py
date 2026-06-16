"""데이터셋 로딩/검증 테스트, 실제 YAML 파일 + 스키마 위반 케이스"""

from __future__ import annotations

from pathlib import Path

import pytest

from evals.dataset import DatasetError, load_dataset, parse_dataset
from lean_canvas.evaluation.models import Verdict

DATASET_PATH = Path(__file__).parent.parent / "evals" / "data" / "eval_dataset.yaml"


def _valid_entry(**overrides) -> dict:
    entry = {
        "id": "good-99",
        "idea": "테스트 아이디어",
        "category": "good",
        "expected_verdict": "strong",
        "human_scores": None,
        "notes": "",
    }
    entry.update(overrides)
    return entry


class TestRealDatasetFile:
    """저장소에 들어 있는 실제 데이터셋 파일의 무결성 검증"""

    def test_loads_with_20_to_30_items(self):
        # Dataset load 개수 검사
        items = load_dataset(DATASET_PATH)
        assert 20 <= len(items) <= 30

    def test_ids_unique_and_categories_balanced(self):
        # test id 고유성과 분류 모두 존재 여부 검사
        items = load_dataset(DATASET_PATH)
        ids = [item.id for item in items]
        assert len(ids) == len(set(ids))
        # 좋은/애매/나쁜 세 범주가 모두 존재해야 함
        categories = {item.category for item in items}
        assert categories == {"good", "ambiguous", "bad"}

    def test_bad_items_never_expect_strong(self):
        """나쁜 아이디어에 strong 기대 라벨이 붙는지 검사"""
        items = load_dataset(DATASET_PATH)
        for item in items:
            if item.category == "bad":
                assert item.expected_verdict is not Verdict.STRONG


class TestParseValidation:
    """스키마 위반이 위치를 명시한 DatasetError로 잡히는지 검증"""

    def test_valid_entry_parses(self):
        items = parse_dataset([_valid_entry()])
        assert items[0].id == "good-99"
        assert items[0].expected_verdict is Verdict.STRONG
        assert items[0].human_scores is None

    def test_human_scores_parsed_when_present(self):
        entry = _valid_entry(
            human_scores={
                "specificity": 4, "evidence": 3, "coherence": 4, "differentiation": 3,
            }
        )
        items = parse_dataset([entry])
        assert items[0].human_scores == {
            "specificity": 4, "evidence": 3, "coherence": 4, "differentiation": 3,
        }

    def test_duplicate_id_rejected(self):
        with pytest.raises(DatasetError, match="중복"):
            parse_dataset([_valid_entry(), _valid_entry()])

    def test_invalid_category_rejected(self):
        with pytest.raises(DatasetError, match="category"):
            parse_dataset([_valid_entry(category="great")])

    def test_invalid_verdict_rejected(self):
        with pytest.raises(DatasetError, match="expected_verdict"):
            parse_dataset([_valid_entry(expected_verdict="excellent")])

    def test_partial_human_scores_rejected(self):
        """human_scores는 있으면 4차원 전부 있어야 한다."""
        with pytest.raises(DatasetError, match="누락된 차원"):
            parse_dataset([_valid_entry(human_scores={"specificity": 4})])

    def test_out_of_range_human_score_rejected(self):
        entry = _valid_entry(
            human_scores={
                "specificity": 6, "evidence": 3, "coherence": 4, "differentiation": 3,
            }
        )
        with pytest.raises(DatasetError, match="specificity"):
            parse_dataset([entry])

    def test_empty_dataset_rejected(self):
        with pytest.raises(DatasetError):
            parse_dataset([])
