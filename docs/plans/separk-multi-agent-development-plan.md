# SePark 멀티에이전트 개발 계획

> 문서 상태: 실행 계획 초안 1.0<br>
> 기준 저장소: `master@9a312f3`<br>
> 제품명: **SePark**<br>
> 목표 릴리스: 포트폴리오 공개용 `v1.0.0`<br>
> 원칙: Agent는 독립 worktree와 브랜치에서 작업하고, 통합 Coordinator만 공유 파일을 수정한다.

## 1. 문서 목적

이 문서는 현재 CLI 중심의 린 캔버스 생성·평가 코드를 다음 상태로 발전시키기 위한 실행 계획이다.

- GitHub에서 안전하게 공개할 수 있는 코드 저장소
- 공유 URL로 누구나 체험할 수 있는 Streamlit 웹 앱
- `아이디어 찾기`와 `기존 아이디어 구체화`의 두 진입 경로
- 생성 → 평가 → 확인 질문 → 개선 → 전후 비교의 반복 흐름
- 인간 평가, 신뢰도, 편향, 비용 및 지연시간을 공개할 수 있는 평가 체계
- 여러 Agent가 파일 충돌 없이 동시에 개발할 수 있는 브랜치 구조

이 문서는 단순 백로그가 아니다. 각 브랜치의 파일 소유권, 선행 조건, 완료 기준, 검증 명령과 병합 순서를 함께 정의한다.

## 2. 제품 정의

### 2.1 한 문장 문제 정의

> SePark는 아이디어가 없거나 막연한 예비 창업자가 자신의 관심사와 기존 구상을 검증 가능한 사업 가설로 구체화하고, 취약한 가설을 반복 개선하도록 돕는 AI 코치다.

### 2.2 핵심 사용자 흐름

```text
아이디어 없음
  → 관심사·경험·가용 자원·제약 입력
  → 후보 아이디어 3개 제안
  → 후보 선택
                                    ┐
                                    ├→ 린 캔버스 v1
기존 아이디어 있음                  │
  → 기존 기획 입력                  │
  → 핵심 가설·누락 정보 추출        ┘
  → 블록별 평가와 취약점 표시
  → 확인 질문 최대 3개
  → 사용자 답변
  → 린 캔버스 v2
  → 변경 내용·점수 변화·남은 가설 비교
  → Markdown/JSON 다운로드
```

### 2.3 포트폴리오에서 증명할 내용

- 단순 LLM 생성기가 아니라 평가와 개선 루프를 설계했다.
- Judge의 점수를 그대로 믿지 않고 일관성·인간 일치도·편향을 검증했다.
- API 비용, 지연시간, 오류와 공개 서비스 악용 가능성을 운영 관점에서 다뤘다.
- 검증되지 않은 사실과 AI의 추론을 구분하고 제품의 한계를 공개했다.

## 3. 현재 기준선

### 3.1 구현된 영역

- 관심사와 추가 지침을 받아 9블록 `LeanCanvas` 생성
- OpenAI 기반 JSON 응답 처리
- Console/Markdown 렌더링
- LLM-as-a-Judge 4차원 평가
- 가중 집계, min-guard, verdict 매핑
- self-consistency, pairwise position swap
- 인간 일치도 및 편향 측정 로직
- good/ambiguous/bad 각 8개, 총 24개 평가 데이터셋
- 외부 API 없이 실행되는 다수의 단위 테스트

### 3.2 공개를 막는 결함

- `lean_canvas.factory`에 `create_judge`, `create_pairwise_judge`가 없어 전체 테스트 수집과 평가 CLI가 실패한다.
- 실제 import되는 `PyYAML`과 테스트 의존성이 설치 정의에 빠져 있다.
- `.gitignore`가 `.env`, 가상환경, 캐시, 빌드 결과를 보호하지 않는다.
- README가 존재하지 않는 `requirements-dev.txt`, `test.md`를 참조한다.
- 인간 점수 24개가 모두 `null`이고 실제 평가 리포트가 없다.
- 웹 UI, CI, 패키징, 라이선스와 배포 설정이 없다.
- 해커톤 당시의 아이디어 후보 제안과 기존 기획 구체화 흐름이 현재 코드에는 없다.

### 3.3 확인된 검증 상태

- `compileall`: 통과
- 문제가 되는 평가 메트릭 모듈을 제외한 테스트: `56 passed`
- 전체 테스트: factory import 오류로 수집 단계 실패
- 실제 OpenAI API 기반 E2E: 아직 검증하지 않음

## 4. 범위와 비범위

### 4.1 v1 필수 범위

- 두 진입 모드
- 아이디어 후보 3개 제안
- 린 캔버스 v1 생성 및 평가
- 취약 블록 기반 확인 질문
- 사용자 답변을 반영한 v2 생성 및 재평가
- v1/v2 비교와 Markdown/JSON 내보내기
- API 키 없이 가능한 샘플 세션
- 공개 URL, GitHub 저장소, CI와 실제 평가 리포트

### 4.2 v1 비범위

- 사용자 계정과 영구 데이터베이스
- 팀 협업 기능
- 결제
- 모바일 네이티브 앱
- 다중 LLM 제공자 완성
- 시장조사의 사실성을 완전히 보장하는 자동 시스템
- 기존 `lean_canvas` 패키지의 전면적인 `separk` rename

`SePark`는 우선 제품명과 새 응용 계층 이름으로 사용한다. 기존 `lean_canvas` 패키지는 v1에서 유지해 불필요한 대규모 rename과 병합 충돌을 피한다.

## 5. 목표 아키텍처와 계약

```text
lean_canvas/                     기존 생성·평가 코어
├── models.py                    LeanCanvas — 변경 최소화
├── generator.py                생성 Facade
├── evaluation/                 Judge와 평가 모델
└── llm/                        LLMClient 구현

separk/                          새 제품 응용 계층
├── application/                공용 DTO, Protocol, 오케스트레이션
├── intake/                     아이디어 탐색·기존 기획 입력
├── refinement/                 취약점 질문·답변 반영·버전 비교
├── runtime/                    호출 제한·캐시·안전 정책
├── presentation/               Markdown/JSON export
└── ui/                         Streamlit 상태와 화면 컴포넌트

evals/                           오프라인 평가 및 실험
streamlit_app.py                 공개 웹 진입점
```

### 5.1 병렬 개발 전에 고정할 공용 모델

- `EntryMode`: `IDEA_DISCOVERY`, `EXISTING_PLAN`
- `IdeaProfile`: 관심사, 경험, 가용 자원, 제약
- `IdeaCandidate`: id, 제목, 설명, 고객, 문제, 적합 이유
- `PlanningBrief`: 진입 모드, 원문, 선택 아이디어, 추가 제약
- `ClarificationQuestion`: id, 대상 블록, 질문, 질문 이유
- `ClarificationAnswer`
- `CanvasVersion`: 버전, `LeanCanvas`, `CanvasEvaluation`, 변경 요약
- `SessionSnapshot`: 단계, 후보, 버전 이력, 미응답 질문

### 5.2 병렬 개발 전에 고정할 Protocol

```python
class CanvasGeneratorPort(Protocol):
    def generate(
        self,
        interest: str,
        extra_instructions: list[str] | None = None,
    ) -> LeanCanvas: ...


class CanvasEvaluatorPort(Protocol):
    def evaluate(self, canvas: LeanCanvas) -> CanvasEvaluation: ...


class IdeaDiscoveryPort(Protocol):
    def suggest(
        self,
        profile: IdeaProfile,
        limit: int = 3,
    ) -> tuple[IdeaCandidate, ...]: ...


class RefinementPort(Protocol):
    def questions(
        self,
        version: CanvasVersion,
        limit: int = 3,
    ) -> tuple[ClarificationQuestion, ...]: ...

    def refine(
        self,
        version: CanvasVersion,
        answers: tuple[ClarificationAnswer, ...],
    ) -> CanvasVersion: ...


class SeParkUseCases(Protocol):
    def suggest_ideas(...): ...
    def create_canvas(...): ...
    def ask_for_clarification(...): ...
    def refine_canvas(...): ...
```

기존 `LeanCanvas`, `CanvasEvaluation`, `LLMClient`의 공개 시그니처는 병렬 작업 중 변경하지 않는다. 새 DTO가 기존 객체를 감싸게 한다.

## 6. 전체 브랜치 토폴로지

```text
master + 이 계획 문서
  └─ integration/separk-v1
      ├─ fix/factory-wiring ────────────────┐
      ├─ chore/project-foundation ──────────┼─ Foundation Gate
      └─ docs/separk-baseline ──────────────┘
                                                ↓
                     feat/separk-product-contracts
                                                ↓
      ├─ feat/separk-intake ────────────────────┐
      ├─ feat/separk-refinement ────────────────┤
      ├─ feat/separk-web-runtime ───────────────┼─ Product Integration Gate
      └─ feat/separk-streamlit-ui ──────────────┘
                                                ↓
                         feat/separk-app-integration
                                                ↓
      ├─ feat/eval-human-labeling ──────────────┐
      ├─ feat/eval-observability ───────────────┼─ Evidence Gate
      └─ chore/separk-deploy ───────────────────┘
                         ↓                      ↓
                   사람 라벨 작업       공개 배포 URL
                         ↓                      ↓
                    results/eval-baseline ─────┐
                                               ├─ docs/portfolio-release
                                               ↓
                                      release/separk-v1.0.0
```

현재 실행 환경처럼 동시 슬롯이 4개라면 Coordinator 1명과 Worker 3명을 기준으로 파동을 나눈다. 네 번째 제품 브랜치는 먼저 끝난 Worker 슬롯을 재사용한다.

## 7. Wave 0 — 저장소 기반 정상화

세 브랜치는 현재 기준점에서 동시에 시작할 수 있다. 파일 소유권이 겹치지 않는다.

### 7.1 Agent F1 — Factory 복구

- 브랜치: `fix/factory-wiring`
- worktree: `../separk-factory`
- 독점 소유:
  - `lean_canvas/factory.py`
  - `tests/test_factory.py`
- 작업:
  - `create_judge(api_key=None, model=None)`
  - `create_pairwise_judge(api_key=None, model=None)`
  - 공통 API 키 해석
  - generator/judge 모델 우선순위 테스트
  - judge와 pairwise 평가 temperature 정책 명시
- 금지:
  - requirements, README, eval 실험 파일 수정
  - 실제 OpenAI API 호출
- 완료 기준:
  - 세 factory가 올바른 Facade 타입을 반환한다.
  - `JUDGE_MODEL`과 `OPENAI_MODEL` 우선순위가 테스트된다.
  - API 키가 없을 때 일관된 오류를 반환한다.
  - 평가 모듈의 import 오류가 사라진다.

권장 커밋:

1. `test(factory): add dependency wiring contract`
2. `fix(factory): wire canvas and pairwise judges`

### 7.2 Agent F2 — 패키징·의존성·CI

- 브랜치: `chore/project-foundation`
- worktree: `../separk-foundation`
- 독점 소유:
  - `pyproject.toml`
  - `requirements.txt`
  - `requirements-dev.txt`
  - `.gitignore`
  - `.env.example`
  - `.github/workflows/ci.yml`
- 작업:
  - 프로젝트 메타데이터 `separk`, 초기 버전 `0.1.0`
  - Python `>=3.10`
  - runtime: `openai`, `python-dotenv`, `PyYAML`
  - dev: `pytest`, `pytest-cov`, `build`
  - console scripts: `separk`, `separk-evals`
  - wheel에 `evals/data/*.yaml` 포함
  - Python 3.10/3.12 CI 매트릭스
  - 패키징·테스트·CLI smoke test
- `.gitignore` 최소 정책:
  - `.env`, `.env.*`, `!.env.example`
  - `.venv/`, `venv/`, `__pycache__/`, `*.py[cod]`
  - `.pytest_cache/`, `.coverage`, `htmlcov/`
  - `build/`, `dist/`, `*.egg-info/`
  - `evals/results/_canvas_cache/`
  - `graphify-out/`
- 완료 기준:
  - `pip install -e ".[dev]"`가 새 환경에서 성공한다.
  - `pytest -q`, `python -m build`가 CI에서 실행된다.
  - `separk --help`, `separk-evals --help`가 성공한다.
  - CI는 API 키와 유료 평가 호출을 요구하지 않는다.

권장 커밋:

1. `chore(packaging): define SePark project and dependencies`
2. `chore(repo): harden env example and gitignore`
3. `ci: add deterministic test and package workflow`

### 7.3 Agent F3 — SePark 문서 기준선

- 브랜치: `docs/separk-baseline`
- worktree: `../separk-docs`
- 독점 소유:
  - `README.md`
  - `docs/evaluation.md`
  - `CONTRIBUTING.md`
  - `LICENSE` — 사용자 라이선스 선택 후
- 작업:
  - 프로젝트명을 SePark로 통일
  - 현재 구현과 예정 기능을 분리
  - 존재하지 않는 파일 참조 제거
  - 현재 한계를 숨기지 않고 기록
  - 로컬 설치·테스트·CLI 사용법 갱신
  - 단위 테스트와 유료 API 평가의 차이 설명
- 완료 기준:
  - dead link와 존재하지 않는 명령이 없다.
  - 웹 데모가 없을 때 가짜 URL을 넣지 않는다.
  - CLI 전용, 인간 라벨 미완성, 실제 결과 없음, 근거 검색 미구현을 명시한다.
  - 라이선스는 사용자가 명시적으로 선택한다. 기본 제안은 MIT다.

### 7.4 Foundation Gate

병합 순서:

1. `chore/project-foundation`
2. `fix/factory-wiring`
3. `docs/separk-baseline`

통합 검증:

```bash
python -m pip install -e ".[dev]"
pytest -q
python -m build
separk --help
separk-evals --help
python -m evals list-results
git diff --check
```

추가 확인:

- `.env`, API 키, 캐시와 빌드 산출물이 추적되지 않는다.
- README 명령을 새 가상환경에서 그대로 실행할 수 있다.
- CI가 green이다.
- 이 Gate를 통과한 SHA를 이후 모든 제품 브랜치의 기준점으로 기록한다.

## 8. Wave 1 — 제품 계약 고정

### 8.1 Agent C1 — 공용 제품 계약

- 브랜치: `feat/separk-product-contracts`
- worktree: `../separk-contracts`
- 독점 소유:
  - `separk/__init__.py`
  - `separk/application/__init__.py`
  - `separk/application/models.py`
  - `separk/application/ports.py`
  - `tests/separk/application/test_models.py`
  - `docs/architecture/separk-product-contracts.md`
- 작업:
  - 5장의 DTO와 Protocol 구현
  - frozen dataclass 또는 동등한 불변 모델 사용
  - 직렬화 가능성과 입력 검증 정의
  - 기존 코어 모델을 변경하지 않고 참조
- 완료 기준:
  - 타입 계약 테스트가 외부 API 없이 통과한다.
  - UI는 fake `SeParkUseCases`만으로 개발할 수 있다.
  - intake, refinement, runtime Agent가 공용 모델을 새로 정의할 필요가 없다.

이 브랜치는 Wave 2의 공통 기준점이므로 작고 빠르게 병합한다.

## 9. Wave 2 — 제품 기능 병렬 개발

### 9.1 Agent P1 — 두 진입 모드

- 브랜치: `feat/separk-intake`
- worktree: `../separk-intake`
- 독점 소유:
  - `separk/intake/**`
  - `tests/separk/intake/**`
- 작업:
  - 관심사·경험·자원·제약 기반 후보 3개 생성
  - 후보 선택을 `PlanningBrief`로 변환
  - 기존 기획 원문과 제약을 손실 없이 `PlanningBrief`로 변환
  - strict JSON 파싱과 명시적 오류
  - `LLMClient` 생성자 주입
- 완료 기준:
  - 탐색 모드는 서로 다른 후보 정확히 3개를 반환한다.
  - 후보마다 고객, 문제, 적합 이유가 존재한다.
  - 기존 기획 원문이 보존된다.
  - 빈 입력과 과도한 입력을 거부한다.
  - fake LLM 테스트만 사용한다.

### 9.2 Agent P2 — 평가 기반 개선 루프

- 브랜치: `feat/separk-refinement`
- worktree: `../separk-refinement`
- 독점 소유:
  - `separk/refinement/**`
  - `tests/separk/refinement/**`
- 작업:
  - 가장 약한 블록 최대 3개 선정
  - 점수와 rationale 기반 확인 질문 생성
  - 답변과 이전 캔버스를 이용해 v2 생성
  - v1 불변 유지
  - v2 재평가와 블록별 diff
- 완료 기준:
  - 동점 우선순위가 결정적이다.
  - 질문에 대상 블록과 이유가 포함된다.
  - 미응답 상태에서는 재생성하지 않는다.
  - v1/v2 총점, verdict와 변경 블록을 비교할 수 있다.
  - UI가 “점수는 정답이 아닌 개선 우선순위 신호”라고 표시할 수 있다.

### 9.3 Agent P3 — 공개 runtime·캐시·내보내기

- 브랜치: `feat/separk-web-runtime`
- worktree: `../separk-runtime`
- 독점 소유:
  - `separk/runtime/**`
  - `separk/presentation/**`
  - `tests/separk/runtime/**`
  - `tests/separk/presentation/**`
- 작업:
  - 입력 길이, 세션 호출 수, timeout 제한
  - `LLMClient`를 감싸는 budget/cache wrapper
  - 입력+모델+프롬프트 버전 기반 TTL 캐시
  - Markdown/JSON export
- 권장 초기 정책:
  - 기존 기획 최대 6,000자
  - 세션당 실시간 사용자 액션 3회
  - timeout 30초
  - 기존 기획 원문은 디스크나 영구 캐시에 저장하지 않음
  - API 키는 캐시 키·로그·export에 포함하지 않음
- 완료 기준:
  - 제한 초과와 timeout이 사용자 친화적 오류로 변환된다.
  - 캐시 키에서 원문과 API 키가 노출되지 않는다.
  - 한글 Markdown/JSON이 보존된다.
  - 실험용 `evals.cache.CanvasCache`를 웹에서 재사용하지 않는다.
- 금지:
  - 이 Wave에서 `lean_canvas/llm/openai_client.py` 수정
  - root 의존성 파일 수정

### 9.4 Agent P4 — Streamlit UI

- 브랜치: `feat/separk-streamlit-ui`
- worktree: `../separk-ui`
- 독점 소유:
  - `streamlit_app.py`
  - `separk/ui/**`
  - `examples/demo_session.json`
  - `tests/separk/ui/**`
- 작업:
  - 두 진입 경로
  - 후보 3개 선택 화면
  - 9블록 캔버스와 평가 결과
  - 질문/답변 화면
  - v1/v2 비교와 다운로드 버튼
  - loading/error/retry/limit 상태
  - API 키 없는 샘플 세션
- 완료 기준:
  - fake `SeParkUseCases`만으로 전체 UI 흐름을 테스트한다.
  - 후보 선택 전 불필요한 재호출이 없다.
  - Streamlit rerun 시 `request_id`로 중복 생성을 막는다.
  - API 키가 없어도 샘플 세션을 끝까지 볼 수 있다.
  - 모바일 폭에서 핵심 정보가 가로 스크롤 없이 보인다.

### 9.5 Wave 2 슬롯 운용

Coordinator 포함 4슬롯 기준:

1. P1 intake, P2 refinement, P3 runtime을 동시에 시작한다.
2. 가장 먼저 끝난 Worker 슬롯에 P4 UI를 시작한다.
3. UI는 fake service를 사용하므로 P1~P3 병합을 기다리지 않는다.
4. 모든 Agent는 공용 계약 변경이 필요하면 직접 고치지 않고 Coordinator에게 RFC를 보낸다.

## 10. Wave 3 — 제품 통합

### 10.1 Agent I1 — 응용 서비스와 bootstrap

- 브랜치: `feat/separk-app-integration`
- worktree: `../separk-integration`
- Coordinator/통합 Agent 독점 소유:
  - `separk/application/service.py`
  - `separk/bootstrap.py`
  - `tests/separk/application/test_service.py`
  - `tests/separk/test_user_journey.py`
  - root 공유 파일의 통합 수정
- 조립:

```text
OpenAILLMClient
  → Budget/Cache wrapper
  → LeanCanvasGenerator + CanvasJudge
  → IntakeService + RefinementService
  → SeParkService
  → Streamlit UI
```

- 병합 권장 순서:
  1. `feat/separk-intake`
  2. `feat/separk-refinement`
  3. `feat/separk-web-runtime`
  4. `feat/separk-streamlit-ui`
- 완료 기준:
  - 두 사용자 경로가 fake LLM E2E로 통과한다.
  - 키가 없으면 앱이 죽지 않고 샘플 모드로 진입한다.
  - 실시간 모드에는 timeout·호출 제한·캐시가 적용된다.
  - `streamlit run streamlit_app.py --server.headless true`가 기동한다.
  - 의존성 추가는 이 브랜치에서 한 번만 반영한다.

## 11. Wave 4 — 평가 증거와 공개 준비

### 11.1 Agent E1 — 인간 라벨링 도구

- 브랜치: `feat/eval-human-labeling`
- worktree: `../separk-labeling`
- 독점 소유:
  - `evals/annotation.py`
  - `evals/experiments/generate.py`
  - `evals/data/annotations/**`
  - `docs/evaluation/labeling-guide.md`
  - `tests/test_annotations.py`
- 작업:
  - 채점 문서에서 category와 expected verdict를 숨겨 블라인드 처리
  - 생성 설정과 캔버스 hash 고정
  - 평가자 A/B 원본 라벨과 합의 라벨 분리
  - 누락·범위·중복 검증
  - 평가자 간 MAE·일치율 계산
- 코드 완료 기준:
  - 두 평가자의 24×4 점수 입력을 검증할 수 있다.
  - 라벨링 문서에 기대 범주가 노출되지 않는다.
  - 불일치 조정 내역과 평가 입력 hash를 남길 수 있다.
- 사람 작업 Gate:
  - 최소 2명의 사람이 24개 캔버스를 독립 채점한다.
  - Agent는 사람 점수를 추측하거나 자동 생성하지 않는다.
  - 합의 후에만 기존 `human_scores`에 반영한다.

### 11.2 Agent E2 — 비용·지연·재현성

- 브랜치: `feat/eval-observability`
- worktree: `../separk-observability`
- 독점 소유:
  - `lean_canvas/llm/openai_client.py`
  - `lean_canvas/llm/telemetry.py`
  - `lean_canvas/factory.py`
  - `evals/config.py`
  - `evals/reporting.py`
  - `evals/experiments/reliability.py`
  - `evals/experiments/bias.py`
  - `evals/experiments/pairwise_ab.py`
  - `tests/test_telemetry.py`
  - `tests/test_reporting.py`
- 선행 조건:
  - Wave 3 제품 통합 완료
  - prompt, rubric, generator model 버전 동결
- 수집 항목:
  - 호출 수, 성공/실패, 재시도
  - 입출력 토큰, latency, p50/p95, wall time
  - 캐시 hit/miss
  - 모델, temperature, SDK 버전
  - git SHA, dataset hash, rubric/prompt 버전
  - 실행 시점의 단가 스냅샷과 추정 비용
- 완료 기준:
  - `config.json`, `metrics.json`, `report.md`에 재현 정보가 포함된다.
  - API 키, 전체 프롬프트, 민감한 원문은 기록하지 않는다.
  - 가격은 영구 상수가 아니라 날짜가 있는 설정 스냅샷으로 관리한다.
  - 테스트는 외부 API 없이 통과한다.

### 11.3 Agent D1 — 배포

- 브랜치: `chore/separk-deploy`
- worktree: `../separk-deploy`
- 독점 소유:
  - `.streamlit/config.toml`
  - `docs/deployment.md`
  - 배포 smoke test
  - Streamlit Cloud 설정 안내
- 공유 파일 변경:
  - 필요한 dependency/env 변경은 직접 수정하지 않고 통합 Agent에게 목록 전달
- 완료 기준:
  - Streamlit Community Cloud에서 GitHub entrypoint로 배포한다.
  - API 키는 Streamlit Secrets에만 저장한다.
  - `.streamlit/secrets.toml`은 추적되지 않는다.
  - 빈 입력, 과도한 입력, timeout, 예산 소진 시 UI가 복구한다.
  - 샘플 모드는 항상 사용할 수 있다.
  - 배포 문서만으로 새 환경에 재배포할 수 있다.

참고:

- Streamlit 배포: <https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy>
- Streamlit Secrets: <https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management>
- OpenAI Responses 이전: <https://developers.openai.com/api/docs/guides/migrate-to-responses>

Responses API 이전은 공개를 막는 P0 결함이 아니다. Chat Completions 기반 v1이 안정화된 뒤 `feat/responses-api`라는 별도 브랜치에서 수행하고 동일 E2E·평가 기준으로 비교한다.

## 12. Wave 5 — 실제 평가 결과와 포트폴리오 릴리스

### 12.1 사람 및 비용 승인 Gate

다음 작업은 자동으로 시작하지 않는다.

- 사람 평가자 2명 섭외와 라벨 작성
- 실제 OpenAI API를 사용하는 24개 전체 평가
- 모델 A/B 비교
- 유료 배포 또는 외부 저장소 연결

실행 전에 Coordinator가 예상 호출 수, 모델, 비용 한도와 저장할 결과를 사용자에게 제시하고 승인을 받는다.

### 12.2 Agent R1 — 실제 baseline 결과

- 브랜치: `results/eval-baseline`
- worktree: `../separk-eval-results`
- 선행 조건:
  - 인간 합의 라벨 완료
  - observability 병합
  - generator/prompt/rubric 동결
- 독점 소유:
  - `evals/results/<fixed-run-id>/config.json`
  - `evals/results/<fixed-run-id>/metrics.json`
  - `evals/results/<fixed-run-id>/report.md`
  - `docs/evaluation/baseline-results.md`
- 실행 범위:
  - self-consistency
  - 인간 일치도
  - verdict accuracy, Cohen's kappa
  - 허위 출처 편향
  - 자기 선호 편향
  - pairwise A/B
  - 비용과 지연시간
- 완료 기준:
  - 24개 전체 데이터셋을 사용한다.
  - git SHA와 dataset hash를 기록한다.
  - 재실행 명령과 모델명을 공개한다.
  - PASS와 FAIL을 가리지 않고 그대로 기록한다.
  - `_canvas_cache`, API 원문, secret은 커밋하지 않는다.

### 12.3 Agent R2 — 포트폴리오 문서 최종화

- 브랜치: `docs/portfolio-release`
- worktree: `../separk-portfolio-docs`
- 독점 소유:
  - `README.md`
  - `docs/case-study.md`
  - `docs/architecture.md`
  - `docs/assets/**`
  - `LICENSE`
  - `SECURITY.md`
  - `CONTRIBUTING.md`
- 선행 조건:
  - 실제 배포 URL
  - 실제 baseline 평가 결과
- 완료 기준:
  - 제목과 화면 표기가 모두 SePark다.
  - README 첫 화면에 문제, Live Demo, GIF/스크린샷, 실행법이 있다.
  - 생성 → 평가 → 질문 → 개선 흐름을 설명한다.
  - 실제 평가 리포트를 링크한다.
  - 실패 사례, 기술적 결정과 한계를 공개한다.
  - 검증하지 않은 성능 수치와 시장 사실을 쓰지 않는다.
  - `TBD`, 깨진 링크와 로컬 전용 경로가 없다.

## 13. Worktree 생성 예시

먼저 이 계획 문서를 커밋하고 통합 브랜치를 만든다.

```bash
git switch master
git switch -c integration/separk-v1
```

Wave 0:

```bash
git worktree add ../separk-factory -b fix/factory-wiring integration/separk-v1
git worktree add ../separk-foundation -b chore/project-foundation integration/separk-v1
git worktree add ../separk-docs -b docs/separk-baseline integration/separk-v1
```

Foundation Gate 병합 후 기준 SHA에서 계약 브랜치를 만든다.

```bash
git worktree add ../separk-contracts -b feat/separk-product-contracts integration/separk-v1
```

계약 병합 후 제품 브랜치:

```bash
git worktree add ../separk-intake -b feat/separk-intake integration/separk-v1
git worktree add ../separk-refinement -b feat/separk-refinement integration/separk-v1
git worktree add ../separk-runtime -b feat/separk-web-runtime integration/separk-v1
git worktree add ../separk-ui -b feat/separk-streamlit-ui integration/separk-v1
```

주의:

- 각 명령의 마지막 인자는 반드시 최신 Gate가 병합된 `integration/separk-v1`이어야 한다.
- 이미 다른 worktree에서 checkout된 브랜치를 재사용하지 않는다.
- Agent는 자신의 worktree 밖 파일을 수정하지 않는다.
- worktree 삭제는 PR 병합과 미추적 파일 확인 후 Coordinator만 수행한다.

## 14. Agent 작업 지시 템플릿

각 Agent에게 다음 양식으로 작업을 전달한다.

```text
프로젝트: SePark
역할: <Agent 역할>
브랜치: <branch>
worktree: <absolute path>
기준 SHA: <base sha>

목표:
- <사용자 가치와 구현 목표>

독점 소유 파일:
- <paths>

수정 금지 파일:
- README.md
- pyproject.toml / requirements*
- .env.example / .gitignore
- lean_canvas/factory.py
- <브랜치별 추가 금지>

공용 계약:
- separk/application/models.py
- separk/application/ports.py
- LeanCanvas/CanvasEvaluation/LLMClient 공개 시그니처 변경 금지

완료 기준:
- <acceptance criteria>

필수 검증:
- python -m pytest <owned tests> -q
- python -m pytest -q
- git diff --check

규칙:
- 실제 외부 API를 호출하지 않는다.
- secret, 캐시, 생성 결과 원문을 커밋하지 않는다.
- 의존성이나 공용 계약 변경이 필요하면 직접 수정하지 말고 RFC를 보낸다.
- 작업 완료 후 커밋 SHA, 변경 파일, 테스트 결과, 남은 위험을 보고한다.
- 통합 브랜치에 직접 merge하거나 push하지 않는다.
```

## 15. 파일 소유권 규칙

| 파일/영역 | 단독 소유자 | 다른 Agent의 행동 |
|---|---|---|
| `lean_canvas/factory.py` | F1, 이후 E2 | 변경 요청만 전달 |
| `pyproject.toml`, `requirements*` | F2, 이후 통합 Agent | 필요한 의존성 목록 전달 |
| `.env.example`, `.gitignore` | F2, 이후 통합 Agent | 필요한 env/ignore 목록 전달 |
| `README.md` | F3/R2 | 문서 변경 요약 전달 |
| `separk/application/models.py`, `ports.py` | C1 | RFC 제출 |
| `separk/intake/**` | P1 | 수정 금지 |
| `separk/refinement/**` | P2 | 수정 금지 |
| `separk/runtime/**`, `presentation/**` | P3 | 수정 금지 |
| `streamlit_app.py`, `separk/ui/**` | P4 | 수정 금지 |
| `evals/data/annotations/**` | E1 | 사람 라벨 원본 보존 |
| `evals/experiments/**`, `evals/reporting.py` | E2 | 동시 수정 금지 |
| `evals/results/<run-id>/**` | R1 | 결과 수정 금지 |
| `docs/assets/**`, case study | R2 | 변경 요청 전달 |

공통 fixture가 필요해도 `tests/conftest.py`를 여러 Agent가 수정하지 않는다. 각 브랜치의 테스트 폴더에 지역 helper를 둔 뒤 통합 Agent가 중복을 정리한다.

## 16. PR과 병합 규칙

### 16.1 모든 PR이 포함할 내용

- 목표와 사용자 가치
- 변경 파일 목록
- 명시적으로 하지 않은 일
- 테스트 명령과 결과
- UI 변경이면 스크린샷
- 새 환경변수·의존성·마이그레이션 요구
- 알려진 위험과 후속 작업

### 16.2 Coordinator 검토 순서

1. 파일 소유권 위반 확인
2. `git diff --check`
3. 브랜치 전용 테스트
4. 전체 오프라인 테스트
5. 패키지 build/CLI smoke test
6. secret·캐시·생성 결과 추적 여부 확인
7. 계약 변경 여부 확인
8. squash merge 또는 명시한 프로젝트 병합 정책 적용

### 16.3 금지 사항

- Agent가 통합 브랜치에 직접 merge
- 다른 Agent 브랜치의 commit을 임의 cherry-pick
- 사용자 승인 없는 실제 API 비용 발생
- 실패한 평가 결과 숨기기
- 자동 생성한 값을 사람 라벨로 기록
- Streamlit secret 파일 또는 `.env` 커밋

## 17. 테스트 전략

### 17.1 항상 실행하는 오프라인 테스트

```bash
python -m pytest -q
python -m build
separk --help
separk-evals --help
python -m evals list-results
git diff --check
```

### 17.2 계층별 테스트

- core: generator, parsing, aggregation, judge, pairwise
- product contract: DTO 불변성, validation, serialization
- intake: prompt, strict parsing, 후보 중복 방지
- refinement: 취약 블록 우선순위, 질문, 불변 v1, diff
- runtime: 입력 제한, timeout, budget, cache privacy
- UI: session state와 view model, fake service 사용자 여정
- eval: 데이터셋, annotation, telemetry, report 재현성
- integration: 두 진입 경로의 fake LLM E2E

### 17.3 실제 API smoke test

- 기본 CI에는 포함하지 않는다.
- 별도 marker와 수동 workflow로만 실행한다.
- 호출 전 모델, 최대 호출 수, 예상 비용을 표시한다.
- 결과에는 git SHA와 모델명을 기록한다.
- API 키와 전체 사용자 원문은 저장하지 않는다.

## 18. 릴리스 Definition of Done

### 코드

- 전체 오프라인 테스트 green
- 패키지 build와 CLI smoke test green
- CI green
- 공용 계약과 실제 구현 일치
- API key 없이 샘플 모드 E2E 성공
- 실제 key 사용 시 제한·timeout·오류 처리 검증

### 제품

- 두 진입 모드 사용 가능
- 후보 3개 → v1 → 질문 → v2 → 비교 → 다운로드 가능
- 점수의 한계와 검증 필요성 표시
- 모바일에서 핵심 흐름 사용 가능
- 공유 가능한 공개 URL 존재

### 평가

- 두 명의 독립 인간 평가 완료
- 24개 합의 라벨과 입력 hash 존재
- 신뢰도·인간 일치도·편향·비용·지연 결과 공개
- PASS와 FAIL 모두 공개

### 공개 저장소

- SePark README, 스크린샷/GIF, Live Demo 링크
- LICENSE, SECURITY, CONTRIBUTING
- secret scan 통과
- `.env`, cache, raw API 결과가 Git 이력에 없음
- 설치법과 배포법을 새 환경에서 재현 가능

## 19. 주요 위험과 대응

| 위험 | 대응 |
|---|---|
| 공용 모델을 Agent마다 다르게 정의 | 계약 브랜치를 먼저 병합하고 변경을 RFC로 제한 |
| `factory.py`, README, 의존성 충돌 | 단계별 단독 소유자 지정 |
| UI가 코어 구현을 기다려 병렬성 상실 | `SeParkUseCases` Protocol과 fake service 사용 |
| Streamlit rerun으로 중복 과금 | request id, session state, cache wrapper |
| LLM 출력이 시장 사실처럼 보임 | 사용자 제공/AI 추론/외부 검증 필요 상태 구분 |
| Judge 점수가 객관적 품질처럼 보임 | 인간 일치도와 편향 결과, 한계 문구 공개 |
| 인간 라벨이 기대 verdict에 오염 | category/verdict를 숨긴 블라인드 라벨링 |
| 생성기 변경으로 인간 라벨 무효화 | prompt/model/canvas hash 동결 |
| 공개 API 악용 | 샘플 모드, 세션 제한, timeout, 예산 상한, 필요 시 외부 rate-limit 저장소 |
| API·모델 변경으로 재현성 상실 | 모델·SDK·prompt·rubric·git SHA 기록 |

## 20. 첫 실행 권장 순서

1. 이 계획 문서를 리뷰하고 MIT 등 라이선스 정책을 결정한다.
2. 계획 문서를 커밋하고 `integration/separk-v1`을 만든다.
3. F1, F2, F3 Agent를 동시에 시작한다.
4. Foundation Gate를 통과하고 기준 SHA를 기록한다.
5. C1 계약 브랜치를 작게 구현·병합한다.
6. P1, P2, P3를 동시에 시작하고 첫 빈 슬롯에 P4를 시작한다.
7. I1 통합 Agent가 E2E를 완성한다.
8. E1, E2, D1을 병렬 실행한다.
9. 사용자가 인간 라벨링과 실제 API 평가 비용을 승인한다.
10. R1이 실제 baseline을 생성한다.
11. R2가 README와 case study를 실제 수치·URL로 최종화한다.
12. `release/separk-v1.0.0`에서 최종 검증 후 태그한다.

이 순서를 따르면 가장 먼저 저장소의 신뢰성을 회복하고, 이후 제품 기능과 평가 증거를 독립적으로 개발하면서도 README·factory·의존성 파일에서 발생하는 병합 충돌을 최소화할 수 있다.
