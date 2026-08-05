from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import theme
from models import ConfirmedCase

st.set_page_config(
    page_title="119 약물안전 코파일럿 | 대응카드",
    page_icon="🚑",
    layout="wide",
    initial_sidebar_state="expanded",
)
theme.inject_css()
theme.render_sidebar("대응카드")

# 근거: 119구급대원 현장응급처치 표준지침(2023) 기반 상담 프로토콜 초안.
# 카드 문장은 사전 검토된 지침 문장이며, 생성형 AI는 순서 정리·요약에만 사용됩니다.
TOXIDROME_CARDS = {
    "진정수면성": {
        "title": "진정제·수면제 과량복용 의심",
        "severity": "심각",
        "immediate": [
            "환자가 자극에 반응하는가", "정상적으로 호흡하는가", "호흡수와 산소포화도는 얼마인가",
            "술이나 다른 약물을 함께 복용했는가", "복용한 제품과 남은 수량을 확인할 수 있는가",
            "자살시도 가능성이 있는가",
        ],
        "scene": ["약통·약 봉지·처방전 확보", "복용시각 및 최대 추정량 확인", "다른 노출자 존재 여부 확인", "의복이나 주변의 독성물질 오염 확인"],
        "tier": "지역응급의료센터 이상", "icu": "일반 또는 내과 ICU", "vent": "필요",
    },
    "오피오이드성": {
        "title": "오피오이드 과량복용 의심",
        "severity": "심각",
        "immediate": [
            "환자가 자극에 반응하는가", "호흡수가 느리거나 무호흡인가", "코고는·가글거리는 소리가 있는가",
            "청색증·축동이 있는가", "날록손 보유 여부(기관 승인 절차 있을 때만 안내)",
        ],
        "scene": ["약통·처방전·주사기 확보", "복용/노출 시각 확인", "다른 약물 동시 사용 여부 확인"],
        "tier": "지역응급의료센터 이상", "icu": "일반 ICU", "vent": "필요",
    },
    "부식성/화학물질": {
        "title": "농약·화학물질 노출 의심",
        "severity": "경계",
        "immediate": [
            "환자가 자극에 반응하는가", "정상적으로 호흡하는가", "침·눈물·땀·구토·배뇨 등 콜린성 증상이 있는가", "근육연축이 있는가",
        ],
        "scene": ["오염 의복·주변 위험물 확인", "맨손 접촉 금지 여부 확인", "2차 오염 방지 장비 필요 여부"],
        "tier": "권역응급의료센터(해독제 보유기관) 우선", "icu": "필요시 검토", "vent": "필요시 검토",
    },
}
DEFAULT_CARD = {
    "title": "약물 관련 응급 — 유형 확인 필요",
    "severity": "주의",
    "immediate": ["환자가 자극에 반응하는가", "정상적으로 호흡하는가", "복용/노출 물질을 확인할 수 있는가"],
    "scene": ["약통·처방전·용기 확보", "복용시각 확인"],
    "tier": "지역응급의료센터 이상", "icu": "확인 필요", "vent": "확인 필요",
}

GUIDELINE_SOURCES = [
    "대한응급의학회 · 독성물질 노출 환자 초기평가 및 처치 지침",
    "보건복지부 · 약물중독 응급처치 및 병원전 단계 지침",
    "소방청 · 119 구급대원 현장응급처치 표준지침",
]


def _pick_card(confirmed: ConfirmedCase) -> dict:
    text = f"{confirmed.drug_group or ''} {confirmed.suspected_drug or ''}"
    if any(k in text for k in ["수면제", "진정제", "벤조디아제핀"]):
        return TOXIDROME_CARDS["진정수면성"]
    if any(k in text for k in ["오피오이드", "펜타닐", "모르핀", "헤로인", "옥시코돈"]):
        return TOXIDROME_CARDS["오피오이드성"]
    if any(k in text for k in ["농약", "제초제", "살충제", "화학물질", "부식제"]):
        return TOXIDROME_CARDS["부식성/화학물질"]
    return DEFAULT_CARD


render_header = f"""
<div class="topbar"><div>
<span class="brand"><span class="em">119</span>약물안전 코파일럿</span>
<span class="title">화면 4. 약물 대응카드 및 의료지도</span>
</div>
<div class="pill">● Pre-KTAS 결과는 기존 시스템 값 사용</div>
<div class="small-muted">{datetime.now().strftime('%Y.%m.%d %H:%M')}</div>
</div>
"""
st.markdown(render_header, unsafe_allow_html=True)

confirmed: ConfirmedCase | None = st.session_state.get("confirmed_case")
if confirmed is None:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.info("먼저 화면 3. 약물 AI 보조패널에서 사건을 분석하고 '확인 후 저장'까지 진행하세요.")
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

age_group, sex = st.session_state.get("patient_age_sex", ("50대", "여성"))
age_group, sex = age_group or "50대", sex or "여성"
card = _pick_card(confirmed)

st.markdown('<div class="panel">', unsafe_allow_html=True)
s1, s2, s3, s4, s5 = st.columns([1.1, 1.6, 0.9, 0.9, 1.1])
s1.markdown(f'<div class="card-label">환자 정보</div><div class="card-value">{age_group} {sex}</div>', unsafe_allow_html=True)
s2.markdown(f'<div class="card-label">의심 상황</div><div class="card-value">{card["title"]}</div>', unsafe_allow_html=True)
conscious_txt = {"A": "정상", "V": "음성 반응", "P": "통증 반응", "U": "반응 없음", "미상": "확인 필요"}[confirmed.consciousness]
s3.markdown(f'<div class="card-label">의식(AVPU)</div><div class="card-value">{confirmed.consciousness} · {conscious_txt}</div>', unsafe_allow_html=True)
breathing_abn = (confirmed.respiratory_rate is not None and (confirmed.respiratory_rate < 10 or confirmed.respiratory_rate > 30)) or \
                (confirmed.spo2 is not None and confirmed.spo2 < 94)
breathing_txt = "이상 의심" if breathing_abn else ("정상" if confirmed.respiratory_rate is not None else "확인 필요")
s4.markdown(f'<div class="card-label">호흡</div><div class="card-value">{breathing_txt}</div>', unsafe_allow_html=True)
s5.markdown(theme.status_badge(card["severity"], f"위험도 {card['severity']}"), unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

left, right = st.columns([1.3, 1], gap="large")

with left:
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.markdown("**① 즉시 확인**")
        for item in card["immediate"]:
            st.checkbox(item, key=f"imm_{hash(item)}")
        st.markdown("</div>", unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.markdown("**② 현장안전 및 추가확인**")
        for item in card["scene"]:
            st.checkbox(item, key=f"scene_{hash(item)}")
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown(
        f"""
        <div class="panel">
        <b style="color:{theme.STATUS['critical']};">주의 및 금지사항</b>
        <div style="margin-top:.4rem;">
        ✕ 억지로 토하게 하지 않는다<br>
        ✕ 약물 확인 때문에 이송을 지연하지 않는다<br>
        ✕ 의식·호흡·순환 평가보다 약물 확인을 우선하지 않는다
        </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown("**지침 근거**")
    for src in GUIDELINE_SOURCES:
        st.markdown(f"· {src}")
    st.caption(
        "카드 문장은 사전 검토·승인된 지침 문장이며, 생성형 AI는 순서 정리와 요약에만 사용됩니다. "
        "이 MVP는 지침 원문 페이지 인용 기능은 포함하지 않습니다."
    )
    st.markdown("</div>", unsafe_allow_html=True)

with right:
    conditions = {
        "의식 저하(AVPU V/P/U)": confirmed.consciousness in {"V", "P", "U"},
        "호흡 이상 또는 저산소증": breathing_abn,
        "혈압·맥박 이상": False,
        "자살시도 가능성": confirmed.suicide_risk == "예",
        "이송기관 선정이 어려움": False,
    }
    met = sum(conditions.values())
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown(f"**의료지도 검토 조건** · {met}개 충족")
    g1, g2 = st.columns(2)
    for i, (label, ok) in enumerate(conditions.items()):
        dot = theme.STATUS["critical"] if ok else theme.TEXT_MUTED
        (g1 if i % 2 == 0 else g2).markdown(
            f'<div style="margin:.25rem 0;"><span style="color:{dot};">●</span> {label}</div>',
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown("**영상의료지도 연계**")
    st.markdown(
        f'<span class="badge" style="background:{theme.CATEGORICAL["aqua"]};">● 연결 가능</span> '
        '<span class="muted">(MVP 시연 — 실제 화상연결 아님)</span>',
        unsafe_allow_html=True,
    )
    st.caption("영상의료지도를 통해 약물 확인 및 처치 지도를 받을 수 있습니다.")
    st.button("의료지도 요청", type="primary", use_container_width=True, disabled=met < 2,
               help=None if met >= 2 else "검토 조건이 2개 이상 충족되면 활성화됩니다.")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown("**이송기관 요구조건**")
    st.markdown(f'<div class="muted">기관 수준</div><div style="font-weight:700;">{card["tier"]}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="muted">중환자실</div><div style="font-weight:700;">{card["icu"]}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="muted">인공호흡기</div><div style="font-weight:700;">{card["vent"]}</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    if st.button("확인 완료", use_container_width=True):
        st.toast("확인 항목이 구급활동기록에 반영됩니다.")

    st.caption(
        "최종 판단: 이 카드는 확인 순서를 제시할 뿐이며, 임상 판단과 처치 결정은 "
        "구급대원과 의료지도의사가 수행합니다."
    )
