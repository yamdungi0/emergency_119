from __future__ import annotations

import re

import streamlit as st

import theme
from core.drug_db import DrugDatabase
from core.protocol_rules import build_protocol
from data_loader import DATA_DIR

PRESETS = {
    "진정제·수면제 과량복용 (의식저하 의심)": (
        "50대 여성이 수면제를 한 통 정도 먹은 것 같아요. 40분 전부터 불러도 반응이 없고, "
        "숨소리가 이상해요. 옆에 빈 약통이 있어요."
    ),
    "오피오이드 과량복용 (호흡저하 의심)": (
        "30대 남자가 약을 먹고 쓰러졌어요. 불러도 반응이 없고 숨이 아주 느리면서 "
        "코고는 소리가 납니다. 약봉지에는 펜타닐이라고 적혀 있습니다."
    ),
    "농약·화학물질 노출 (2차오염 위험)": (
        "밭에서 농약을 마신 것 같다고 합니다. 의식은 있는데 침을 계속 흘리고 구토를 했어요. "
        "옷에 농약이 묻어 있는 것 같습니다."
    ),
}

# 기존 구급활동일지(e-Triage 연계)를 흉내낸 데모용 레코드 — 실제 병원/개인정보가 아닌
# PRESETS 시나리오에 맞춘 가상의 값입니다. 통화 원문에서 뽑을 수 없는 항목(연락처·주소·
# 과거병력 등)까지 포함하므로, 좌측 패널은 "AI 보조"가 아니라 이미 채워진 일지로 둡니다.
# lat/lon: 실제 구급대는 병원 연계 API를 주소가 아니라 위경도 기준으로 조회하므로,
# 04 병원연계 화면이 이 좌표를 그대로 이어받아 후보 병원 거리를 계산한다(번지수까지
# 정확한 좌표는 아니지만, 실제로 존재하는 서울 시내 장소를 기준으로 한 근사치).
EMS_LOG_DEMO = {
    "진정제·수면제 과량복용 (의식저하 의심)": dict(
        case_no="20260804-1456", name="김ㅇ순", sex_age="여 / 54세", phone="010-1234-5678",
        address="서울특별시 관악구 신림동 (신림역 인근 PC방)", onset_place="PC방", onset_time="2026-08-04 14:10",
        lat=37.4844, lon=126.9296,
        chief_complaint="의식저하", symptom_onset="13:30경 (약 40분 전)", etc_note="현장에 수면제 약통 1개 발견",
        past_hx="우울증", drug_hx="수면제 복용 중 (종류·용량 미상)", allergy="없음", etc_hx="특이사항 없음",
        vitals=dict(consciousness="혼돈 (GCS E3M5)", bp="96/60 mmHg", hr="58 회/분", rr="9 회/분",
                    spo2="90 %", bt="36.2 ℃", glucose="112 mg/dL"),
        pre_ktas="2단계 (긴급)", pre_ktas_reason="의식저하, 호흡저하, 저혈압",
        planned_hospital="확인 중", transport_mode="구급차",
        crew_note="50대 여성, 수면제 과량 복용 의심. 의식 저하 및 호흡수 감소, 저혈압 관찰. 기도 유지 중이며 산소 투여 중.",
    ),
    "오피오이드 과량복용 (호흡저하 의심)": dict(
        case_no="20260804-1512", name="박ㅇ현", sex_age="남 / 33세", phone="010-9876-5432",
        address="서울특별시 동작구 신대방동 (보라매공원)", onset_place="보라매공원", onset_time="2026-08-04 15:05",
        lat=37.4952, lon=126.9223,
        chief_complaint="무반응·호흡저하", symptom_onset="15:00경 (약 10분 전)", etc_note="약봉지에 '펜타닐' 표기 확인",
        past_hx="확인 필요", drug_hx="확인 필요", allergy="확인 필요", etc_hx="목격자 진술 확보",
        vitals=dict(consciousness="무반응 (GCS E1M1)", bp="확인 중", hr="확인 중", rr="4 회/분",
                    spo2="82 %", bt="확인 중", glucose="확인 중"),
        pre_ktas="1단계 (소생)", pre_ktas_reason="무호흡 위험, 의식 무반응",
        planned_hospital="확인 중", transport_mode="구급차",
        crew_note="30대 남성, 오피오이드 계열 과량복용 의심. 호흡수 현저히 저하, 산소포화도 낮음. 기도 확보 및 보조환기 중.",
    ),
    "농약·화학물질 노출 (2차오염 위험)": dict(
        case_no="20260804-1608", name="이ㅇ자", sex_age="여 / 61세", phone="010-2468-1357",
        address="서울특별시 구로구 항동 (도시텃밭)", onset_place="도시텃밭", onset_time="2026-08-04 16:00",
        lat=37.4835, lon=126.8319,
        chief_complaint="구토·침흘림", symptom_onset="15:50경 (약 10분 전)", etc_note="의복에 농약 오염 의심, 2차 오염 주의",
        past_hx="고혈압", drug_hx="혈압약 복용 중", allergy="없음", etc_hx="현장 접근 시 보호구 필요",
        vitals=dict(consciousness="명료 (GCS E4M6)", bp="132/84 mmHg", hr="102 회/분", rr="22 회/분",
                    spo2="95 %", bt="36.8 ℃", glucose="확인 중"),
        pre_ktas="2단계 (긴급)", pre_ktas_reason="콜린성 증상, 화학물질 노출",
        planned_hospital="확인 중", transport_mode="구급차",
        crew_note="60대 여성, 농약 음독 의심. 침흘림·구토 등 콜린성 증상 관찰. 오염 의복 제거 및 제염 시행 중.",
    ),
}

_AMOUNT_WORDS = {"한": 1, "두": 2, "세": 3, "네": 4}


def _supplement_facts(transcript: str, facts, matches: list[dict]) -> None:
    """정규식 기반 보조 추출 — LLM 없이도 명시적으로 문장에 있는 값만 채움."""
    age_sex = re.search(r"(\d{1,2})0대\s*(남성|여성|남자|여자|남|여)", transcript)
    if age_sex and facts.age is None:
        facts.age = f"{age_sex.group(1)}0대"
        facts.sex = "여성" if "여" in age_sex.group(2) else "남성"

    if facts.exposure_time is None:
        m = re.search(r"(\d+)\s*분\s*전", transcript) or re.search(r"(\d+)\s*시간\s*전", transcript)
        if m:
            unit = "분" if "분" in m.group(0) else "시간"
            facts.exposure_time = f"약 {m.group(1)}{unit} 전"

    if facts.amount is None:
        m = re.search(r"(\d+)\s*(정|알|mg|ml)", transcript)
        word_m = re.search(r"(한|두|세|네)\s*통", transcript)
        if m:
            facts.amount = f"{m.group(1)}{m.group(2)} (신고자 추정)"
        elif word_m:
            facts.amount = f"약 {_AMOUNT_WORDS[word_m.group(1)]}통 (정확한 수량 미상)"

    if facts.route is None:
        if re.search(r"먹|삼켰|복용|섭취", transcript):
            facts.route = "경구"
        elif re.search(r"주사|찔렀|바늘", transcript):
            facts.route = "주사"
        elif re.search(r"마셨|흡입|냄새|가스", transcript):
            facts.route = "흡입"
        elif re.search(r"피부|눈에|묻었", transcript):
            facts.route = "피부·눈"

    if facts.suspected_substance is None and matches:
        facts.suspected_substance = matches[0]["한글명"]

    if facts.package_available is None and re.search(r"약통|봉지|포장|처방전", transcript):
        facts.package_available = True


SEDATIVE_KEYWORDS = ["수면제", "졸피뎀", "진정제", "신경안정제", "벤조디아제핀", "안정제"]


def _supplement_toxidrome(transcript: str, result) -> None:
    """규칙엔진(core/protocol_rules.py)은 LLM 없이 진정수면성을 분류하지 않으므로,
    표준지침 PROTOCOL.md 단계4에 정의된 진정수면성 키워드만 보조로 매칭합니다."""
    if result.suspected_toxidrome == "혼합/미상" and any(k in transcript for k in SEDATIVE_KEYWORDS):
        result.suspected_toxidrome = "진정수면성"


def _required_missing(result) -> list[str]:
    missing = []
    if result.facts.normal_breathing is None:
        missing.append("호흡수/정상호흡 여부")
    if result.facts.exposure_time is None:
        missing.append("복용시각 정확도")
    if result.facts.intent == "미상":
        missing.append("자살시도 가능성")
    if result.facts.package_available is None:
        missing.append("약통 확보 여부")
    return missing


def _row(label: str, value: str) -> str:
    return f'<div class="muted" style="margin-top:.35rem;">{label}</div><div style="font-weight:600;">{value}</div>'


def _mapped_field(label: str, value) -> str:
    # space-between으로 라벨/배지를 컬럼 양 끝에 붙이면, 컬럼이 넓어질 때(와이드 화면)
    # 값이 짧은 행일수록 라벨과 배지 사이가 과도하게 벌어져 행마다 배지 위치가
    # 들쭉날쭉해 보였다 — 라벨 폭을 고정하고 값은 그 옆에 붙여서(gap) 항상 같은
    # 위치에서 시작하도록 정렬한다.
    if value is None or value == [] or value == "":
        return (
            f'<div style="display:flex;align-items:center;gap:.6rem;margin:.35rem 0;">'
            f'<span class="muted" style="width:8.5em;flex-shrink:0;">{label}</span>'
            f'<span class="badge badge-warning">미확인</span></div>'
        )
    if isinstance(value, list):
        value = ", ".join(str(v) for v in value)
    return (
        f'<div style="display:flex;align-items:center;gap:.6rem;margin:.35rem 0;">'
        f'<span class="muted" style="width:8.5em;flex-shrink:0;">{label}</span>'
        f'<b>{value}</b> <span class="badge badge-good">매핑됨</span></div>'
    )


def render() -> None:
    st.session_state.setdefault("intake_preset", "진정제·수면제 과량복용 (의식저하 의심)")
    preset = st.selectbox("사건 선택 (e-Triage 연동 시뮬레이션)", list(PRESETS), key="intake_preset")
    transcript = PRESETS[preset]
    log = EMS_LOG_DEMO[preset]
    # 04 병원연계가 사건과 무관하게 항상 같은 위치를 쓰던 문제를 고치기 위해, 선택된
    # 사건의 위경도를 세션에 넘긴다 — 실제 소방 구급대도 병원 API를 위경도로 조회한다.
    st.session_state["patient_location"] = {
        "label": log["onset_place"], "address": log["address"],
        "lat": log["lat"], "lon": log["lon"],
    }

    if st.session_state.get("intake_transcript_used") != transcript:
        result = build_protocol(transcript, None, [])
        db = DrugDatabase(DATA_DIR / "약물남용정보.csv")
        matches = db.search(transcript)
        _supplement_facts(transcript, result.facts, matches)
        _supplement_toxidrome(transcript, result)
        st.session_state["intake_result"] = result
        st.session_state["intake_matches"] = matches
        st.session_state["intake_transcript_used"] = transcript

    result = st.session_state["intake_result"]
    f = result.facts
    missing = _required_missing(result)

    left, right = st.columns([1.05, 1], gap="large")

    with left:
        with st.container(border=True):
            top1, top2 = st.columns([2, 1])
            top1.markdown("**기존 구급활동일지**")
            top2.markdown(
                '<div style="text-align:right;"><span class="badge" style="background:'
                f'{theme.CATEGORICAL["blue"]};">e-Triage 연계</span></div>',
                unsafe_allow_html=True,
            )
            st.caption(f"사건번호 {log['case_no']} · 초안 자동 반영")

            st.markdown("**환자정보**")
            c1, c2 = st.columns(2)
            c1.markdown(_row("성명", log["name"]), unsafe_allow_html=True)
            c1.markdown(_row("성별/나이", log["sex_age"]), unsafe_allow_html=True)
            c2.markdown(_row("연락처", log["phone"]), unsafe_allow_html=True)
            c2.markdown(_row("주소", log["address"]), unsafe_allow_html=True)
            c1.markdown(_row("발생장소", log["onset_place"]), unsafe_allow_html=True)
            c2.markdown(_row("발생일시", log["onset_time"]), unsafe_allow_html=True)
            # 병원연계 API는 주소가 아니라 위경도로 후보기관을 조회하므로, 구급활동일지에도
            # 위경도를 그대로 노출해 04 병원연계 화면과 동일한 좌표를 쓴다는 걸 보여준다.
            c1.markdown(_row("위경도", f"{log['lat']:.4f}, {log['lon']:.4f}"), unsafe_allow_html=True)

            st.markdown("**환자 증상**")
            c1, c2 = st.columns(2)
            c1.markdown(_row("주요증상", log["chief_complaint"]), unsafe_allow_html=True)
            c2.markdown(_row("발병시각", log["symptom_onset"]), unsafe_allow_html=True)
            st.markdown(_row("기타 특이사항", log["etc_note"]), unsafe_allow_html=True)

            st.markdown("**병력**")
            c1, c2 = st.columns(2)
            c1.markdown(_row("과거병력", log["past_hx"]), unsafe_allow_html=True)
            c1.markdown(_row("약물복용력", log["drug_hx"]), unsafe_allow_html=True)
            c2.markdown(_row("알레르기", log["allergy"]), unsafe_allow_html=True)
            c2.markdown(_row("기타", log["etc_hx"]), unsafe_allow_html=True)

            st.markdown("**활력징후 (현장 측정)**")
            v = log["vitals"]
            c1, c2, c3 = st.columns(3)
            c1.markdown(_row("의식상태", v["consciousness"]), unsafe_allow_html=True)
            c1.markdown(_row("BP", v["bp"]), unsafe_allow_html=True)
            c2.markdown(_row("HR", v["hr"]), unsafe_allow_html=True)
            c2.markdown(_row("RR", v["rr"]), unsafe_allow_html=True)
            c3.markdown(_row("SpO₂", v["spo2"]), unsafe_allow_html=True)
            c3.markdown(_row("BT", v["bt"]), unsafe_allow_html=True)

            st.markdown("**Pre-KTAS**")
            c1, c2 = st.columns(2)
            c1.markdown(_row("분류단계", log["pre_ktas"]), unsafe_allow_html=True)
            c2.markdown(_row("분류사유", log["pre_ktas_reason"]), unsafe_allow_html=True)

            st.markdown("**구급대원 평가소견**")
            st.markdown(f'<div class="muted" style="margin-top:.2rem;">{log["crew_note"]}</div>', unsafe_allow_html=True)

    with right:
        with st.container(border=True):
            top1, top2 = st.columns([2, 1])
            top1.markdown("**약물 AI 보조**")
            top2.markdown(
                f'<div style="text-align:right;" class="muted">중복 입력 감소 · 누락 경고</div>',
                unsafe_allow_html=True,
            )

            st.markdown("**AI 추출 요약**")
            g1, g2 = st.columns(2)
            g1.markdown(_mapped_field("의심 약물", f.suspected_substance), unsafe_allow_html=True)
            g1.markdown(_mapped_field("복용 시각", f.exposure_time), unsafe_allow_html=True)
            g1.markdown(_mapped_field("복용량", f.amount), unsafe_allow_html=True)
            g2.markdown(_mapped_field("노출 경로", f.route), unsafe_allow_html=True)
            g2.markdown(_mapped_field("자살시도 가능성", None if f.intent == "미상" else f.intent), unsafe_allow_html=True)
            g2.markdown(_mapped_field("약통 확보", "예" if f.package_available else None), unsafe_allow_html=True)

            with st.expander("AI 추출 원문 보기"):
                st.markdown(f'"{transcript}"')

            if missing:
                st.markdown(
                    f'<div class="card" style="border-color:{theme.STATUS["warning"]}66;margin-top:.6rem;">'
                    f'{theme.status_badge("주의", f"미확인 필수항목 {len(missing)}개")} '
                    f'<span class="muted">{" · ".join(missing)}</span>'
                    f"<div class='muted' style='margin-top:.4rem;'>확인되지 않은 값은 자동으로 채우지 않습니다.</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

            urgency_badge = {"RED": "심각", "ORANGE": "경계", "YELLOW": "주의", "UNKNOWN": "관심"}[result.urgency]
            st.markdown(
                f'<div style="margin-top:.6rem;">{theme.status_badge(urgency_badge, f"{result.urgency} · {result.category}")}</div>',
                unsafe_allow_html=True,
            )
            st.caption(result.dispatch_recommendation)

        b1, b2, b3 = st.columns(3)
        if b1.button("확인 후 저장", type="primary", use_container_width=True):
            st.toast("구급활동일지에 반영되었습니다.")
        if b2.button("대응카드 보기", use_container_width=True):
            st.session_state.update(page="card")
            st.rerun()
        if b3.button("병원 전달문 생성 →", use_container_width=True):
            st.session_state.update(page="hospital")
            st.rerun()
