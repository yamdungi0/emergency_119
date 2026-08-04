from __future__ import annotations

from datetime import datetime

import streamlit as st

import theme
from pages_impl import p01_dashboard, p02_intake, p03_card, p04_hospital, p06_admin

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
    "dashboard": (p01_dashboard, "전국 약물안전 상황판", "상황실 · 향후 3시간 수요예측 및 이상징후", None),
    "intake": (p02_intake, "약물 AI 보조패널", "기존 구급활동일지(e-Triage 연계) + 약물 정보 자동추출", "기존 e-Triage를 대체하지 않고 선제예측 기능을 추가"),
    "card": (p03_card, "약물 대응 카드 및 의료지도", "표준지침 기반 확인 순서 · 영상의료지도 연계", "Pre-KTAS 결과는 기존 시스템 값 사용"),
    "hospital": (p04_hospital, "병원 연계 보조 및 전달문", "적합성 판단 근거 비교 + 전달문 자동생성", "병원 추천이 아닌 적합성 설명과 전달문 보조"),
    "admin": (p06_admin, "관리자 · 모델 검증", "백테스트 성능과 데이터 품질", None),
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
        with st.container(key=f"navwrap_{key}"):
            if st.button(f"{num}　{label}", key=f"nav_{key}", use_container_width=True):
                st.session_state["page"] = key
                st.rerun()
        if active:
            st.markdown(
                f"<style>div[class*='st-key-navwrap_{key}'] button {{"
                "border-color:#ffffff !important;color:#ffffff !important;"
                "background:rgba(255,255,255,0.14) !important;font-weight:700;}}</style>",
                unsafe_allow_html=True,
            )

    st.divider()
    st.caption("데이터: 소방청 구급상황관리 현황(2019-2023) · 국립중앙의료원 응급의료기관 정보")
    st.caption("이 서비스는 의사결정 지원용 시연 MVP이며, 최종 임상 판단은 구급대원·의료지도의사가 수행합니다.")

module, title, subtitle, badge = PAGES[st.session_state["page"]]
badge_html = (
    f'<span class="badge" style="background:{theme.NAVY};margin-top:.3rem;display:inline-block;">ⓘ {badge}</span>'
    if badge else ""
)

# 한 줄 문자열로 조립 — 여러 줄 들여쓰기된 HTML을 st.markdown에 넘기면 빈 줄에서
# CommonMark가 HTML 블록을 끊고 이후 들여쓰기를 코드블록으로 처리해버린다
# (sidebar_logo_html과 동일한 이유로 같은 패턴을 씀).
topbar_html = (
    '<div class="topbar"><div>'
    f'<div class="topbar-title">{title}</div>'
    f'<div class="topbar-sub">{subtitle}</div>'
    f"{badge_html}"
    "</div>"
    f'<div class="topbar-time">{datetime.now().strftime("%Y-%m-%d %H:%M:%S")} KST</div>'
    "</div>"
)
st.markdown(topbar_html, unsafe_allow_html=True)

module.render()
