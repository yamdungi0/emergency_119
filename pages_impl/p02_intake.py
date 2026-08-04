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
    return missing


def render() -> None:
    st.session_state.setdefault("intake_transcript", PRESETS["진정제·수면제 과량복용 (의식저하 의심)"])

    preset = st.selectbox("예시 신고 시나리오", list(PRESETS), key="intake_preset")
    if st.button("예시 불러오기"):
        st.session_state["intake_transcript"] = PRESETS[preset]
        st.rerun()

    left, right = st.columns([1, 1.1], gap="large")

    with left:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("**신고 통화 · 텍스트 입력**")
        transcript = st.text_area(
            "통화 내용 (실제 서비스에서는 실시간 음성전사 결과가 들어옵니다)",
            key="intake_transcript",
            height=140,
        )
        run = st.button("구조화 분석 실행", type="primary", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

        if run or "intake_result" in st.session_state:
            if run:
                result = build_protocol(transcript, None, [])
                db = DrugDatabase(DATA_DIR / "약물남용정보.csv")
                matches = db.search(transcript)
                _supplement_facts(transcript, result.facts, matches)
                _supplement_toxidrome(transcript, result)
                st.session_state["intake_result"] = result
                st.session_state["intake_matches"] = matches
                st.session_state["intake_transcript_used"] = transcript

            result = st.session_state["intake_result"]
            matches = st.session_state.get("intake_matches", [])

            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown("**다음에 물어볼 질문 · 표준지침 기준**")
            for q in result.next_questions[:6]:
                st.checkbox(q, key=f"q_{hash(q)}", value=False)
            if matches:
                st.markdown("**약물명 사전 매칭**")
                for m in matches[:3]:
                    st.caption(f"{m['한글명']} ({m['영문명']}) · {m['분류/구분']}")
            st.markdown("</div>", unsafe_allow_html=True)

    with right:
        if "intake_result" not in st.session_state:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.info("왼쪽에서 통화 내용을 입력하고 '구조화 분석 실행'을 누르세요.")
            st.markdown("</div>", unsafe_allow_html=True)
            return

        result = st.session_state["intake_result"]
        missing = _required_missing(result)

        if missing:
            st.markdown(
                f'<div class="card" style="border-color:{theme.STATUS["warning"]}66;">'
                f'{theme.status_badge("주의", f"미확인 필수항목 {len(missing)}개")} '
                f'<span class="muted">{" · ".join(missing)}</span>'
                f"<div class='muted' style='margin-top:.4rem;'>확인되지 않은 값은 자동으로 채우지 않습니다.</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

        urgency_badge = {"RED": "심각", "ORANGE": "경계", "YELLOW": "주의", "UNKNOWN": "관심"}[result.urgency]
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown(
            f'{theme.status_badge(urgency_badge, f"{result.urgency} · {result.category}")}',
            unsafe_allow_html=True,
        )
        st.markdown(f"**추정 독성증후군:** {result.suspected_toxidrome}")
        st.caption(result.dispatch_recommendation)
        st.markdown("</div>", unsafe_allow_html=True)

        def field(label: str, value) -> str:
            if value is None or value == [] or value == "":
                return f'<div class="muted">{label}</div><div><span class="badge badge-warning">미상 · 확인 필요</span></div>'
            if isinstance(value, list):
                value = ", ".join(str(v) for v in value)
            return f'<div class="muted">{label}</div><div style="font-weight:700;">{value}</div>'

        f = result.facts
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("**AI 구조화 결과**")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(field("약물/물질", f.suspected_substance), unsafe_allow_html=True)
            st.markdown(field("경로", f.route), unsafe_allow_html=True)
            st.markdown(field("복용량", f.amount), unsafe_allow_html=True)
            st.markdown(field("노출 시각", f.exposure_time), unsafe_allow_html=True)
        with c2:
            st.markdown(field("의식", "저하 의심" if f.conscious is False else ("정상" if f.conscious else None)), unsafe_allow_html=True)
            st.markdown(field("정상호흡", "없음/저하 의심" if f.normal_breathing is False else ("정상" if f.normal_breathing else None)), unsafe_allow_html=True)
            st.markdown(field("증상", f.symptoms), unsafe_allow_html=True)
            st.markdown(field("현장 위험", f.scene_hazards), unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("**지금 신고자에게 안내**")
        for i, instr in enumerate(result.caller_instructions[:5], 1):
            st.write(f"{i}. {instr}")
        st.markdown("**금지·주의**")
        for d in result.do_not:
            st.write("• ", d)
        st.markdown("</div>", unsafe_allow_html=True)

        st.button(
            "상담카드 열기 →",
            type="primary",
            use_container_width=True,
            on_click=lambda: st.session_state.update(page="card"),
        )
