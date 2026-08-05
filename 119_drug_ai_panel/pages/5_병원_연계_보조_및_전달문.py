from __future__ import annotations

import math
import sys
from datetime import datetime, timedelta
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import theme
from case_data import PATIENT_LOCATION
from models import ConfirmedCase
from templates import make_hospital_message

st.set_page_config(
    page_title="119 약물안전 코파일럿 | 병원 연계 보조 및 전달문",
    page_icon="🚑",
    layout="wide",
    initial_sidebar_state="expanded",
)
theme.inject_css()
theme.render_sidebar("병원연계")

# 샘플 응급의료기관 후보 — 실서비스에서는 국립중앙의료원 응급의료기관 정보 API로 대체됩니다.
# 화면3(AI 보조패널)의 기본 사건 위치(case_data.PATIENT_LOCATION, 관악구 신림동)와
# 가까운 서울 시내 병원으로 좌표를 맞췄다.
HOSPITALS = [
    {
        "code": "A", "name": "A 지역응급의료센터", "tier": "지역응급의료센터", "lat": 37.5013, "lon": 126.9433,
        "er_beds": 12, "icu_beds": 2, "ventilator": True, "drug_icu": True, "updated_min": 6,
    },
    {
        "code": "B", "name": "B 권역응급의료센터", "tier": "권역응급의료센터", "lat": 37.4563, "lon": 126.8952,
        "er_beds": 6, "icu_beds": 1, "ventilator": True, "drug_icu": True, "updated_min": 3,
    },
    {
        "code": "C", "name": "C 응급의료기관", "tier": "지역응급의료기관", "lat": 37.4785, "lon": 126.9612,
        "er_beds": 4, "icu_beds": 0, "ventilator": False, "drug_icu": False, "updated_min": 7,
    },
]

STAGES = ["API상 후보", "전화 확인 중", "수용 확인", "최종 이송 결정"]


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _eta_minutes(distance_km: float) -> int:
    # 도심 구급차 평균 이동속도를 시속 25km로 가정한 근사치 — 직선거리 기준이라
    # 실제 도로 이동시간보다 짧게 나올 수 있음(샘플 데이터 한계).
    return max(3, round(distance_km / 25 * 60))


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
    if not hard_pass:
        verdict = "부적합"
    elif total >= 0.75:
        verdict = "적합"
    else:
        verdict = "조건부 적합"
    return {"total": total, "parts": weighted, "hard_pass": hard_pass, "verdict": verdict}


def render_header() -> None:
    st.markdown(
        f"""
        <div class="topbar">
          <div>
            <span class="brand"><span class="em">119</span>약물안전 코파일럿</span>
            <span class="title">화면 5. 병원 연계 보조 및 전달문</span>
          </div>
          <div class="pill">● 병원 추천이 아닌 적합성 설명과 전달문 보조</div>
          <div class="small-muted">{datetime.now().strftime('%Y.%m.%d %H:%M')}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


render_header()

confirmed: ConfirmedCase | None = st.session_state.get("confirmed_case")
if confirmed is None:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.info("먼저 화면 3. 약물 AI 보조패널에서 사건을 분석하고 '확인 후 저장'까지 진행하세요.")
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

age_group, sex = st.session_state.get("patient_age_sex", ("50대", "여성"))
age_group = age_group or "50대"
sex = sex or "여성"

# AVPU/숫자 활력징후 기준으로 중환자실·인공호흡기 필요 여부를 판단한다.
require_icu = confirmed.consciousness in {"V", "P", "U"}
require_vent = (
    (confirmed.respiratory_rate is not None and (confirmed.respiratory_rate < 10 or confirmed.respiratory_rate > 30))
    or (confirmed.spo2 is not None and confirmed.spo2 < 90)
)

hospitals_with_eta = []
for h in HOSPITALS:
    distance_km = _haversine_km(PATIENT_LOCATION["lat"], PATIENT_LOCATION["lon"], h["lat"], h["lon"])
    hospitals_with_eta.append({**h, "distance_km": round(distance_km, 1), "eta_min": _eta_minutes(distance_km)})

scored = [{**h, **score_hospital(h, require_icu, require_vent)} for h in hospitals_with_eta]
passed = sorted([h for h in scored if h["hard_pass"]], key=lambda x: -x["total"])
top = passed[0] if passed else None

st.session_state.setdefault("transport_stage", 0)
stage = st.session_state["transport_stage"]
hospital = st.session_state.get("selected_hospital", top["name"] if top else None)
eta = st.session_state.get("selected_eta", top["eta_min"] if top else 0)

st.markdown('<div class="panel">', unsafe_allow_html=True)
p1, p2, p3, p4 = st.columns([1, 1.4, 0.8, 0.8])
p1.markdown(f'<div class="card-label">환자 정보</div><div class="card-value">{age_group} {sex}</div>', unsafe_allow_html=True)
p2.markdown(
    f'<div class="card-label">의심 상황</div><div class="card-value">'
    f'{confirmed.drug_group or confirmed.suspected_drug or "확인 중"} 관련 응급</div>',
    unsafe_allow_html=True,
)
p3.markdown(f'<div class="card-label">의식(AVPU)</div><div class="card-value">{confirmed.consciousness}</div>', unsafe_allow_html=True)
rr_spo2 = f"{confirmed.respiratory_rate or '?'}/분 · {confirmed.spo2 or '?'}%"
p4.markdown(f'<div class="card-label">RR·SpO₂</div><div class="card-value">{rr_spo2}</div>', unsafe_allow_html=True)
st.caption(f"현재 위치: {PATIENT_LOCATION['onset_place']} · {PATIENT_LOCATION['address']} ({PATIENT_LOCATION['lat']:.4f}, {PATIENT_LOCATION['lon']:.4f})")
st.markdown("</div>", unsafe_allow_html=True)

st.markdown('<div class="panel" style="margin-top:.6rem;">', unsafe_allow_html=True)
cols = st.columns(len(STAGES))
for i, (col, label) in enumerate(zip(cols, STAGES)):
    color = theme.BLUE if i <= stage else theme.MUTED
    col.markdown(
        f'<div style="text-align:center;"><div style="color:{color};font-weight:800;">{i + 1}. {label}</div>'
        f'<div style="height:4px;background:{color};border-radius:2px;margin-top:.4rem;"></div></div>',
        unsafe_allow_html=True,
    )
st.caption("API상 가용병상이 있어도 실제 수용이 확정된 것은 아닙니다. 각 단계는 전화 확인 결과로만 넘어갑니다.")
st.markdown("</div>", unsafe_allow_html=True)

col_l, col_m, col_r = st.columns([1.1, 1.3, 1], gap="small")

with col_l:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<div class="section-title" style="font-size:1.05rem;">① 후보 의료기관</div>', unsafe_allow_html=True)
    fig = go.Figure()
    fig.add_trace(go.Scattermapbox(
        lat=[PATIENT_LOCATION["lat"]], lon=[PATIENT_LOCATION["lon"]], mode="markers+text",
        marker=dict(size=15, color=theme.RED),
        text=["★"], textposition="middle center", name="환자 위치",
    ))
    verdict_color = {"적합": theme.STATUS["good"], "조건부 적합": theme.STATUS["warning"], "부적합": theme.STATUS["critical"]}
    for h in scored:
        fig.add_trace(go.Scattermapbox(
            lat=[h["lat"]], lon=[h["lon"]], mode="markers+text",
            marker=dict(size=15, color=verdict_color[h["verdict"]]),
            text=[f"{h['code']} {h['eta_min']}분"], textposition="top center", name=h["name"],
        ))
    fig.update_layout(
        mapbox=dict(
            style="https://basemaps.cartocdn.com/gl/positron-nolabels-gl-style/style.json",
            center=dict(lat=PATIENT_LOCATION["lat"], lon=PATIENT_LOCATION["lon"]), zoom=12.5,
        ),
        paper_bgcolor="white", margin=dict(l=0, r=0, t=0, b=0), height=260, showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    for h in scored:
        badge_kind = {"적합": "good", "조건부 적합": "warning", "부적합": "critical"}[h["verdict"]]
        st.markdown(
            f'<div style="display:flex;justify-content:space-between;align-items:center;margin:.4rem 0 .15rem;">'
            f'<span><b>{h["name"]}</b> <span class="small-muted">{h["eta_min"]}분 · {h["distance_km"]}km</span></span>'
            f'{theme.status_badge(badge_kind, h["verdict"])}</div>',
            unsafe_allow_html=True,
        )

        def _tag(ok: bool, label: str) -> str:
            color = theme.STATUS["good"] if ok else theme.MUTED
            return f'<span style="color:{color};font-size:.74rem;margin-right:.6rem;">{"●" if ok else "○"} {label}</span>'

        icu_tag = _tag(h["icu_beds"] > 0, f"중환자실 {h['icu_beds']}병상")
        vent_tag = _tag(h["ventilator"], "인공호흡기")
        drug_icu_tag = _tag(h["drug_icu"], "약물중환자 대응")
        st.markdown(f'<div style="margin-bottom:.5rem;">{icu_tag}{vent_tag}{drug_icu_tag}</div>', unsafe_allow_html=True)
    st.caption("이동 시간은 실시간 교통 상황에 따라 변동될 수 있습니다(샘플 데이터).")
    st.markdown("</div>", unsafe_allow_html=True)

with col_m:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<div class="section-title" style="font-size:1.05rem;">② 적합성 판단 근거</div>', unsafe_allow_html=True)
    rows = ["임상적합성", "자원가용성", "이동접근성", "정보최신성", "기관수준"]
    header = "".join(f"<th style='padding:.3rem .5rem;text-align:center;'>{h['code']}</th>" for h in scored)
    html = [f"<table style='width:100%;border-collapse:collapse;font-size:.82rem;'>",
            f"<tr><th style='text-align:left;padding:.3rem .5rem;'>평가 항목</th>{header}</tr>"]
    for label in rows:
        cells = "".join(
            f"<td style='padding:.3rem .5rem;text-align:center;'>{h['parts'][label][1]:.2f}</td>" for h in scored
        )
        html.append(f"<tr style='border-top:1px solid {theme.BORDER};'><td style='padding:.3rem .5rem;color:{theme.MUTED};'>{label}</td>{cells}</tr>")
    drug_icu_cells = "".join(
        f"<td style='padding:.3rem .5rem;text-align:center;'>{'✓' if h['drug_icu'] else '—'}</td>" for h in scored
    )
    html.append(
        f"<tr style='border-top:1px solid {theme.BORDER};'>"
        f"<td style='padding:.3rem .5rem;color:{theme.MUTED};'>약물중환자 대응<span style='font-size:.7rem;'>(참고)</span></td>"
        f"{drug_icu_cells}</tr>"
    )
    verdict_cells = "".join(
        f"<td style='padding:.3rem .5rem;text-align:center;'>{theme.status_badge({'적합': 'good', '조건부 적합': 'warning', '부적합': 'critical'}[h['verdict']], h['verdict'])}</td>"
        for h in scored
    )
    html.append(f"<tr style='border-top:2px solid {theme.BORDER};'><td style='padding:.3rem .5rem;font-weight:700;'>종합 판정</td>{verdict_cells}</tr>")
    html.append("</table>")
    st.markdown("".join(html), unsafe_allow_html=True)
    st.caption("※ 본 판단은 현재 확보된 정보 기반 보조 판단이며, 실제 수용 가능 여부는 전화 확인을 통해 최종 결정됩니다.")
    st.markdown("</div>", unsafe_allow_html=True)

with col_r:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<div class="section-title" style="font-size:1.05rem;">③ 병원 전달문 자동생성</div>', unsafe_allow_html=True)
    if hospital:
        handoff = make_hospital_message(confirmed, age_group, sex)
        st.text_area("자동 생성 (수정 가능)", value=handoff, height=200, key="handoff_text")
        st.caption(f"수신 병원: {hospital} · 생성 시각 {datetime.now().strftime('%H:%M')}")
    else:
        st.caption("적합 후보가 없어 전달문을 생성할 수 없습니다.")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="panel" style="margin-top:.6rem;">', unsafe_allow_html=True)
    st.markdown('<div class="section-title" style="font-size:1.05rem;">연락 기록</div>', unsafe_allow_html=True)
    called_at = st.session_state.get("call_started_at")
    st.markdown(f"**{hospital or '-'}** — 연결시각 {called_at.strftime('%H:%M') if called_at else '-'} · 결과 {STAGES[stage]}")
    st.markdown("</div>", unsafe_allow_html=True)

    b1, b2, b3 = st.columns(3)
    if b1.button("수용 요청", type="primary", use_container_width=True, disabled=not top or stage != 0):
        st.session_state.update(transport_stage=1, selected_hospital=top["name"], selected_eta=top["eta_min"], call_started_at=datetime.now())
        st.rerun()
    if b2.button("수용 확인됨", use_container_width=True, disabled=stage != 1):
        st.session_state["transport_stage"] = 2
        st.rerun()
    if b3.button("최종 병원 선택", use_container_width=True, disabled=stage != 2):
        st.session_state.update(transport_stage=3, departed_at=datetime.now())
        st.rerun()

    if stage == 3:
        departed = st.session_state.get("departed_at", datetime.now())
        arrival = departed + timedelta(minutes=eta)
        st.markdown('<div class="panel" style="margin-top:.6rem;">', unsafe_allow_html=True)
        st.success(f"이송 결정 확정 — 출발 {departed.strftime('%H:%M')} · 예상 도착 {arrival.strftime('%H:%M')}")
        st.caption("구급활동 기록 초안이 자동 저장됩니다.")
        st.markdown("</div>", unsafe_allow_html=True)

st.caption(
    "본 코드는 공모전 MVP 시연용입니다. 병원 후보·병상정보는 샘플이며, 실제 배포 시 "
    "국립중앙의료원 응급의료기관 정보 API로 대체해야 합니다."
)
