"""
생성 캔버스 디스크 캐시 — judge 실험이 캔버스를 재생성하지 않도록

self-consistency(N=5) x 30개 = judge 150콜이 돌아도 캔버스 생성은 30콜로 고정
키는 sha256(생성 모델 + 아이디어), 런 디렉토리 밖에 공유 저장하여 실험 간 재사용
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from lean_canvas.evaluation.models import EvalDatasetItem
from lean_canvas.generator import LeanCanvasGenerator
from lean_canvas.models import LeanCanvas


class CanvasCache:
    """아이디어 -> 생성 캔버스의 파일 캐시"""

    def __init__(self, root: Path, enabled: bool = True) -> None:
        self._root = Path(root)
        self._enabled = enabled
        self._root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def key(gen_model: str, idea: str) -> str:
        # 해시화
        digest = hashlib.sha256(f"{gen_model}\n{idea}".encode("utf-8"))
        return digest.hexdigest()[:16]

    def _path(self, gen_model: str, idea: str) -> Path:
        return self._root / f"{self.key(gen_model, idea)}.json"

    def get(self, gen_model: str, idea: str) -> LeanCanvas | None:
        """캐시 적중 시 캔버스 복원, 미적중·비활성 시 None"""
        if not self._enabled:
            return None
        path = self._path(gen_model, idea)
        if not path.exists():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        return LeanCanvas(**payload["canvas"])

    def put(
        self,
        gen_model: str,
        idea: str,
        canvas: LeanCanvas,
        item_id: str = "",
    ) -> None:
        payload = {
            "item_id": item_id,       # 사람이 캐시 파일을 식별할 수 있게 기록
            "gen_model": gen_model,
            "idea": idea,
            "canvas": asdict(canvas),
        }
        self._path(gen_model, idea).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def get_or_generate(
        self,
        item: EvalDatasetItem,
        generator: LeanCanvasGenerator,
        gen_model: str,
    ) -> LeanCanvas:
        """캐시 우선 조회, 미적중 시 생성 후 저장"""
        cached = self.get(gen_model, item.idea)
        if cached is not None:
            return cached
        canvas = generator.generate(item.idea)
        self.put(gen_model, item.idea, canvas, item_id=item.id)
        return canvas
