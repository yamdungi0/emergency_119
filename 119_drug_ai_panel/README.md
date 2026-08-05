# 119 약물안전 코파일럿 — 화면 3 약물 AI 보조패널

공모전 MVP용 Streamlit 구현입니다.

## 구현 기능

- 119 통화 STT 또는 텍스트 입력
- 약물명·약물군·복용시각·최대 추정량·노출경로 자동추출
- 의식·호흡수·산소포화도 구조화
- 음주·복합복용·자살시도 가능성·약통 확보 여부 추출
- 미확인 필수항목 경고
- 기존 구급활동일지 필드 자동 매핑 및 사용자 수정
- 규칙 기반 약물 대응카드
- 입력된 구조화 값만 사용한 병원 전달문
- AI 원본과 사용자 확인값의 SQLite 감사로그 저장
- OpenAI API 키가 없을 때 규칙 기반 데모로 자동 대체

## 폴더 구조

```text
119_drug_ai_panel/
├─ app.py                 # Streamlit 화면
├─ extractor.py           # 하이브리드 분석 파이프라인
├─ openai_service.py      # OpenAI 구조화 추출·음성인식
├─ rules.py               # 약물사전/정규식/누락·위험 검증
├─ models.py              # Pydantic 고정 스키마
├─ templates.py           # 대응카드·병원 전달문
├─ storage.py             # 감사로그 SQLite
├─ drug_dictionary.py     # MVP용 약물사전
├─ sample_data.py         # 시연 사례
├─ test_rules.py          # 규칙 기반 스모크 테스트
├─ requirements.txt
└─ .env.example
```

## 설치

Python 3.11 환경을 권장합니다.

```bash
cd 119_drug_ai_panel
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

`.env`:

```dotenv
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-5-mini
OPENAI_TRANSCRIBE_MODEL=gpt-4o-mini-transcribe
USE_OPENAI=true
AUDIT_DB_PATH=./data/audit.db
```

API 키는 서버 환경변수 또는 비밀관리 도구에 저장하고 Git에 커밋하지 않습니다.

## 실행

```bash
streamlit run app.py
```

브라우저에서 표시된 예시 문장을 그대로 사용해 `AI 분석 실행`을 누르면 됩니다.

## API 키 없이 실행

`.env`에서 다음과 같이 설정합니다.

```dotenv
USE_OPENAI=false
```

약물사전·정규표현식·규칙 엔진만 사용해 동일한 화면 흐름을 시연합니다.

## 음성입력

OpenAI 연동 상태에서 `wav`, `mp3`, `m4a`, `mp4`, `webm`, `ogg` 파일을 올린 후
`음성 → 통화 STT 변환`을 누릅니다. 변환된 텍스트를 사용자가 검토한 뒤 분석합니다.

## 검증

```bash
python test_rules.py
```

## 구현 원칙

1. AI 결과는 초안이며 사용자가 확인하기 전 기존 기록을 덮어쓰지 않습니다.
2. 입력에 없는 제품명·복용량·활력징후를 생성하지 않습니다.
3. 현장 측정 숫자와 정규식 추출값은 LLM 결과보다 우선합니다.
4. 처치방법·해독제·약물 용량을 생성하지 않습니다.
5. 최종 판단은 구급대원과 의료지도 담당자가 수행합니다.
6. 시연용 경보 임계치는 실제 배포 전 승인된 119 지침으로 교체해야 합니다.

## 실서비스 전 추가 작업

- 식약처 의약품·마약류 전체 사전 구축
- 실제 e-Triage 필드 및 연계 API 규격 반영
- 통화·현장 데이터 비식별화 및 접근통제
- 승인된 119 현장응급처치 표준지침 기반 규칙 검증
- 필드별 정답셋을 이용한 Precision/Recall/F1 평가
- 약물명, 복용시각, 최대 추정량, 자살시도 가능성의 사용자 수정률 분석
