# SePark

SePark는 막연한 창업 아이디어를 9개 블록의 린 캔버스로 정리하고, 그 결과를 LLM-as-a-Judge로 평가하기 위한 프로젝트입니다. 현재 저장소에는 **OpenAI API를 사용하는 CLI 생성기와 오프라인 평가 코드**가 구현되어 있습니다.

> 현재 상태: 개발 기준선입니다. 웹 앱과 공개 데모 URL은 아직 없으며, 아이디어 탐색·확인 질문·반복 개선 흐름도 구현 전입니다. 생성된 시장 정보와 수치는 외부 근거 검색으로 검증되지 않은 가설입니다.

## 현재 제공하는 기능

- 관심사와 추가 지침으로 9블록 `LeanCanvas` 생성
- 터미널 출력 및 Markdown 파일 저장
- 구체성·근거성·일관성·차별성의 4차원 평가 모델
- 가중 집계, 취약 블록 min-guard, verdict 매핑
- self-consistency, pairwise position swap, 인간 일치도 및 편향 측정 로직
- good/ambiguous/bad 각 8개로 구성된 24개 평가 데이터셋
- 외부 API를 호출하지 않는 단위 테스트

평가 실험의 설계와 현재 검증 상태는 [평가 가이드](docs/evaluation.md)에서 확인할 수 있습니다.

## 아직 제공하지 않는 기능

- Streamlit 웹 UI와 공개 데모
- 관심사·경험·자원을 바탕으로 한 아이디어 후보 제안
- 기존 기획의 누락 정보 추출
- 취약 블록 확인 질문과 답변 기반 v2 개선
- v1/v2 점수 및 변경 내용 비교
- JSON 내보내기와 API 키 없는 샘플 세션
- 검색 또는 인용 검증에 기반한 시장 근거 수집

위 항목은 SePark v1의 예정 범위이며, 현재 동작하는 기능처럼 간주하면 안 됩니다.

## 로컬 실행

Python 3.10 이상이 필요합니다. 현재 기준선의 의존성을 새 가상환경에 설치하려면 다음 명령을 실행합니다.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install "PyYAML>=6.0" "pytest>=8.0"
```

현재 `requirements.txt`에는 평가 데이터 로딩에 필요한 PyYAML과 테스트 도구가 포함되어 있지 않아 마지막 설치 명령이 필요합니다.

API 키는 파일에 커밋하지 말고 환경변수로 전달합니다.

```bash
export OPENAI_API_KEY="your-api-key"
export OPENAI_MODEL="gpt-4o-mini"  # 선택 사항
```

린 캔버스를 터미널에 출력하거나 Markdown으로 저장할 수 있습니다.

```bash
python main.py "반려동물 헬스케어"
python main.py "비건 베이커리" -i "국내 시장 한정" -o canvas.md
python main.py --help
```

이 명령은 실제 OpenAI API를 호출하므로 계정 요금과 모델 접근 권한을 확인해야 합니다. 출력 파일에는 민감한 아이디어나 개인정보가 포함될 수 있으므로 공개 저장소에 그대로 커밋하지 마세요.

## 테스트

```bash
python -m pytest -q
```

단위 테스트는 `ScriptedLLMClient`의 고정 응답을 사용하며 외부 API를 호출하지 않습니다. 다만 이 기준선에서는 평가 factory 연결이 아직 완료되지 않아 전체 테스트 수집이 실패합니다. 생성기 이외의 judge factory가 복구된 뒤 전체 테스트가 정상 실행되는 것이 목표입니다.

단위 테스트 통과는 실제 모델의 출력 품질을 증명하지 않습니다. API를 호출하는 평가 실험, 사람 라벨, 결과 해석은 [평가 가이드](docs/evaluation.md)에 별도로 설명합니다.

## 현재 구조

```text
main.py                         생성 CLI
lean_canvas/
├── models.py                  9블록 불변 도메인 모델
├── prompts.py                 생성 프롬프트
├── generator.py               생성 흐름
├── factory.py                 OpenAI 생성기 조립
├── llm/                       LLM 추상화와 OpenAI 구현
├── renderers.py               터미널·Markdown 출력
└── evaluation/                rubric, judge, 집계, pairwise
evals/
├── data/eval_dataset.yaml     24개 고정 평가 항목
├── experiments/               신뢰도·판정·편향·A/B 실험
├── metrics.py                 MAE, Cohen's kappa 등
└── reporting.py               JSON·Markdown 리포트
tests/                         API 없는 결정적 단위 테스트
```

제품명은 SePark이지만 기존 코어 Python 패키지 이름은 현재 `lean_canvas`로 유지합니다.

## 평가 결과의 현재 상태

- 데이터셋 24개의 `human_scores`는 모두 미입력 상태입니다.
- 저장소에 실제 OpenAI 평가 실행 결과나 검증된 baseline 리포트가 없습니다.
- judge의 점수는 제품 품질에 대한 확정적 증거가 아니라 검증해야 할 측정값입니다.
- 근거성 점수는 검색이나 출처 검증을 수행하지 않으므로 사실성을 보장하지 않습니다.

따라서 이 저장소의 임계값과 테스트만으로 모델 품질, 시장성 또는 사업 성공 가능성을 주장해서는 안 됩니다.

## 기여와 라이선스

개발 환경, 테스트 원칙, PR 체크리스트는 [CONTRIBUTING.md](CONTRIBUTING.md)를 참고하세요.

아직 오픈소스 라이선스가 선택되지 않았습니다. MIT가 기본 제안이지만, 라이선스 파일은 관리자가 명시적으로 결정한 뒤 추가합니다. 라이선스가 없다는 것은 코드의 복제·수정·배포 권한이 자동으로 부여된다는 뜻이 아닙니다.
