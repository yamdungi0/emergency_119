# 119 약물안전 상황판 (MVP 시연)

약물 관련 119 구급상황을 예측·접수·상담·이송까지 한 화면 흐름으로 보여주는 시연용 웹앱입니다.
소방청 구급상황관리 현황(2019-2023) 백테스트 예측모델, 119 표준지침 규칙엔진, 국립중앙의료원
응급의료기관 정보 API 연동 로직(현재는 샘플 데이터)을 하나의 Streamlit 앱으로 통합했습니다.

## 화면 구성

| # | 화면 | 설명 |
|---|------|------|
| 01 | 상황판 | 2023 백테스트 예측 vs 2024 합성 실시간 데이터로 시간대별/지역별 위험도 표시 |
| 02 | 접수·문진 | 통화 텍스트를 규칙엔진으로 구조화 (LLM 없이도 동작) |
| 03 | 상담카드 | 표준지침 기반 체크리스트, 의료지도 요청조건 |
| 04 | 기관연계 | 필수조건 필터 + 다기준 점수화로 병원 후보 랭킹, 지도 표시 |
| 05 | 이송결정 | 병원 전달문 자동생성, 연락 상태 기록 |
| 06 | 관리자 검증 | 모델 성능(MAE/WMAPE), 특성 중요도, 데이터 품질 |

## 로컬 실행

```bash
cd webapp
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## 데이터·로직 출처

- `data/test_predictions_2023.csv`, `metrics.csv`, `feature_importance.csv`, `run_metadata.json`:
  `소방청/발생 예측 모델/` 의 LightGBM Poisson 백테스트 산출물을 그대로 사용합니다.
- `data/realtime_sample_2024.csv`: 2024년 임의 합성 실시간 입력 샘플 — 실제 신고 데이터가
  누적되기 전까지 "실시간 갱신" 흐름을 시연하기 위한 자리표시자입니다.
- `core/protocol_rules.py`, `core/schemas.py`, `core/drug_db.py`: `소방청/응급전화대응프로토콜/`의
  규칙 기반 구조화 엔진을 그대로 재사용합니다 (OpenAI API 키 없이 규칙만으로 동작).
- 04/05 화면의 병원 후보는 현재 샘플 데이터입니다. 국립중앙의료원 응급의료기관 API를 연동하려면
  `소방청/응급실매칭/app.py`의 `call_api`/`enrich_candidates` 로직을 참고해 `pages_impl/p04_hospital.py`에
  연결하세요.

## 알려진 한계 (시연 MVP)

- 예측 모델은 지역·시간대별 신고 발생량만 다루며, 환자 중증도는 예측하지 않습니다
  (원본 데이터의 중증도 결측률 약 45.2%).
- 02 접수 화면은 정규식 기반 보조 추출을 포함하되 LLM을 사용하지 않으므로, 자유 서술형 문장에서
  약물명·경로 등을 못 찾으면 정직하게 "미상·확인 필요"로 표시합니다.
- 04/05는 실제 병원 수용 이력 데이터가 없어 학습 기반 랭킹 대신 PDF 제안 그대로
  `0.35*임상적합성 + 0.25*자원가용성 + 0.20*이동접근성 + 0.10*정보최신성 + 0.10*기관수준` 규칙식을 사용합니다.

## GitHub / Streamlit Community Cloud 배포

1. 이 `webapp/` 폴더를 GitHub 저장소로 push
2. https://share.streamlit.io 에서 저장소 연결, Main file path를 `app.py`로 지정
3. `requirements.txt`가 자동으로 설치됩니다 (Python 3.11+ 권장)
