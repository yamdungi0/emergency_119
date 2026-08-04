from __future__ import annotations

from datetime import datetime, timedelta

import streamlit as st

import theme

STAGES = ["API상 후보", "전화 확인 중", "수용 확인", "최종 이송 결정"]


def _value(x, fallback="확인 중") -> str:
    if x is None or x == [] or x == "":
        return fallback
    if isinstance(x, list):
        return ", ".join(str(v) for v in x) or fallback
    return str(x)


def build_handoff(facts, hospital: str, eta: int) -> str:
    age_sex = " ".join(v for v in [_value(facts.age, ""), _value(facts.sex, "")] if v) or "연령·성별 확인 중"
    conscious = "무반응(V/P/U 확인 필요)" if facts.conscious is False else ("정상" if facts.conscious else "확인 중")
    breathing = "이상 의심 — 호흡수 확인 중" if facts.normal_breathing is False else ("정상" if facts.normal_breathing else "확인 중")

    lines = [
        f"{age_sex}, {_value(facts.suspected_substance, '약물')} 관련 응급 의심입니다.",
        f"{_value(facts.exposure_time, '노출/복용 시각')} 노출된 것으로 추정되며 "
        f"복용량은 {_value(facts.amount)}입니다.",
        f"현재 의식 {conscious}, 호흡 {breathing}입니다.",
        f"동시복용·자살시도 가능성은 {_value(facts.intent, '확인 중')} 상태이며, "
        f"관련 증상: {_value(facts.symptoms, '보고된 추가 증상 없음')}.",
        f"예상 도착시간은 {eta}분입니다.",
        "중환자 대응 및 수용 가능 여부 확인 요청드립니다.",
    ]
    return " ".join(lines)


def render() -> None:
    hospital = st.session_state.get("selected_hospital")
    eta = st.session_state.get("selected_eta", 14)
    result = st.session_state.get("intake_result")

    if not hospital or not result:
        with st.container(border=True):
            st.info("먼저 02 접수 → 04 기관연계에서 이송 병원을 선택하세요.")
        return

    st.session_state.setdefault("transport_stage", 1)
    stage = st.session_state["transport_stage"]

    with st.container(border=True):
        cols = st.columns(len(STAGES))
        for i, (col, label) in enumerate(zip(cols, STAGES)):
            color = theme.CATEGORICAL["blue"] if i <= stage else theme.TEXT_MUTED
            col.markdown(
                f'<div style="text-align:center;"><div style="color:{color};font-weight:800;">{label}</div>'
                f'<div style="height:4px;background:{color};border-radius:2px;margin-top:.4rem;"></div></div>',
                unsafe_allow_html=True,
            )
        st.caption("API상 가용병상이 있어도 실제 수용이 확정된 것은 아닙니다. 각 단계는 전화 확인 결과로만 넘어갑니다.")

    left, right = st.columns([1.2, 1], gap="large")

    with left:
        with st.container(border=True):
            st.markdown(f"**병원 전달문 · {hospital}**")
            handoff = build_handoff(result.facts, hospital, eta)
            st.text_area("자동 생성 (수정 가능)", value=handoff, height=160, key="handoff_text")
            st.caption("템플릿 고정 · 구조화 문진에 입력된 값만 사용 · 추정 문장 생성 없음")

            b1, b2, b3 = st.columns(3)
            if b1.button("전화 연결 시작", use_container_width=True, disabled=stage != 0):
                st.session_state["transport_stage"] = 1
                st.session_state["call_started_at"] = datetime.now()
                st.rerun()
            if b2.button("수용 확인됨", type="primary", use_container_width=True, disabled=stage != 1):
                st.session_state["transport_stage"] = 2
                st.rerun()
            if b3.button("수용 불가 → 다른 병원", use_container_width=True, disabled=stage not in (1, 2)):
                st.session_state["page"] = "hospital"
                st.session_state["transport_stage"] = 0
                st.rerun()

        if stage >= 2:
            if st.button("최종 이송 결정 확정", type="primary", use_container_width=True, disabled=stage != 2):
                st.session_state["transport_stage"] = 3
                st.session_state["departed_at"] = datetime.now()
                st.rerun()

    with right:
        with st.container(border=True):
            st.markdown("**연락 기록**")
            called_at = st.session_state.get("call_started_at")
            st.markdown(
                f"**{hospital}** — 연결시각 {called_at.strftime('%H:%M') if called_at else '-'} · "
                f"결과 {STAGES[stage]}"
            )

        with st.container(border=True):
            st.markdown("**이송 결정**")
            if stage == 3:
                departed = st.session_state.get("departed_at", datetime.now())
                arrival = departed + timedelta(minutes=eta)
                m1, m2 = st.columns(2)
                m1.metric("최종 이송병원", hospital)
                m2.metric("출발시각", departed.strftime("%H:%M"))
                m1.metric("예상 도착", arrival.strftime("%H:%M"))
                m2.metric("의료지도", "완료")
                st.success("이송 결정이 확정되었습니다. 구급활동 기록 초안이 자동 저장됩니다.")
            else:
                st.caption(f"최종 이송병원: 미확정 · 현재 단계 — {STAGES[stage]}")

        with st.container(border=True):
            st.markdown("**구급활동 기록 초안**")
            st.caption("문진·상담카드 확인 항목·연락 기록·의료지도 내용이 하나의 초안으로 정리되며, "
                        "구급대원이 최종 확인 후 확정합니다.")
