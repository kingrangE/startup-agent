# 창업 린 캔버스 생성·평가 시스템

사용자의 창업 아이디어로 9-block 린 캔버스를 LLM이 생성하고, **생성된 캔버스의 품질을 LLM-as-a-Judge로 정량 측정**하는 시스템입니다. 단순 생성기가 아니라 *생성 + 측정* 한 쌍이 핵심이며, 측정 레이어(`lean_canvas/evaluation/` + `evals/`)가 이 프로젝트의 차별점입니다. 사용자 트래픽 없이도 시스템 품질을 회귀 추적할 수 있도록 judge의 일관성·인간 일치도·편향까지 검증 대상으로 둡니다.

## 빠른 시작

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt   # 테스트 실행용
cp .env.example .env                   # OPENAI_API_KEY / OPENAI_MODEL / JUDGE_MODEL 설정
```

**캔버스 생성**

```bash
python main.py "반려동물 헬스케어"
python main.py "비건 베이커리" -i "국내 시장 한정" -o canvas.md
python main.py "시니어 케어" -m gpt-4o
```

**평가 실험**

```bash
python -m evals generate-canvases              # 데이터셋 캔버스 일괄 생성 (캐시)
python -m evals run-judge-reliability --n 5    # judge self-consistency (σ ≤ 0.3)
python -m evals run-verdict-accuracy           # verdict 정확도 + Cohen's κ
python -m evals run-bias --limit 10            # 구체성·자기선호 편향
python -m evals run-pairwise --model-a gpt-4o-mini --model-b gpt-4o
python -m evals list-results                   # 누적 실험 결과 인덱스
```

## 시스템 한눈에

```
[입력 아이디어]
      │
      ▼
┌────────────────────────────────────────┐
│ Generation                             │
│  LeanCanvasPromptBuilder (Builder)     │
│   → LLMClient (Strategy: OpenAI)       │
│   → JSON parsing → LeanCanvas          │
│   → Renderer (Console / Markdown)      │
└────────────────────────────────────────┘
      │
      ▼
┌────────────────────────────────────────┐
│ Evaluation                             │
│  CanvasJudge (Facade)                  │
│   ├─ JudgePromptBuilder + few-shot     │
│   ├─ score_once() + 재시도(JSON 위반)  │
│   ├─ aggregation.canvas_score          │
│   │     · 4차원 가중평균 + min-guard   │
│   └─ map_verdict →                     │
│         strong / acceptable / needs_work│
│  부속 측정                              │
│   · self_consistency (N회, σ 측정)     │
│   · PairwiseJudge (position swap)      │
│   · metrics (MAE / κ / signed bias)    │
└────────────────────────────────────────┘
```

## 설계 결정과 트레이드오프

각 결정에는 구현 위치와 검증하는 테스트가 짝지어져 있습니다.

### 1. LLM-as-a-Judge — 측정 도구 자체도 검증한다

다차원 Likert 점수를 JSON으로 받는 형태의 judge(`lean_canvas/evaluation/judge.py`)를 채택했습니다. 선행 LLM-as-a-Judge 연구가 지적하는 *절대 점수 방식*의 두 약점(편향 취약, pairwise 대비 불안정)을 보완하기 위해 다음 세 축으로 judge 자신을 검증합니다.

- **few-shot 앵커링** — 1~5점 모든 척도에 실제 답안 예시를 박아 채점자 드리프트를 차단 (`judge_prompts.py`, `rubric.py`)
- **JSON 스키마 strict 파싱 + self-correction 재시도** — 응답이 스키마를 위반하면 위반 사유를 다시 프롬프트에 박아 최대 `max_retries`회 재시도 (`parsing.py`, `tests/test_judge.py`)
- **생성기 / judge 모델 분리** — `OPENAI_MODEL=gpt-4o-mini`로 생성하고 `JUDGE_MODEL=gpt-4o`로 채점해 자기 선호 편향(self-enhancement bias)을 줄임

### 2. 가중 다차원 집계 + min-guard 캡 (`aggregation.py`)

칸당 4개 차원을 다음 가중치로 합산합니다.

| 차원 | 가중치 | 선택 이유 |
|---|---|---|
| 근거성 (evidence) | 0.35 | 할루시네이션 차단·검증 가능성이 이 프로젝트의 1차 목표 |
| 일관성 (coherence) | 0.25 | 9칸이 단일 가설로 묶이는지 |
| 구체성 (specificity) | 0.20 | 측정 가능한 진술인지 |
| 차별성 (differentiation) | 0.20 | 모방 난이도 |

캔버스 총점은 9칸 점수 평균이되, **어느 한 칸이라도 2.0 미만이면 총점을 3.0으로 캡(min-guard)**합니다. 평균이 치명적 약점을 가리지 못하게 하기 위해서입니다.

> 명시한 트레이드오프: 근거성에 최대 가중치를 둔 선택은 *구체성·권위 편향*(허위 출처가 점수를 부당하게 올릴 위험)을 함께 키웁니다. 이 위험을 §6에서 별도 실험으로 측정합니다.

### 3. self-consistency — σ로 신뢰도 게이팅

같은 입력을 N회 채점해 차원별·총점 표준편차를 측정하고, σ ≤ 0.3 일 때만 신뢰 가능한 판정으로 간주합니다 (`judge.self_consistency`, `tests/test_self_consistency.py`). 단일 호출 점수를 그대로 신뢰하지 않는다는 의미입니다.

### 4. pairwise + position swap 디바이어싱 (`pairwise.py`)

A/B 두 캔버스를 judge에게 나란히 보여주고 어느 쪽이 더 나은지 묻습니다. 단일 호출 시 *앞 답안 선호* 현상이 있으므로 **순서를 바꿔 두 번 질의**하고, 결과가 뒤집히면 무승부로 처리합니다. 절대 점수 측정과 결과가 어긋날 때 점수 노이즈를 의심할 근거로 씁니다.

### 5. 인간 일치도 — 절대 점수 지표 + 우연 보정 (`evals/metrics.py`)

상관계수가 아니라 절대 점수차 지표를 씁니다. 시스템이 임계값(예: 4.0)으로 종료를 판정하기 때문에 *순위*가 아닌 *절대 위치*가 중요하기 때문입니다.

| 지표 | 정의 | 의미 |
|---|---|---|
| MAE | \|judge − human\| 평균 | 평균적 어긋남 |
| within-1 비율 | \|차이\| ≤ 1 비율 | 실용적 합치 정도 |
| signed bias | (judge − human) 평균 | judge가 후한가 / 박한가 (방향성) |
| Cohen's κ | 우연 보정된 verdict 일치도 | 단순 일치율의 chance level 보정 |

### 6. 편향 측정 — 약점을 능동적으로 검증

- **구체성·권위 편향**: 같은 캔버스에 *허위 출처·조작 수치*를 주입한 변형을 만들어 judge 점수가 부당하게 오르는지 측정 (`evals/experiments/bias.py`)
- **자기 선호 편향**: 생성 모델과 judge 모델을 분리해 같은 답안을 양쪽으로 채점, 점수 차이 모니터링

## 아키텍처와 디자인 패턴

| 패턴 | 적용 위치 | 목적 |
|---|---|---|
| Strategy | `LLMClient`, `CanvasRenderer` | LLM 제공자·출력 형식 교체를 코드 수정 없이 |
| Builder | `LeanCanvasPromptBuilder`, `JudgePromptBuilder` | 프롬프트 단계 조립, 재시도 시 self-correction 피드백 누적 |
| Facade | `LeanCanvasGenerator`, `CanvasJudge` | 프롬프트 → 호출 → 파싱 → 집계 흐름 단일 진입점 |
| Factory | `create_generator`, `create_judge` | 환경설정 기반 의존성 조립을 한곳에 |
| Immutable Value | `LeanCanvas` (frozen dataclass) | 생성 후 상태 변형 차단, 평가 입력 무결성 보장 |

## 디렉터리 구조

```
lean_canvas/
├── models.py                  # 불변 LeanCanvas
├── prompts.py                 # 생성 프롬프트 빌더
├── generator.py               # 생성 Facade
├── factory.py                 # 생성기·judge Factory
├── llm/
│   ├── base.py                # LLMClient 추상
│   └── openai_client.py       # OpenAI 구현
├── renderers.py               # Console / Markdown
└── evaluation/
    ├── models.py              # JudgeScore, CanvasEvaluation, Verdict
    ├── rubric.py              # 4차원 1~5점 앵커링, 가중치, 임계값
    ├── judge_prompts.py       # 평가 프롬프트 빌더 + few-shot
    ├── judge.py               # CanvasJudge Facade + self_consistency
    ├── parsing.py             # strict JSON 파싱
    ├── aggregation.py         # 가중 집계 + min-guard
    └── pairwise.py            # A/B 비교 + position swap
evals/
├── __main__.py                # CLI 진입점
├── config.py                  # EvalConfig
├── data/                      # YAML 평가 데이터셋
├── dataset.py                 # 데이터셋 로딩·검증
├── cache.py                   # 캔버스 생성 캐시
├── metrics.py                 # MAE, κ, accuracy 등
├── reporting.py               # markdown 리포트
├── results/                   # 누적 실험 결과
└── experiments/
    ├── generate.py            # 데이터셋 배치 생성
    ├── reliability.py         # self-consistency·verdict 정확도
    ├── bias.py                # 편향 실험
    └── pairwise_ab.py         # A/B 비교 실험
tests/                         # 12 모듈 (judge / 집계 / pairwise / 데이터셋 / metrics)
main.py                        # 생성 CLI
test.md                        # 측정 방법론 설계 문서
```

## 테스트

```bash
pytest tests/            # 전체
pytest tests/ -k judge   # 특정 영역
```

| 영역 | 모듈 |
|---|---|
| 공통 픽스처 / 헬퍼 | `conftest.py`, `helpers.py` (`ScriptedLLMClient`) |
| Judge 프롬프트·파싱 | `test_judge_prompts.py`, `test_parsing.py` |
| Judge facade·재시도 | `test_judge.py` |
| 집계·verdict | `test_aggregation.py`, `test_verdict_mapping.py` |
| Self-consistency | `test_self_consistency.py` |
| Pairwise + position swap | `test_pairwise.py` |
| 평가 지표 (MAE / κ) | `test_eval_metrics.py` |
| 데이터셋 검증 | `test_dataset.py` |
| 생성기 통합 | `test_generator_smoke.py` |

테스트는 외부 API를 호출하지 않습니다. `ScriptedLLMClient`가 사전 정의된 응답을 순차 반환하므로, 모든 평가 로직(재시도, 위치 스왑, σ 임계값 등)이 결정적으로 검증됩니다.

## 기술 스택

| 분류 | 사용 |
|---|---|
| 런타임 | `openai>=1.40.0`, `python-dotenv>=1.0.0`, `pyyaml>=6.0` |
| 테스트 | `pytest>=8.0` |
| 언어 | Python 3.10+ |

**의도적으로 채택하지 않은 것**

- **LangChain** — 프롬프트·체이닝 추상화를 거치지 않고 직접 제어. 디버깅 표면을 단순하게 유지하기 위함.
- **Pydantic** — frozen dataclass와 명시적 파싱(`parsing.py`)으로 충분.
- **Anthropic SDK** — 현재 OpenAI 단일 구현체. `LLMClient` 추상으로 교체 가능.

의존성을 적게 두는 만큼 라이브러리 버전 마이그레이션 리스크와 디버깅 표면이 줄어듭니다.

## 현재 한계와 다음 단계

- **인간 라벨 의존**: judge 인간 일치도 측정은 20~30개 데이터셋에 4차원 1~5점 라벨이 선행되어야 함. 라벨 자체의 일관성(rater agreement)은 아직 측정 대상이 아님.
- **OpenAI 단일 백엔드**: `LLMClient` 추상으로 Anthropic·로컬 모델 교체를 열어 뒀으나 실제 구현체는 OpenAI 하나.
- **편향 실험 범위**: 구체성·자기선호 두 편향에 집중. 길이 편향(verbosity bias) 등은 다음 라운드.
- **비용·지연 메트릭 미수집**: `test.md` §6.7에 정의돼 있으나 자동 집계는 미구현.

## 참고

- 측정 체계 설계의 상세 근거와 가중치·임계값 선택 이유: `test.md` §6 "측정 체계"
- 데이터셋 라벨링 가이드: `evals/dataset.py` docstring, `evals/data/*.yaml` 주석
