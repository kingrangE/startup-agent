"""
실험 결과 영속화 — run 디렉토리 관리 + ReportWriter Strategy

renderers.py의 CanvasRenderer와 동일한 Strategy 구조. 모든 실험은 공통
payload 형식을 만들고, JSON(재집계용)과 Markdown(사람용 리포트)으로 쓴다.

payload 형식:
  {
    "experiment": str,
    "title": str,
    "config": dict,
    "metrics": [{"name": str, "value": str, "target": str, "passed": bool|None}],
    "notes": [str],
    ...실험별 추가 필드
  }
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path

from evals.config import EvalConfig


class ReportWriter(ABC):
    """실험 결과 출력 형식 공통 인터페이스"""

    @abstractmethod
    def write(self, run_dir: Path, payload: dict) -> Path:
        raise NotImplementedError


class JsonReportWriter(ReportWriter):
    """재집계/추세 분석용 JSON 리포트"""

    def write(self, run_dir: Path, payload: dict) -> Path:
        path = run_dir / "metrics.json"
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return path


class MarkdownReportWriter(ReportWriter):
    """사람이 읽는 Markdown 리포트 — 메트릭|값|목표|판정 표"""

    def write(self, run_dir: Path, payload: dict) -> Path:
        lines = [f"# {payload['title']}", ""]
        lines.append(f"- 실행 디렉토리: `{run_dir.name}`")
        for key, value in payload.get("config", {}).items():
            lines.append(f"- {key}: `{value}`")
        lines.append("")

        lines.append("| 메트릭 | 값 | 목표 | 판정 |")
        lines.append("| --- | --- | --- | --- |")
        for metric in payload.get("metrics", []):
            passed = metric.get("passed")
            mark = "—" if passed is None else ("PASS" if passed else "FAIL")
            lines.append(
                f"| {metric['name']} | {metric['value']} | {metric['target']} | {mark} |"
            )
        lines.append("")

        for note in payload.get("notes", []):
            lines.append(f"> {note}")
            lines.append("")

        path = run_dir / "report.md"
        path.write_text("\n".join(lines), encoding="utf-8")
        return path


def prepare_run_dir(config: EvalConfig, experiment: str) -> Path:
    """타임스탬프 run 디렉토리를 만들고 config.json 기록"""
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = Path(config.results_root) / f"{stamp}-{experiment}"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "config.json").write_text(
        json.dumps(config.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return run_dir


def save_raw(run_dir: Path, raw: dict) -> Path:
    """항목별 원점수 저장 — 추후 임계값을 바꿔 재집계할 때 사용"""
    path = run_dir / "raw_scores.json"
    path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def write_reports(run_dir: Path, payload: dict) -> None:
    """JSON + Markdown 두 형식으로 리포트 작성"""
    for writer in (JsonReportWriter(), MarkdownReportWriter()):
        writer.write(run_dir, payload)


def list_results(results_root: Path) -> list[dict]:
    """results/ 아래의 모든 런을 시간순 요약"""
    summaries = []
    root = Path(results_root)
    if not root.exists():
        return summaries
    for metrics_path in sorted(root.glob("*/metrics.json")):
        payload = json.loads(metrics_path.read_text(encoding="utf-8"))
        metrics = payload.get("metrics", [])
        judged = [m for m in metrics if m.get("passed") is not None]
        summaries.append(
            {
                "run": metrics_path.parent.name,
                "title": payload.get("title", ""),
                "passed": sum(1 for m in judged if m["passed"]),
                "total": len(judged),
            }
        )
    return summaries
