"""린 캔버스 출력 렌더러 — Strategy 패턴."""

from __future__ import annotations

from abc import ABC, abstractmethod

from lean_canvas.models import LeanCanvas


class CanvasRenderer(ABC):
    """캔버스 출력 형식 공통 인터페이스"""

    @abstractmethod
    def render(self, canvas: LeanCanvas) -> str:
        raise NotImplementedError


class ConsoleRenderer(CanvasRenderer):
    """터미널 출력용 텍스트 렌더러"""

    _WIDTH = 70

    def render(self, canvas: LeanCanvas) -> str:
        lines = [
            "=" * self._WIDTH,
            f"  창업 린 캔버스: {canvas.interest}",
            "=" * self._WIDTH,
        ]
        titles = LeanCanvas.block_titles()
        for key, value in canvas.blocks().items():
            lines.append("")
            lines.append(f"[{titles[key]}]")
            if isinstance(value, list):
                lines.extend(f"  - {item}" for item in value)
            else:
                lines.append(f"  {value}")
        lines.append("")
        lines.append("=" * self._WIDTH)
        return "\n".join(lines)


class MarkdownRenderer(CanvasRenderer):
    """파일 저장용 마크다운 렌더러"""

    def render(self, canvas: LeanCanvas) -> str:
        lines = [f"# 창업 린 캔버스: {canvas.interest}", ""]
        titles = LeanCanvas.block_titles()
        for key, value in canvas.blocks().items():
            lines.append(f"## {titles[key]}")
            lines.append("")
            if isinstance(value, list):
                lines.extend(f"- {item}" for item in value)
            else:
                lines.append(f"> {value}")
            lines.append("")
        return "\n".join(lines)
