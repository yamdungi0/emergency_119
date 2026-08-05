from __future__ import annotations

import os
from datetime import datetime

import streamlit as st
from dotenv import load_dotenv

import theme
from case_data import PATIENT_LOCATION
from extractor import analyze_case
from models import ConfirmedCase, DrugExtraction, ValidationResult
from openai_service import is_enabled, transcribe_audio
from sample_data import SAMPLE_FIELD_NOTE, SAMPLE_TRANSCRIPT, SAMPLE_VITALS
from storage import save_case
from templates import make_hospital_message, make_response_card

load_dotenv()

st.set_page_config(
    page_title="119 약물안전 코파일럿 | 약물 AI 보조패널",
    page_icon="🚑",
    layout="wide",
    initial_sidebar_state="expanded",
)
theme.inject_css()


def init_state() -> None:
    defaults = {
        "transcript": SAMPLE_TRANSCRIPT,
        "field_note": SAMPLE_FIELD_NOTE,
        "vital_text": SAMPLE_VITALS,
        "result": None,
        "validation": None,
        "analysis_mode": None,
        "show_response_card": False,
        "show_hospital_message": False,
        "last_saved_id": None,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def value_or_unknown(value, unknown="미상"):
    return unknown if value in (None, "", "미상") else value



def render_header() -> None:
    enabled_text = "OpenAI 연동" if is_enabled() else "규칙 기반 데모"
    st.markdown(
        f"""
        <div class="topbar">
          <div>
            <span class="brand"><span class="em">119</span>약물안전 코파일럿</span>
            <span class="title">화면 3. 약물 AI 보조패널</span>
          </div>
          <div class="pill">● 기존 e-Triage를 대체하지 않고 약물사고 특화 AI 보조기능을 추가</div>
          <div class="small-muted">{datetime.now().strftime('%Y.%m.%d %H:%M')} · {enabled_text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_existing_record() -> None:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">기존 구급활동일지</div>', unsafe_allow_html=True)

    st.markdown(
        f"""
        <div class="record-box">
          <div class="record-head">환자정보</div>
          <div class="metric-row">
            <div class="metric"><div class="metric-label">성명</div><div class="metric-value">{PATIENT_LOCATION['name']}</div></div>
            <div class="metric"><div class="metric-label">성별/나이</div><div class="metric-value">{PATIENT_LOCATION['sex_age']}</div></div>
            <div class="metric"><div class="metric-label">발생장소</div><div class="metric-value">{PATIENT_LOCATION['onset_place']}</div></div>
            <div class="metric"><div class="metric-label">발생일시</div><div class="metric-value">2026-08-04 21:10</div></div>
            <div class="metric"><div class="metric-label">사건번호</div><div class="metric-value">{PATIENT_LOCATION['case_no']}</div></div>
          </div>
        </div>
        <div class="record-box">
          <div class="record-head">환자 증상</div>
          <b>주요증상</b>&nbsp;&nbsp; 의식저하<br>
          <span class="small-muted">반응 저하 지속, 깨워도 반응 미약. 현장에 수면제 약통 1개 발견.</span>
        </div>
        <div class="record-box">
          <div class="record-head">활력징후(현장 측정)</div>
          <div class="metric-row">
            <div class="metric"><div class="metric-label">의식</div><div class="metric-value">V</div></div>
            <div class="metric"><div class="metric-label">BP</div><div class="metric-value">96/60</div></div>
            <div class="metric"><div class="metric-label">HR</div><div class="metric-value">58</div></div>
            <div class="metric"><div class="metric-label">RR</div><div class="metric-value risk">9</div></div>
            <div class="metric"><div class="metric-label">SpO₂</div><div class="metric-value risk">90%</div></div>
          </div>
        </div>
        <div class="record-box">
          <div class="record-head">Pre-KTAS</div>
          <div class="metric-row" style="grid-template-columns:1fr 1fr">
            <div class="metric"><div class="metric-label">분류단계</div><div class="metric-value risk">2단계(긴급)</div></div>
            <div class="metric"><div class="metric-label">위경도</div><div class="metric-value">{PATIENT_LOCATION['lat']:.4f}, {PATIENT_LOCATION['lon']:.4f}</div></div>
          </div>
          <div class="small-muted" style="margin-top:.4rem;">{PATIENT_LOCATION['address']} · 이송병원은 화면5 병원연계에서 위경도 기준으로 계산됩니다.</div>
        </div>
        <div class="record-box">
          <div class="record-head">구급대원 평가소견</div>
          50대 여성, 수면제 과량 복용 의심. 의식 저하 및 호흡수 감소.
          정확한 약물명과 최대 복용량 확인 필요.
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)


def result_cards(result: DrugExtraction) -> None:
    cards = [
        ("의심 약물", value_or_unknown(result.drug_group or result.suspected_drug), ""),
        ("복용 시각", value_or_unknown(result.exposure_time_text), "card-teal"),
        ("복용량", value_or_unknown(result.amount_text), "card-orange"),
        ("노출 경로", value_or_unknown(result.route), ""),
        ("음주 여부", value_or_unknown(result.alcohol_use), "card-teal"),
        ("자살시도", value_or_unknown(result.suicide_risk), "card-orange"),
    ]
    cols = st.columns(3)
    for idx, (label, value, css_class) in enumerate(cards):
        with cols[idx % 3]:
            st.markdown(
                f'<div class="card {css_class}"><div class="card-label">{label}</div>'
                f'<div class="card-value">{value}</div></div>',
                unsafe_allow_html=True,
            )
        if idx == 2:
            cols = st.columns(3)


def render_input_and_analysis() -> None:
    st.markdown('<div class="ai-panel">', unsafe_allow_html=True)
    st.markdown('<div class="ai-title">AI 약물정보 자동구조화</div>', unsafe_allow_html=True)

    with st.expander("① 통화 STT·현장소견 입력", expanded=st.session_state.result is None):
        audio = st.file_uploader(
            "통화 음성 업로드(선택)",
            type=["wav", "mp3", "m4a", "mp4", "webm", "ogg"],
            help="OpenAI API 키가 설정된 경우 음성인식을 사용할 수 있습니다.",
        )
        if audio is not None:
            st.audio(audio)
            if st.button("음성 → 통화 STT 변환", use_container_width=True):
                if not is_enabled():
                    st.error("OPENAI_API_KEY와 USE_OPENAI=true 설정이 필요합니다.")
                else:
                    try:
                        with st.spinner("음성을 변환하고 있습니다."):
                            st.session_state.transcript = transcribe_audio(audio)
                        st.success("음성인식이 완료되었습니다.")
                    except Exception as exc:
                        st.error(f"음성인식 실패: {exc}")

        st.session_state.transcript = st.text_area(
            "119 통화 STT",
            value=st.session_state.transcript,
            height=105,
        )
        st.session_state.field_note = st.text_area(
            "구급대원 현장 평가소견",
            value=st.session_state.field_note,
            height=90,
        )
        st.session_state.vital_text = st.text_input(
            "현장 측정 활력징후",
            value=st.session_state.vital_text,
        )

        if st.button("AI 분석 실행", type="primary", use_container_width=True):
            with st.spinner("약물정보를 구조화하고 누락항목을 검사하고 있습니다."):
                result, validation, mode = analyze_case(
                    st.session_state.transcript,
                    st.session_state.field_note,
                    st.session_state.vital_text,
                )
            st.session_state.result = result
            st.session_state.validation = validation
            st.session_state.analysis_mode = mode
            st.session_state.show_response_card = False
            st.session_state.show_hospital_message = False
            st.rerun()

    if st.session_state.result is None:
        st.info("예시 문장이 입력되어 있습니다. ‘AI 분석 실행’을 누르세요.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    result: DrugExtraction = st.session_state.result
    validation: ValidationResult = st.session_state.validation

    st.caption(f"분석 방식: {st.session_state.analysis_mode}")
    st.markdown("#### AI 추출 요약")
    result_cards(result)

    st.markdown("<br>", unsafe_allow_html=True)
    left, right = st.columns([1, 1.05])
    with left:
        missing = validation.missing_required or ["미확인 필수항목 없음"]
        items = "".join(f'<div class="warning-item">❗ {item}</div>' for item in missing)
        st.markdown(
            f'<div class="warning-box"><div class="warning-title">미확인 필수항목</div>{items}</div>',
            unsafe_allow_html=True,
        )
        if validation.risk_alerts:
            with st.expander("위험신호 및 재확인 조건", expanded=True):
                for alert in validation.risk_alerts:
                    st.warning(alert)

    with right:
        mapping = [
            ("의심 약물", value_or_unknown(result.drug_group or result.suspected_drug)),
            ("복용 시각", value_or_unknown(result.exposure_time_text)),
            ("복용량", value_or_unknown(result.amount_text)),
            ("의식상태", value_or_unknown(result.consciousness)),
            ("경로", value_or_unknown(result.route)),
            ("약통 확보", value_or_unknown(result.medicine_container_secured)),
        ]
        rows = "".join(
            f'<div class="map-row"><span class="map-name">{name}</span>'
            f'<span class="map-value">{value}</span></div>'
            for name, value in mapping
        )
        st.markdown(
            f'<div class="mapping-box"><div class="section-title" style="font-size:1.05rem">'
            f'자동 매핑 결과</div>{rows}</div>',
            unsafe_allow_html=True,
        )

    st.markdown("#### 기존 구급활동일지 매핑값 확인·수정")
    c1, c2, c3 = st.columns(3)
    suspected_drug = c1.text_input(
        "의심 약물",
        value=result.suspected_drug or "",
    )
    drug_group = c2.text_input(
        "약물군",
        value=result.drug_group or "",
    )
    exposure_time = c3.text_input(
        "복용·노출 시각",
        value=result.exposure_time_text or "",
    )

    c4, c5, c6 = st.columns(3)
    amount = c4.text_input("최대 추정량", value=result.amount_text or "")
    route_options = ["경구", "흡입", "피부", "주사", "안구", "기타", "미상"]
    route = c5.selectbox(
        "노출 경로",
        route_options,
        index=route_options.index(result.route),
    )
    consciousness_options = ["A", "V", "P", "U", "미상"]
    consciousness = c6.selectbox(
        "의식상태",
        consciousness_options,
        index=consciousness_options.index(result.consciousness),
    )

    c7, c8, c9 = st.columns(3)
    rr = c7.number_input(
        "호흡수",
        min_value=0,
        max_value=100,
        value=result.respiratory_rate or 0,
        help="0은 미확인값으로 저장됩니다.",
    )
    spo2 = c8.number_input(
        "산소포화도",
        min_value=0,
        max_value=100,
        value=result.spo2 or 0,
        help="0은 미확인값으로 저장됩니다.",
    )
    state_options = ["예", "아니오", "미상", "확인 필요"]
    alcohol = c9.selectbox(
        "음주 여부",
        state_options,
        index=state_options.index(result.alcohol_use),
    )

    c10, c11, c12 = st.columns(3)
    multiple = c10.selectbox(
        "복합복용 여부",
        state_options,
        index=state_options.index(result.multiple_drug_use),
    )
    suicide = c11.selectbox(
        "자살시도 가능성",
        state_options,
        index=state_options.index(result.suicide_risk),
    )
    container = c12.selectbox(
        "약통 확보 여부",
        state_options,
        index=state_options.index(result.medicine_container_secured),
    )

    confirmed = ConfirmedCase(
        suspected_drug=suspected_drug or None,
        drug_group=drug_group or None,
        exposure_time_text=exposure_time or None,
        amount_text=amount or None,
        route=route,
        consciousness=consciousness,
        respiratory_rate=None if rr == 0 else int(rr),
        spo2=None if spo2 == 0 else int(spo2),
        alcohol_use=alcohol,
        multiple_drug_use=multiple,
        suicide_risk=suicide,
        medicine_container_secured=container,
    )
    # 화면5(병원연계)가 같은 세션 안에서 이 확인값을 이어받아 쓴다 — Streamlit의
    # 멀티페이지 앱은 pages/ 아래 스크립트끼리 st.session_state를 공유한다.
    st.session_state["confirmed_case"] = confirmed
    st.session_state["patient_age_sex"] = (result.age_group, result.sex)

    b1, b2, b3 = st.columns(3)
    if b1.button("대응카드 보기", use_container_width=True):
        st.session_state.show_response_card = not st.session_state.show_response_card
    if b2.button("병원 전달문 생성", use_container_width=True):
        st.session_state.show_hospital_message = not st.session_state.show_hospital_message
    if b3.button("확인 후 저장", type="primary", use_container_width=True):
        case_id = save_case(
            st.session_state.transcript,
            st.session_state.field_note,
            result,
            validation,
            confirmed,
        )
        st.session_state.last_saved_id = case_id
        st.success(f"확인값과 AI 원본이 감사로그에 저장되었습니다. 사건 ID: {case_id}")

    if st.session_state.show_response_card:
        card = make_response_card(result, validation)
        st.markdown("### 약물 대응카드(시연)")
        card_cols = st.columns(3)
        for col, (section, items) in zip(card_cols, card.items()):
            with col:
                st.markdown(f"**{section}**")
                for item in items:
                    st.write(f"• {item}")
        st.caption(
            "시연용 카드입니다. 실제 배포 전 승인된 119 현장응급처치 표준지침과 "
            "의료지도 기준으로 문구와 조건을 검증해야 합니다."
        )

    if st.session_state.show_hospital_message:
        st.markdown("### 병원 전달문")
        st.text_area(
            "자동 생성 결과",
            value=make_hospital_message(confirmed),
            height=220,
        )

    with st.expander("추출 근거·처리 메모"):
        if result.evidence:
            for evidence in result.evidence:
                st.write(f"- **{evidence.field}** · {evidence.source}: “{evidence.quote}”")
        else:
            st.write("표시할 근거 문장이 없습니다.")
        for note in result.extraction_notes:
            st.caption(note)

    st.markdown("</div>", unsafe_allow_html=True)


init_state()
theme.render_sidebar("AI 보조")
render_header()

left_col, right_col = st.columns([0.9, 1.1], gap="medium")
with left_col:
    render_existing_record()
with right_col:
    render_input_and_analysis()

st.caption(
    "본 코드는 공모전 MVP 시연용입니다. 진단·처치 자동결정 기능이 아니며, "
    "실제 운영 시 개인정보보호, 보안, 승인 지침, e-Triage 연계 규격 및 의료지도 절차 검증이 필요합니다."
)
