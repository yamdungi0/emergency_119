from __future__ import annotations

from datetime import datetime

import streamlit as st

import theme
from pages_impl import p01_dashboard, p02_intake, p03_card, p04_hospital, p05_transport, p06_admin

st.set_page_config(
    page_title="119 약물안전 상황판",
    page_icon="🚑",
    layout="wide",
    initial_sidebar_state="expanded",
)
theme.inject_css()

if "page" not in st.session_state:
    st.session_state["page"] = "dashboard"

PAGES = {
    "dashboard": (p01_dashboard, "전국 약물안전 상황판", "상황실 · 향후 4시간 수요예측 및 이상징후"),
    "intake": (p02_intake, "약물 신고 접수 및 구조화 문진", "통화 내용을 표준 필드로 자동 구조화"),
    "card": (p03_card, "표준지침 기반 상담지원 카드", "119 현장응급처치 표준지침 기준"),
    "hospital": (p04_hospital, "응급의료기관 연계 지도", "필수조건 필터 + 다기준 점수화"),
    "transport": (p05_transport, "병원 연락 및 이송 의사결정", "전달문 자동생성 · 연락 상태 기록"),
    "admin": (p06_admin, "관리자 · 모델 검증", "백테스트 성능과 데이터 품질"),
}

with st.sidebar:
    sidebar_logo_html = (
        '<div style="display:flex;align-items:center;gap:.6rem;margin-bottom:1.2rem;">'
        + theme.logo_svg(width=40, height=31, on_dark=True)
        + '<div style="line-height:1.2;">'
        + '<div style="font-weight:900;font-size:1rem;">119 약물안전</div>'
        + '<div style="font-weight:500;font-size:.72rem;color:rgba(255,255,255,.65);">상황판</div>'
        + "</div></div>"
    )
    st.markdown(sidebar_logo_html, unsafe_allow_html=True)
    for key, num, label in theme.NAV_ITEMS:
        active = st.session_state["page"] == key
        css_class = "nav-btn-active" if active else ""
        st.markdown(f'<div class="{css_class}">', unsafe_allow_html=True)
        if st.button(f"{num}　{label}", key=f"nav_{key}", use_container_width=True):
            st.session_state["page"] = key
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    st.divider()
    st.caption("데이터: 소방청 구급상황관리 현황(2019-2023) · 국립중앙의료원 응급의료기관 정보")
    st.caption("이 서비스는 의사결정 지원용 시연 MVP이며, 최종 임상 판단은 구급대원·의료지도의사가 수행합니다.")

module, title, subtitle = PAGES[st.session_state["page"]]

st.markdown(
    f"""
    <div class="topbar">
        <div>
            <div class="topbar-title">{title}</div>
            <div class="topbar-sub">{subtitle}</div>
        </div>
        <div class="topbar-time">{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} KST</div>
    </div>
    """,
    unsafe_allow_html=True,
)

module.render()
