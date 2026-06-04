"""창업 린 캔버스 생성기 CLI 진입점.

사용법:
    python main.py                          # 대화형 입력
    python main.py "반려동물 헬스케어"        # 인자로 관심사 전달
    python main.py "비건 베이커리" -o out.md  # 마크다운 파일로 저장
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

from lean_canvas.factory import create_generator
from lean_canvas.llm.base import LLMError
from lean_canvas.renderers import ConsoleRenderer, MarkdownRenderer


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="창업 관심사로 린 캔버스를 생성합니다.")
    parser.add_argument("interest", nargs="?", help="창업 관심사 (생략 시 대화형 입력)")
    parser.add_argument(
        "-i", "--instruction", action="append", default=[],
        help="추가 지침 (여러 번 지정 가능, 예: -i '국내 시장 한정')",
    )
    parser.add_argument("-m", "--model", help="사용할 OpenAI 모델 (기본: gpt-4o-mini)")
    parser.add_argument("-o", "--output", help="마크다운으로 저장할 파일 경로")
    return parser.parse_args()


def main() -> int:
    load_dotenv()
    args = parse_args()

    interest = args.interest
    if not interest:
        try:
            interest = input("창업 관심사를 입력하세요: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n취소되었습니다.")
            return 1

    try:
        generator = create_generator(model=args.model)
        print("\n린 캔버스를 생성하는 중입니다...\n")
        canvas = generator.generate(interest, extra_instructions=args.instruction)
    except (ValueError, RuntimeError, LLMError) as e:
        print(f"오류: {e}", file=sys.stderr)
        return 1

    print(ConsoleRenderer().render(canvas))

    if args.output:
        path = Path(args.output)
        path.write_text(MarkdownRenderer().render(canvas), encoding="utf-8")
        print(f"\n마크다운 파일 저장 완료: {path.resolve()}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
