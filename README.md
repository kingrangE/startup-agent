# 창업 린 캔버스 생성기

사용자의 창업 관심사를 입력받아 LLM으로 창업용 린 캔버스 9개 블록을 자동 생성하는 도구입니다.

## Install

```bash
pip install -r requirements.txt
copy .env.example .env   # 이후 .env에 OPENAI_API_KEY 입력
```

## 사용법

```bash
# 대화형 입력
python main.py

# 관심사를 인자로 전달
python main.py "반려동물 헬스케어"

# 추가 지침과 함께 마크다운 파일로 저장
python main.py "비건 베이커리" -i "국내 시장 한정" -o canvas.md

# 모델 변경
python main.py "시니어 케어 플랫폼" -m gpt-4o
```

## 구조 및 디자인 패턴

```
lean_canvas/
├── models.py          # 불변 도메인 모델
├── prompts.py         # LeanCanvasPromptBuilder — Builder 패턴
├── llm/
│   ├── base.py        # LLMClient 추상 인터페이스 — Strategy 패턴
│   └── openai_client.py  # OpenAILLMClient — OpenAI 구현체
├── renderers.py       # ConsoleRenderer / MarkdownRenderer — Strategy 패턴
├── generator.py       # LeanCanvasGenerator — Facade 패턴 + 생성자 주입(DI)
└── factory.py         # create_generator — Factory 패턴 (의존성 조립)
main.py                # CLI 진입점
```

| 패턴 | 적용 위치 | 목적 |
|---|---|---|
| Strategy | `LLMClient`, `CanvasRenderer` | LLM 제공자,출력 형식을 코드 수정 없이 교체 |
| Builder | `LeanCanvasPromptBuilder` | 프롬프트를 단계적으로 조립, 추가 지침 누적 |
| Facade | `LeanCanvasGenerator` | 프롬프트→호출→파싱 흐름을 단일 진입점으로 캡슐화 |
| Factory | `create_generator` | 환경설정 기반 의존성 조립을 한 곳에 집중 |
