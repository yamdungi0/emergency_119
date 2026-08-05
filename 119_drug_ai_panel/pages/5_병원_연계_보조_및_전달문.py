from __future__ import annotations

import math
import sys
from datetime import datetime, timedelta
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import nmc_api
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

# 샘플 응급의료기관 후보 — 국립중앙의료원 API 호출이 실패하면(키 없음, 네트워크 오류 등)
# 이 3곳으로 대체된다. 화면3(AI 보조패널)의 기본 사건 위치(case_data.PATIENT_LOCATION,
# 관악구 신림동)와 가까운 서울 시내 병원으로 좌표를 맞췄다.
SAMPLE_HOSPITALS = [
    {
        "code": "A", "name": "A 지역응급의료센터", "tier": "지역응급의료센터", "lat": 37.5013, "lon": 126.9433,
        "icu_beds": 2, "ventilator": True, "er_beds": 12, "updated_min": 6,
        "phone": None, "address": None, "duty_hours_text": None,
    },
    {
        "code": "B", "name": "B 권역응급의료센터", "tier": "권역응급의료센터", "lat": 37.4563, "lon": 126.8952,
        "icu_beds": 1, "ventilator": True, "er_beds": 6, "updated_min": 3,
        "phone": None, "address": None, "duty_hours_text": None,
    },
    {
        "code": "C", "name": "C 응급의료기관", "tier": "지역응급의료기관", "lat": 37.4785, "lon": 126.9612,
        "icu_beds": 0, "ventilator": False, "er_beds": 4, "updated_min": 7,
        "phone": None, "address": None, "duty_hours_text": None,
    },
]

STAGES = ["API상 후보", "전화 확인 중", "수용 확인", "최종 이송 결정"]

# data.go.kr 응급의료기관 조회서비스 제외 대상 병원종별 — 응급실 연계와 무관.
EXCLUDED_DIVS = {"치과병원", "한의원", "조산원"}


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _eta_minutes(distance_km: float) -> int:
    # 도심 구급차 평균 이동속도를 시속 25km로 가정한 근사치 — 직선거리 기준이라
    # 실제 도로 이동시간보다 짧게 나올 수 있음.
    return max(3, round(distance_km / 25 * 60))


def _duty_hours_text(start: str | None, end: str | None) -> str | None:
    def fmt(t):
        t = str(t).zfill(4)
        return f"{t[:2]}:{t[2:]}"

    if not start or not end:
        return None
    try:
        return f"{fmt(start)}~{fmt(end)}"
    except Exception:
        return None


def _minutes_since(hvidate) -> int | None:
    """hvidate: 'YYYYMMDDHHMMSS' 형식 정수/문자열 — 국립중앙의료원 기준 갱신시각."""
    if not hvidate:
        return None
    try:
        dt = datetime.strptime(str(hvidate), "%Y%m%d%H%M%S")
        return max(0, int((datetime.now() - dt).total_seconds() // 60))
    except Exception:
        return None


def _build_real_hospitals(lat: float, lon: float) -> list[dict] | None:
    """국립중앙의료원 API로 실제 병원 후보를 구성. 위치 조회나 병상 조회 중 하나라도
    실패하면 None을 반환해 호출부가 샘플로 대체하게 한다.
    캐시는 nmc_api.py의 성공한 결과에만 걸려 있다 — 여기서 또 캐시하면 실패(None)까지
    캐시되어 API가 회복돼도 한동안 계속 샘플로 보이는 문제가 생긴다."""
    nearby = nmc_api.nearby_hospitals(lat, lon, n=10)
    beds = nmc_api.all_bed_availability()
    if not nearby or beds is None:
        return None

    candidates = [h for h in nearby if h.get("dutyDivName") not in EXCLUDED_DIVS][:5]
    if not candidates:
        return None

    result = []
    for i, h in enumerate(candidates):
        hpid = h.get("hpid")
        bed = beds.get(hpid)
        icu_beds = None
        ventilator = None
        er_beds = None
        updated_min = None
        if bed:
            icu_beds = bed.get("hvicc") if isinstance(bed.get("hvicc"), (int, float)) else None
            er_beds = bed.get("hvec") if isinstance(bed.get("hvec"), (int, float)) else None
            ventilator = {"Y": True, "N": False}.get(bed.get("hvventiayn"))
            updated_min = _minutes_since(bed.get("hvidate"))
        try:
            lat_h, lon_h = float(h["latitude"]), float(h["longitude"])
        except Exception:
            continue
        result.append({
            "code": str(i + 1),
            "name": h.get("dutyName", "이름 미상"),
            "tier": h.get("dutyDivName"),
            "lat": lat_h, "lon": lon_h,
            "distance_km": round(float(h.get("distance", _haversine_km(lat, lon, lat_h, lon_h))), 1),
            "icu_beds": icu_beds, "ventilator": ventilator, "er_beds": er_beds, "updated_min": updated_min,
            "phone": h.get("dutyTel1"),
            "address": h.get("dutyAddr"),
            "duty_hours_text": _duty_hours_text(h.get("startTime"), h.get("endTime")),
        })
    return result or None


def score_hospital(h: dict, require_icu: bool, require_vent: bool) -> dict:
    known_icu = h["icu_beds"] is not None
    known_vent = h["ventilator"] is not None
    known_resource = h["er_beds"] is not None or known_icu

    # 확인된 부족(중환자실 0병상, 인공호흡기 불가)만 감점한다 — 정보가 없는 것과
    # "불가능한 것"을 같은 취급하지 않는다. 정보 없음은 전화 확인으로 넘긴다.
    clinical = 1.0
    if require_icu and known_icu and h["icu_beds"] <= 0:
        clinical -= 0.6
    if require_vent and known_vent and not h["ventilator"]:
        clinical -= 0.6
    clinical = max(0.0, clinical)

    if known_resource:
        resource = min(1.0, (max(h["er_beds"] or 0, 0) + max(h["icu_beds"] or 0, 0) * 2) / 16)
    else:
        resource = 0.5  # 정보 없음 — 가점도 감점도 하지 않는 중립값

    access = max(0.0, 1 - h["eta_min"] / 30)

    weighted = {
        "임상적합성": (0.40, clinical),
        "자원가용성": (0.25, resource),
        "이동접근성": (0.35, access),
    }
    total = sum(w * v for w, v in weighted.values())
    hard_fail = (require_icu and known_icu and h["icu_beds"] <= 0) or (require_vent and known_vent and not h["ventilator"])
    hard_pass = not hard_fail
    if not hard_pass:
        verdict = "부적합"
    elif total >= 0.75:
        verdict = "적합"
    else:
        verdict = "조건부 적합"
    return {"total": total, "parts": weighted, "hard_pass": hard_pass, "verdict": verdict}


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

confirmed: ConfirmedCase | None = st.session_state.get("confirmed_case")
if confirmed is None:
    with st.container(border=True):
        st.info("먼저 화면 3. 약물 AI 보조패널에서 사건을 분석하고 '확인 후 저장'까지 진행하세요.")
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

raw_hospitals = _build_real_hospitals(PATIENT_LOCATION["lat"], PATIENT_LOCATION["lon"])
using_real_data = raw_hospitals is not None
if not using_real_data:
    raw_hospitals = [
        {**h, "distance_km": round(_haversine_km(PATIENT_LOCATION["lat"], PATIENT_LOCATION["lon"], h["lat"], h["lon"]), 1)}
        for h in SAMPLE_HOSPITALS
    ]

hospitals_with_eta = [{**h, "eta_min": _eta_minutes(h["distance_km"])} for h in raw_hospitals]

scored = [{**h, **score_hospital(h, require_icu, require_vent)} for h in hospitals_with_eta]
passed = sorted([h for h in scored if h["hard_pass"]], key=lambda x: -x["total"])
top = passed[0] if passed else None

st.session_state.setdefault("transport_stage", 0)
stage = st.session_state["transport_stage"]
hospital = st.session_state.get("selected_hospital", top["name"] if top else None)
eta = st.session_state.get("selected_eta", top["eta_min"] if top else 0)

with st.container(border=True):
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

with st.container(border=True):
    cols = st.columns(len(STAGES))
    for i, (col, label) in enumerate(zip(cols, STAGES)):
        color = theme.BLUE if i <= stage else theme.MUTED
        col.markdown(
            f'<div style="text-align:center;"><div style="color:{color};font-weight:800;">{i + 1}. {label}</div>'
            f'<div style="height:4px;background:{color};border-radius:2px;margin-top:.4rem;margin-bottom:.8rem;"></div></div>',
            unsafe_allow_html=True,
        )
    st.caption("API상 가용병상이 있어도 실제 수용이 확정된 것은 아닙니다. 각 단계는 전화 확인 결과로만 넘어갑니다.")

col_l, col_m, col_r = st.columns([1.1, 1.3, 1], gap="small")

with col_l, st.container(border=True):
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

    def _tag(state: bool | None, label_true: str, label_false: str = "") -> str:
        if state is None:
            return f'<span style="color:{theme.MUTED};font-size:.74rem;margin-right:.6rem;">◐ 확인 필요</span>'
        color = theme.STATUS["good"] if state else theme.MUTED
        label = label_true if state else (label_false or label_true)
        return f'<span style="color:{color};font-size:.74rem;margin-right:.6rem;">{"●" if state else "○"} {label}</span>'

    for h in scored:
        badge_kind = {"적합": "good", "조건부 적합": "warning", "부적합": "critical"}[h["verdict"]]
        st.markdown(
            f'<div style="display:flex;justify-content:space-between;align-items:center;margin:.4rem 0 .15rem;">'
            f'<span><b>{h["name"]}</b> <span class="small-muted">{h["eta_min"]}분 · {h["distance_km"]}km</span></span>'
            f'{theme.status_badge(badge_kind, h["verdict"])}</div>',
            unsafe_allow_html=True,
        )
        icu_state = None if h["icu_beds"] is None else h["icu_beds"] > 0
        icu_label = f'일반중환자실 {h["icu_beds"]}병상' if h["icu_beds"] is not None else "일반중환자실"
        icu_tag = _tag(icu_state, icu_label)
        vent_tag = _tag(h["ventilator"], "인공호흡기 가능")
        st.markdown(f'<div style="margin-bottom:.1rem;">{icu_tag}{vent_tag}</div>', unsafe_allow_html=True)
        detail_bits = []
        if h.get("phone"):
            detail_bits.append(h["phone"])
        if h.get("duty_hours_text"):
            detail_bits.append(f"진료 {h['duty_hours_text']}")
        if h["updated_min"] is not None:
            detail_bits.append(f"병상정보 {h['updated_min']}분 전 갱신")
        if detail_bits:
            st.markdown(f'<div class="small-muted" style="margin-bottom:.5rem;">{" · ".join(detail_bits)}</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div style="margin-bottom:.5rem;"></div>', unsafe_allow_html=True)

    if using_real_data:
        st.caption("국립중앙의료원 응급의료기관 정보 API(실시간)로 조회한 후보입니다. 이동 시간은 직선거리 기반 추정치입니다.")
    else:
        st.caption("이동 시간은 직선거리 기반 추정치입니다.")

with col_m, st.container(border=True):
    st.markdown('<div class="section-title" style="font-size:1.05rem;">② 적합성 판단 근거</div>', unsafe_allow_html=True)
    rows = ["임상적합성", "자원가용성", "이동접근성"]
    row_colors = {
        "임상적합성": theme.CATEGORICAL["blue"],
        "자원가용성": theme.CATEGORICAL["aqua"],
        "이동접근성": theme.CATEGORICAL["orange"],
    }
    header = "".join(f"<th style='padding:.3rem .5rem;text-align:center;'>{h['code']}</th>" for h in scored)
    html = [f"<table style='width:100%;border-collapse:collapse;font-size:.82rem;'>",
            f"<tr><th style='text-align:left;padding:.3rem .5rem;'>평가 항목</th>{header}</tr>"]
    for label in rows:
        cells = "".join(
            f"<td style='padding:.3rem .5rem;text-align:center;'>{h['parts'][label][1]:.2f}</td>" for h in scored
        )
        html.append(f"<tr style='border-top:1px solid {theme.BORDER};'><td style='padding:.3rem .5rem;color:{row_colors[label]};font-weight:700;'>{label}</td>{cells}</tr>")
    verdict_cells = "".join(
        f"<td style='padding:.3rem .5rem;text-align:center;'>{theme.status_badge({'적합': 'good', '조건부 적합': 'warning', '부적합': 'critical'}[h['verdict']], h['verdict'])}</td>"
        for h in scored
    )
    html.append(f"<tr style='border-top:2px solid {theme.BORDER};'><td style='padding:.3rem .5rem;font-weight:700;'>종합 판정</td>{verdict_cells}</tr>")
    html.append("</table>")
    st.markdown("".join(html), unsafe_allow_html=True)
    st.caption("※ 본 판단은 현재 확보된 정보 기반 보조 판단이며, 실제 수용 가능 여부는 전화 확인을 통해 최종 결정됩니다.")

with col_r:
    with st.container(border=True):
        st.markdown('<div class="section-title" style="font-size:1.05rem;">③ 병원 전달문 자동생성</div>', unsafe_allow_html=True)
        if hospital:
            handoff = make_hospital_message(confirmed, age_group, sex)
            st.text_area("자동 생성 (수정 가능)", value=handoff, height=200, key="handoff_text")
            st.caption(f"수신 병원: {hospital} · 생성 시각 {datetime.now().strftime('%H:%M')}")
        else:
            st.caption("적합 후보가 없어 전달문을 생성할 수 없습니다.")

    with st.container(border=True):
        st.markdown('<div class="section-title" style="font-size:1.05rem;">연락 기록</div>', unsafe_allow_html=True)
        called_at = st.session_state.get("call_started_at")
        st.markdown(f"**{hospital or '-'}** — 연결시각 {called_at.strftime('%H:%M') if called_at else '-'} · 결과 {STAGES[stage]}")

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
        with st.container(border=True):
            st.success(f"이송 결정 확정 — 출발 {departed.strftime('%H:%M')} · 예상 도착 {arrival.strftime('%H:%M')}")
            st.caption("구급활동 기록 초안이 자동 저장됩니다.")

if using_real_data:
    st.caption(
        "병원 후보·병상정보는 국립중앙의료원 응급의료기관 정보 API(실시간)입니다. 인공호흡기·일반중환자실 병상 항목만 "
        "API가 제공하는 값으로 반영했으며, 그 외 세부 수용 조건은 전화로 반드시 재확인해야 합니다."
    )
else:
    st.caption(
        "본 코드는 공모전 MVP 시연용입니다. 병원 후보·병상정보는 샘플이며, 실제 배포 시 "
        "국립중앙의료원 응급의료기관 정보 API로 대체해야 합니다."
    )
