from __future__ import annotations

import streamlit as st

import theme

# 근거: 119구급대원 현장응급처치 표준지침(2023) 기반 상담 프로토콜 초안(PROTOCOL.md 단계4)
# 카드 문장은 사전 검토된 지침 문장이며, 생성형 AI는 순서 정리·요약에만 사용됩니다.
TOXIDROME_CARDS = {
    "진정수면성": {
        "title": "진정제·수면제 과량복용 의심",
        "severity": "심각",
        "immediate": [
            "환자가 자극에 반응하는가",
            "정상적으로 호흡하는가",
            "호흡수와 산소포화도는 얼마인가",
            "술이나 다른 약물을 함께 복용했는가",
            "복용한 제품과 남은 수량을 확인할 수 있는가",
            "자살시도 가능성이 있는가",
        ],
        "scene": ["약통·약 봉지·처방전 확보", "복용시각 및 최대 추정량 확인", "다른 노출자 존재 여부 확인", "의복이나 주변의 독성물질 오염 확인"],
        "tier": "지역응급의료센터 이상", "icu": "일반 또는 내과 ICU", "vent": "필요",
    },
    "오피오이드성": {
        "title": "오피오이드 과량복용 의심",
        "severity": "심각",
        "immediate": [
            "환자가 자극에 반응하는가",
            "호흡수가 느리거나 무호흡인가",
            "코고는·가글거리는 소리가 있는가",
            "청색증·축동이 있는가",
            "날록손 보유 여부(기관 승인 절차 있을 때만 안내)",
        ],
        "scene": ["약통·처방전·주사기 확보", "복용/노출 시각 확인", "다른 약물 동시 사용 여부 확인"],
        "tier": "지역응급의료센터 이상", "icu": "일반 ICU", "vent": "필요",
    },
    "부식성/화학물질": {
        "title": "농약·화학물질 노출 의심",
        "severity": "경계",
        "immediate": [
            "환자가 자극에 반응하는가",
            "정상적으로 호흡하는가",
            "침·눈물·땀·구토·배뇨 등 콜린성 증상이 있는가",
            "근육연축이 있는가",
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


def render() -> None:
    if "intake_result" not in st.session_state:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.info("먼저 02 접수 화면에서 신고 통화를 구조화하세요.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    result = st.session_state["intake_result"]
    card = TOXIDROME_CARDS.get(result.suspected_toxidrome, DEFAULT_CARD)
    f = result.facts

    left, right = st.columns([1.3, 1], gap="large")

    with left:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        badge_label = f"{card['severity']} 경로"
        st.markdown(theme.status_badge(card["severity"], badge_label), unsafe_allow_html=True)
        st.markdown(f"### {card['title']}")

        st.markdown("**즉시 확인**")
        for item in card["immediate"]:
            st.checkbox(item, key=f"imm_{hash(item)}")

        st.markdown("**현장 확인**")
        for item in card["scene"]:
            st.checkbox(item, key=f"scene_{hash(item)}")

        st.markdown(
            f"""
            <div class="card" style="background:rgba(208,59,59,0.08);border-color:{theme.STATUS['critical']}55;">
            <b>주의 · 금지</b><br>
            ✕ 억지로 토하게 하지 않는다<br>
            ✕ 약물 확인을 위해 이송을 지연하지 않는다<br>
            → 기도·호흡·순환 평가와 안정화를 우선한다
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.caption(
            "근거 · 119 구급대원 현장응급처치 표준지침 — 중독, 환자평가 필수항목 및 이송병원 선정지침. "
            "카드 문장은 사전 검토·승인된 지침 문장이며, 생성형 AI는 순서 정리와 요약에만 사용됩니다."
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        conditions = {
            "의식 저하": f.conscious is False,
            "호흡 이상 또는 저산소증": f.normal_breathing is False,
            "혈압·맥박 이상": False,
            "경련": "경련" in (f.symptoms or []),
            "이송기관 선정이 어려움": False,
        }
        met = sum(conditions.values())
        st.markdown('<div class="card" style="border-color:' + theme.STATUS["critical"] + '66;">', unsafe_allow_html=True)
        st.markdown(f"**의료지도 요청 조건** · {met}개 충족")
        for label, ok in conditions.items():
            dot = theme.STATUS["critical"] if ok else theme.TEXT_MUTED
            weight = "700" if ok else "400"
            st.markdown(
                f'<div style="margin:.25rem 0;"><span style="color:{dot};">●</span> '
                f'<span style="font-weight:{weight};">{label}</span> — {"충족" if ok else "미확인" if label not in ("혈압·맥박 이상","이송기관 선정이 어려움") else "없음/해당없음"}</div>',
                unsafe_allow_html=True,
            )
        if met >= 2:
            st.button("의료지도 요청 · 직통 연결", type="primary", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("**이송기관 요구조건**")
        st.markdown(f'<div class="muted">기관 수준</div><div style="font-weight:700;">{card["tier"]}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="muted">중환자실</div><div style="font-weight:700;">{card["icu"]}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="muted">인공호흡기</div><div style="font-weight:700;">{card["vent"]}</div>', unsafe_allow_html=True)
        psych = "자살시도 확인 후" if f.intent == "자살/자해" else "확인 필요"
        st.markdown(f'<div class="muted">정신건강의학과 연계</div><div style="font-weight:700;">{psych}</div>', unsafe_allow_html=True)
        st.button(
            "조건에 맞는 응급의료기관 찾기 →",
            type="primary",
            use_container_width=True,
            on_click=lambda: st.session_state.update(page="hospital"),
        )
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.caption(
            "최종 판단: 이 카드는 확인 순서를 제시할 뿐이며, 임상 판단과 처치 결정은 "
            "구급대원과 의료지도의사가 수행합니다."
        )
        st.markdown("</div>", unsafe_allow_html=True)
