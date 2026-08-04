from __future__ import annotations

import math

import plotly.graph_objects as go
import streamlit as st

import theme

PATIENT = {"name": "환자 현재 위치", "region": "서울 관악구 신림동", "lat": 37.4842, "lon": 126.9294}

# 샘플 응급의료기관 후보 — 실서비스에서는 국립중앙의료원 응급의료기관 정보 API로 대체됩니다.
HOSPITALS = [
    {
        "name": "A 지역응급의료센터", "tier": "지역응급의료센터", "lat": 37.5013, "lon": 126.9433,
        "eta_min": 14, "er_beds": 12, "icu_beds": 2, "ventilator": True, "drug_icu": True,
        "updated_min": 6,
    },
    {
        "name": "B 권역응급의료센터", "tier": "권역응급의료센터", "lat": 37.4563, "lon": 126.8952,
        "eta_min": 21, "er_beds": 6, "icu_beds": 1, "ventilator": True, "drug_icu": True,
        "updated_min": 3,
    },
    {
        "name": "C 병원", "tier": "지역응급의료기관", "lat": 37.4785, "lon": 126.9612,
        "eta_min": 9, "er_beds": 4, "icu_beds": 0, "ventilator": False, "drug_icu": False,
        "updated_min": 7,
    },
]

SEG_COLORS = [
    theme.CATEGORICAL["aqua"], theme.CATEGORICAL["blue"],
    theme.CATEGORICAL["violet"], theme.CATEGORICAL["yellow"], theme.TEXT_MUTED,
]


def score_hospital(h: dict, require_icu: bool, require_vent: bool) -> dict:
    clinical = 1.0
    if require_icu and h["icu_beds"] <= 0:
        clinical -= 0.6
    if require_vent and not h["ventilator"]:
        clinical -= 0.6
    clinical = max(0.0, clinical)

    resource = min(1.0, (h["er_beds"] + h["icu_beds"] * 2) / 16)
    access = max(0.0, 1 - h["eta_min"] / 30)
    freshness = max(0.0, 1 - h["updated_min"] / 60)
    tier_score = {"권역응급의료센터": 1.0, "지역응급의료센터": 0.85, "지역응급의료기관": 0.5}.get(h["tier"], 0.4)

    weighted = {
        "임상적합성": (0.35, clinical),
        "자원가용성": (0.25, resource),
        "이동접근성": (0.20, access),
        "정보최신성": (0.10, freshness),
        "기관수준": (0.10, tier_score),
    }
    total = sum(w * v for w, v in weighted.values())
    hard_pass = not ((require_icu and h["icu_beds"] <= 0) or (require_vent and not h["ventilator"]))
    return {"total": total, "parts": weighted, "hard_pass": hard_pass}


def render() -> None:
    facts = getattr(st.session_state.get("intake_result"), "facts", None)
    require_icu = bool(facts and facts.conscious is False)
    require_vent = bool(facts and facts.normal_breathing is False)

    c1, c2 = st.columns(2)
    require_icu = c1.checkbox("필수조건: 중환자실 필요 (의식저하)", value=require_icu)
    require_vent = c2.checkbox("필수조건: 인공호흡기 필요 (호흡이상)", value=require_vent)

    scored = []
    for h in HOSPITALS:
        s = score_hospital(h, require_icu, require_vent)
        scored.append({**h, **s})
    passed = sorted([h for h in scored if h["hard_pass"]], key=lambda x: -x["total"])
    failed = [h for h in scored if not h["hard_pass"]]

    st.caption(f"필수조건 필터 적용 · 후보 {len(passed)}곳 (부적합 {len(failed)}곳 제외)")

    map_col, info_col = st.columns([1.1, 1], gap="large")

    with map_col:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        fig = go.Figure()
        fig.add_trace(go.Scattermapbox(
            lat=[PATIENT["lat"]], lon=[PATIENT["lon"]], mode="markers+text",
            marker=dict(size=16, color=theme.STATUS["critical"]),
            text=["환자"], textposition="top center", name="환자 위치",
        ))
        for i, h in enumerate(passed, 1):
            fig.add_trace(go.Scattermapbox(
                lat=[h["lat"]], lon=[h["lon"]], mode="markers+text",
                marker=dict(size=14, color=theme.CATEGORICAL["blue"] if i == 1 else theme.CATEGORICAL["aqua"]),
                text=[f"{i}. {h['name']}"], textposition="top center", name=h["name"],
            ))
        for h in failed:
            fig.add_trace(go.Scattermapbox(
                lat=[h["lat"]], lon=[h["lon"]], mode="markers+text",
                marker=dict(size=12, color=theme.TEXT_MUTED),
                text=[f"{h['name']} (제외)"], textposition="top center", name=h["name"],
            ))
        fig.update_layout(
            mapbox=dict(style="carto-darkmatter", center=dict(lat=PATIENT["lat"], lon=PATIENT["lon"]), zoom=11.5),
            paper_bgcolor=theme.CARD_BG, margin=dict(l=0, r=0, t=0, b=0), height=420, showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        st.caption(f"환자 위치: {PATIENT['region']} · 예상 이동시간은 직선거리 기준 추정값(샘플 데이터)")
        st.markdown("</div>", unsafe_allow_html=True)

    with info_col:
        if not passed:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.error("필수조건을 충족하는 후보가 없습니다. 조건을 다시 확인하세요.")
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            top = passed[0]
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown(theme.status_badge("정상", "1순위"), unsafe_allow_html=True)
            st.markdown(f"### {top['name']}")
            st.caption(f"{top['tier']} · 예상 이동 {top['eta_min']}분")
            m1, m2 = st.columns(2)
            m1.metric("응급실 병상", f"{top['er_beds']}")
            m2.metric("중환자실", f"{top['icu_beds']}")
            m1.metric("인공호흡기", "가능" if top["ventilator"] else "불가")
            m2.metric("약물중환자(hv7)", "확인" if top["drug_icu"] else "미확인")

            st.markdown(f"**추천 점수 {top['total']:.2f}**")
            seg_html = "".join(
                f'<div style="flex:{w};background:{SEG_COLORS[i]};height:10px;"></div>'
                for i, (label, (w, v)) in enumerate(top["parts"].items())
            )
            st.markdown(f'<div style="display:flex;border-radius:6px;overflow:hidden;margin:.3rem 0;">{seg_html}</div>', unsafe_allow_html=True)
            legend = " · ".join(f"{label} {v:.2f}" for label, (w, v) in top["parts"].items())
            st.markdown(f'<div class="muted">{legend}</div>', unsafe_allow_html=True)

            st.button(
                "이 병원으로 이송 결정 진행 →",
                type="primary",
                use_container_width=True,
                on_click=lambda: st.session_state.update(page="transport", selected_hospital=top["name"], selected_eta=top["eta_min"]),
            )
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("**후보 비교**")
        for i, h in enumerate(scored, 1):
            status = "제외" if not h["hard_pass"] else ("1순위" if h is passed[0] else f"{passed.index(h)+1}순위")
            st.markdown(
                f"**{h['name']}** — {h['eta_min']}분 · 병상 {h['er_beds']} · "
                f"{'적합' if h['hard_pass'] else '부적합'} · {status} · 점수 {h['total']:.2f}"
            )
        st.caption("여기서 '순위'는 자동 이송 결정이 아니라 연락 우선순위입니다. 실제 수용 여부는 전화로 확인합니다.")
        st.markdown("</div>", unsafe_allow_html=True)
