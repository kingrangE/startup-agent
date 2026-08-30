"""CLI entrypoint for the research-grounded LangGraph agent."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

from lean_canvas.llm.base import LLMError
from separk.agent.factory import create_research_agent
from separk.agent.renderers import render_markdown


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="separk-agent",
        description="A.X·LangGraph·Google/DDG·BGE 기반 근거 검증 린캔버스 에이전트",
    )
    parser.add_argument("interest", help="구체화할 창업 관심사")
    parser.add_argument("-i", "--instruction", action="append", default=[])
    parser.add_argument("--provider", choices=("ax", "openai"), default=None)
    parser.add_argument("--model", default=None)
    parser.add_argument("--require-google", action="store_true")
    parser.add_argument("--top-k", type=int, default=8)
    parser.add_argument("--max-revisions", type=int, default=2)
    parser.add_argument("--markdown-output", type=Path)
    parser.add_argument("--json-output", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    args = parse_args(argv)
    try:
        agent = create_research_agent(
            provider=args.provider,
            model=args.model,
            require_google=args.require_google,
            top_k=args.top_k,
            max_revisions=args.max_revisions,
        )
        result = agent.run(args.interest, tuple(args.instruction))
    except (ValueError, RuntimeError, LLMError) as exc:
        print(f"오류: {exc}", file=sys.stderr)
        return 1

    markdown = render_markdown(result)
    print(markdown)
    if args.markdown_output:
        args.markdown_output.write_text(markdown, encoding="utf-8")
    if args.json_output:
        args.json_output.write_text(
            json.dumps(result.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
