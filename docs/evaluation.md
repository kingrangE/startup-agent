# SePark 평가 가이드

이 문서는 SePark의 평가 코드가 무엇을 측정하는지, 단위 테스트와 실제 모델 실험이 어떻게 다른지, 결과를 어떤 한계 안에서 해석해야 하는지를 설명합니다.

> 기준선 상태: 평가 로직과 24개 데이터셋은 구현되어 있지만, 사람 점수와 실제 OpenAI 실행 결과는 아직 없습니다. 유료 judge 실험은 Foundation의 judge factory 연결이 통합된 뒤 실행할 수 있습니다.

## 평가 대상

`CanvasJudge`는 린 캔버스의 각 블록을 다음 네 차원에서 1~5점으로 평가합니다.

| 차원 | 가중치 | 질문 |
| --- | ---: | --- |
| 근거성 (`evidence`) | 0.35 | 주장을 검증할 근거나 사례가 있는가? |
| 일관성 (`coherence`) | 0.25 | 문제·고객·솔루션·수익 가설이 서로 연결되는가? |
| 구체성 (`specificity`) | 0.20 | 대상과 결과가 검증 가능한 수준으로 구체적인가? |
| 차별성 (`differentiation`) | 0.20 | 대안과 구분되며 모방하기 어려운가? |

9개 블록의 가중 점수를 평균해 캔버스 총점을 만듭니다. 한 블록이라도 2.0 미만이면 치명적인 약점을 평균이 가리지 못하도록 총점을 최대 3.0으로 제한합니다.

| 총점 | verdict |
| ---: | --- |
| 4.0 이상 | `strong` |
| 2.8 이상 4.0 미만 | `acceptable` |
| 2.8 미만 | `needs_work` |

이 수치들은 현재 코드에 정의된 초기 기준입니다. 실제 모델과 사람 평가로 보정된 최종 기준이 아닙니다.

## 두 종류의 검증

### 1. 결정적 단위 테스트

```bash
python3 -m pytest -q
```

단위 테스트는 `ScriptedLLMClient`가 반환하는 고정 응답으로 다음 동작을 검증합니다.

- JSON 스키마 파싱과 오류 재시도
- 가중 집계, min-guard, verdict 경계값
- self-consistency 표준편차 계산
- pairwise 순서 교환과 위치 비일관 처리
- 인간 일치도와 Cohen's kappa 계산
- 평가 데이터셋 스키마와 범주 균형

이 테스트는 외부 API를 호출하지 않으며 비용이 발생하지 않습니다. 코드가 정해진 규칙대로 동작한다는 증거일 뿐, 실제 LLM이 좋은 캔버스를 생성하거나 공정하게 평가한다는 증거는 아닙니다.

전체 테스트가 `create_judge` 또는 `create_pairwise_judge` import 오류로 수집되지 않으면 Foundation의 factory 복구가 빠진 상태입니다. 복구를 통합한 뒤 전체 테스트 통과 여부를 확인해야 합니다.

### 2. 실제 모델 평가

`python3 -m evals`의 실험 명령은 OpenAI API를 호출합니다. 모델, 재시도, 캐시 적중 여부에 따라 비용과 시간이 달라지며 단위 테스트에 포함되지 않습니다.

실행 전에 다음을 확인합니다.

1. 외부 전송이 허용된 비민감 데이터만 사용합니다.
2. 예상 호출량과 계정 예산을 확인합니다.
3. `OPENAI_API_KEY`, `OPENAI_MODEL`, `JUDGE_MODEL`을 기록하되 키 자체는 기록하지 않습니다.
4. 먼저 `--limit 1`로 스모크 실행합니다.
5. 결과에 모델명, 설정, 코드 SHA를 함께 보존합니다.

```bash
export OPENAI_API_KEY="your-api-key"
export OPENAI_MODEL="gpt-4o-mini"
export JUDGE_MODEL="gpt-4o"

python3 -m evals --help
python3 -m evals generate-canvases --limit 1
python3 -m evals run-verdict-accuracy --limit 1
python3 -m evals run-judge-reliability --limit 1 --n 2
python3 -m evals run-bias --limit 1
python3 -m evals run-pairwise --limit 1 --model-a gpt-4o-mini --model-b gpt-4o
python3 -m evals list-results
```

`generate-canvases`는 생성기 factory만 사용합니다. 나머지 judge 실험에는 Foundation에서 제공하는 judge와 pairwise judge factory가 필요합니다.

## 실험별 의미와 최소 호출량

아래 호출량은 항목당 예상 최소치입니다. 캐시가 비어 있고 JSON 오류 재시도가 없다고 가정합니다.

| 명령 | 측정 내용 | 항목당 최소 API 호출 |
| --- | --- | ---: |
| `generate-canvases` | 사람 채점용 캔버스 생성 | 생성 1회 |
| `run-verdict-accuracy` | 기대 verdict와 1회 판정 비교 | 생성 1회 + judge 1회 |
| `run-judge-reliability --n N` | N회 채점의 흔들림과 다수결 판정 | 생성 1회 + judge N회 |
| `run-bias` | 허위 권위 단서와 동일 backbone 선호 | 생성 1회 + judge 3회 |
| `run-pairwise` | 두 생성 모델 A/B와 위치 일관성 | 생성 2회 + judge 2회 |

생성 캐시가 있으면 생성 호출은 생략될 수 있습니다. `--no-cache`는 캐시를 사용하지 않으므로 비교 재현성이 필요한 경우에만 신중히 사용합니다.

## 데이터셋과 사람 라벨

`evals/data/eval_dataset.yaml`에는 세 범주의 아이디어가 각각 8개씩, 총 24개 있습니다.

- `good`: 기대 verdict `strong`
- `ambiguous`: 기대 verdict `acceptable`
- `bad`: 기대 verdict `needs_work`

`expected_verdict`는 아이디어 범주에 대한 기대값입니다. 생성된 캔버스를 사람이 직접 채점한 값은 `human_scores`이며, 현재 24개 모두 `null`입니다.

사람 라벨을 만들 때는 다음 절차를 사용합니다.

1. 고정할 생성 모델과 코드 SHA를 기록합니다.
2. `generate-canvases`로 채점 대상을 생성합니다.
3. 평가자는 모델명과 기대 범주를 보지 않은 상태에서 각 캔버스를 네 차원 1~5점으로 채점합니다.
4. 각 점수의 근거와 애매한 사례를 함께 기록합니다.
5. 두 명 이상이 참여했다면 합의 전에 평가자 간 일치도를 별도로 계산합니다.
6. 원본 라벨과 수정 이력을 보존합니다.

현재 코드는 평가자 간 일치도와 라벨 변경 이력을 자동 관리하지 않습니다. 한 명의 라벨을 객관적 정답으로 간주하면 안 됩니다.

## 메트릭과 초기 목표

| 메트릭 | 초기 목표 | 해석 |
| --- | ---: | --- |
| self-consistency 총점 표준편차 | 0.3 이하 | 같은 입력의 반복 판정 안정성 |
| judge-human MAE | 0.5 이하 | 사람 점수와의 절대 오차 |
| 사람 점수 ±1 이내 비율 | 80% 이상 | 실용적 근접도 |
| signed bias | 절댓값 0.3 이하 | judge가 일관되게 후하거나 박한 정도 |
| verdict 정확도 | 85% 이상 | 기대 범주와 판정의 단순 일치율 |
| Cohen's kappa | 0.6 이상 | 우연 일치를 보정한 verdict 일치도 |
| bad → strong 오판 | 0건 | 명백히 약한 입력의 치명적 오판 |
| 허위 출처 주입 점수 상승 | 0.3 이하 | 권위 단서에 대한 민감도 |

목표 미달 결과를 숨기거나 임계값을 사후에 낮춰 통과시키지 않습니다. 임계값을 바꿀 때는 이유와 변경 전후 결과를 같이 남깁니다.

## 결과 파일

실험은 기본적으로 `evals/results/<timestamp>-<experiment>/` 아래에 다음 파일을 만듭니다.

- `config.json`: 모델과 실행 설정
- `metrics.json`: 기계가 읽을 수 있는 집계 결과
- `raw_scores.json`: 항목별 원점수
- `report.md`: 사람이 읽는 요약

캔버스 캐시는 `evals/results/_canvas_cache/`에 저장됩니다. 현재 저장소에는 검증된 결과 디렉터리가 없으며, 생성 결과와 캐시는 검토 없이 커밋하지 않습니다. 공개 baseline을 만들 때는 실행 SHA, 모델, SDK 버전, 프롬프트·rubric 버전, 실행 시각을 함께 남겨야 합니다.

## 해석상의 한계

- 근거성 평가는 검색이나 출처 확인을 하지 않습니다. 그럴듯한 허위 출처가 점수를 올릴 수 있습니다.
- judge와 생성기가 같은 모델 계열이면 자기 선호 편향이 생길 수 있습니다.
- 모델 제공자의 업데이트로 동일한 모델 이름에서도 결과가 달라질 수 있습니다.
- 24개 데이터셋은 회귀용 초기 표본이며 전체 창업 아이디어 분포를 대표하지 않습니다.
- 현재 비용, 토큰 사용량, 지연시간과 오류율은 자동 수집되지 않습니다.
- 실제 사용자 효용, 사업성, 법률·의료·재무적 타당성은 이 평가로 보장되지 않습니다.

평가 점수는 개선할 가설을 찾는 보조 신호로 사용하고, 전문가 검토와 실제 고객 검증을 대체하지 않습니다.
