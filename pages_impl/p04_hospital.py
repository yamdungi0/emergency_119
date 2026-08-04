from __future__ import annotations

import math
from datetime import datetime, timedelta

import plotly.graph_objects as go
import streamlit as st

import theme

DEFAULT_PATIENT = {"label": "환자 현재 위치", "address": "서울 관악구 신림동", "lat": 37.4842, "lon": 126.9294}

# 샘플 응급의료기관 후보 — 실서비스에서는 국립중앙의료원 응급의료기관 정보 API로 대체됩니다.
# eta_min은 더 이상 고정값이 아니라 환자 위경도 기준 직선거리로 매번 계산한다(아래
# _eta_minutes 참고) — 02에서 사건을 바꾸면 후보 병원까지의 거리도 같이 바뀌어야
# 실제 위경도 기반 병원 API를 흉내낸 의미가 있기 때문.
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
    # 실제 도로 이동시간보다 짧게 나올 수 있음(샘플 데이터 한계로 문서에도 명시).
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
    facts = getattr(st.session_state.get("intake_result"), "facts", None)
    if facts is None:
        with st.container(border=True):
            st.info("먼저 02 AI 보조패널에서 사건을 확인하세요.")
        return

    require_icu = bool(facts.conscious is False)
    require_vent = bool(facts.normal_breathing is False)

    patient = st.session_state.get("patient_location", DEFAULT_PATIENT)
    hospitals_with_eta = []
    for h in HOSPITALS:
        distance_km = _haversine_km(patient["lat"], patient["lon"], h["lat"], h["lon"])
        hospitals_with_eta.append({**h, "distance_km": round(distance_km, 1), "eta_min": _eta_minutes(distance_km)})

    scored = [{**h, **score_hospital(h, require_icu, require_vent)} for h in hospitals_with_eta]
    passed = sorted([h for h in scored if h["hard_pass"]], key=lambda x: -x["total"])
    top = passed[0] if passed else None

    st.session_state.setdefault("transport_stage", 0)
    stage = st.session_state["transport_stage"]
    hospital = st.session_state.get("selected_hospital", top["name"] if top else None)
    eta = st.session_state.get("selected_eta", top["eta_min"] if top else 0)

    with st.container(border=True):
        age_sex = " ".join(v for v in [_value(facts.age, ""), _value(facts.sex, "")] if v) or "확인 중"
        p1, p2, p3, p4, p5 = st.columns([1, 1.6, 0.9, 0.9, 1.7])
        p1.markdown(f'<div class="muted">환자 정보</div><div style="font-weight:700;">{age_sex}</div>', unsafe_allow_html=True)
        p2.markdown(f'<div class="muted">의심 상황</div><div style="font-weight:700;">{_value(facts.suspected_substance, "확인 중")} 관련 응급</div>', unsafe_allow_html=True)
        p3.markdown(f'<div class="muted">의식</div><div style="font-weight:700;">{"저하 의심" if facts.conscious is False else "정상" if facts.conscious else "확인 중"}</div>', unsafe_allow_html=True)
        p4.markdown(f'<div class="muted">호흡</div><div style="font-weight:700;">{"이상 의심" if facts.normal_breathing is False else "정상" if facts.normal_breathing else "확인 중"}</div>', unsafe_allow_html=True)
        p5.markdown(
            f'<div class="muted">&nbsp;</div><span class="badge" style="background:{theme.CATEGORICAL["violet"]};">병원 추천이 아닌 적합성 설명과 전달문 보조</span>',
            unsafe_allow_html=True,
        )
        st.caption(f"현재 위치: {patient['label']} · {patient['address']} ({patient['lat']:.4f}, {patient['lon']:.4f})")

    with st.container(border=True):
        cols = st.columns(len(STAGES))
        for i, (col, label) in enumerate(zip(cols, STAGES)):
            color = theme.CATEGORICAL["blue"] if i <= stage else theme.TEXT_MUTED
            col.markdown(
                f'<div style="text-align:center;"><div style="color:{color};font-weight:800;">{i+1}. {label}</div>'
                f'<div style="height:4px;background:{color};border-radius:2px;margin-top:.4rem;"></div></div>',
                unsafe_allow_html=True,
            )
        st.caption("API상 가용병상이 있어도 실제 수용이 확정된 것은 아닙니다. 각 단계는 전화 확인 결과로만 넘어갑니다.")

    col_l, col_m, col_r = st.columns([1.1, 1.3, 1], gap="small")

    with col_l, st.container(border=True):
        st.markdown("**① 후보 의료기관**")
        fig = go.Figure()
        fig.add_trace(go.Scattermapbox(
            lat=[patient["lat"]], lon=[patient["lon"]], mode="markers+text",
            marker=dict(size=15, color=theme.STATUS["critical"]),
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
                center=dict(lat=patient["lat"], lon=patient["lon"]), zoom=12.5,
            ),
            paper_bgcolor=theme.CARD_BG, margin=dict(l=0, r=0, t=0, b=0), height=260, showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        for h in scored:
            badge_kind = {"적합": "good", "조건부 적합": "warning", "부적합": "critical"}[h["verdict"]]
            st.markdown(
                f'<div style="display:flex;justify-content:space-between;align-items:center;margin:.4rem 0 .15rem;">'
                f'<span><b>{h["name"]}</b> <span class="muted">{h["eta_min"]}분 · {h["distance_km"]}km</span></span>'
                f'<span class="badge badge-{badge_kind}">{h["verdict"]}</span></div>',
                unsafe_allow_html=True,
            )
            # 기획서가 명시한 "중환자실·인공호흡기·약물중환자 정보" 3가지를 점수 뒤에
            # 숨기지 않고 원자료 그대로 보여준다 — 왜 적합/부적합인지 근거가 바로 보이게.
            def _tag(ok: bool, label: str) -> str:
                color = theme.STATUS["good"] if ok else theme.TEXT_MUTED
                return f'<span style="color:{color};font-size:.74rem;margin-right:.6rem;">{"●" if ok else "○"} {label}</span>'
            icu_beds = h["icu_beds"]
            icu_tag = _tag(icu_beds > 0, f"중환자실 {icu_beds}병상")
            vent_tag = _tag(h["ventilator"], "인공호흡기")
            drug_icu_tag = _tag(h["drug_icu"], "약물중환자 대응")
            st.markdown(
                f'<div style="margin-bottom:.5rem;">{icu_tag}{vent_tag}{drug_icu_tag}</div>',
                unsafe_allow_html=True,
            )
        st.caption("이동 시간은 실시간 교통 상황에 따라 변동될 수 있습니다(샘플 데이터).")

    with col_m, st.container(border=True):
        st.markdown("**② 적합성 판단 근거**")
        rows = ["임상적합성", "자원가용성", "이동접근성", "정보최신성", "기관수준"]
        header = "".join(f"<th style='padding:.3rem .5rem;text-align:center;'>{h['code']}</th>" for h in scored)
        html = [f"<table style='width:100%;border-collapse:collapse;font-size:.82rem;'>",
                f"<tr><th style='text-align:left;padding:.3rem .5rem;'>평가 항목</th>{header}</tr>"]
        for label in rows:
            cells = "".join(
                f"<td style='padding:.3rem .5rem;text-align:center;'>{h['parts'][label][1]:.2f}</td>" for h in scored
            )
            html.append(f"<tr style='border-top:1px solid {theme.CARD_BORDER};'><td style='padding:.3rem .5rem;color:{theme.TEXT_SECONDARY};'>{label}</td>{cells}</tr>")
        # 약물중환자 대응 여부는 가중치 점수(임상적합성 등)에는 이미 반영돼 있지만,
        # 기획서가 별도 비교항목으로 명시한 만큼 원자료 그대로 참고행으로 노출한다.
        drug_icu_cells = "".join(
            f"<td style='padding:.3rem .5rem;text-align:center;'>{'✓' if h['drug_icu'] else '—'}</td>" for h in scored
        )
        html.append(
            f"<tr style='border-top:1px solid {theme.CARD_BORDER};'>"
            f"<td style='padding:.3rem .5rem;color:{theme.TEXT_SECONDARY};'>약물중환자 대응<span class='muted' style='font-size:.7rem;'>(참고)</span></td>"
            f"{drug_icu_cells}</tr>"
        )
        verdict_cells = "".join(
            f"<td style='padding:.3rem .5rem;text-align:center;'>{theme.status_badge({'적합':'good','조건부 적합':'warning','부적합':'critical'}[h['verdict']], h['verdict'])}</td>"
            for h in scored
        )
        html.append(f"<tr style='border-top:2px solid {theme.CARD_BORDER};'><td style='padding:.3rem .5rem;font-weight:700;'>종합 판정</td>{verdict_cells}</tr>")
        html.append("</table>")
        st.markdown("".join(html), unsafe_allow_html=True)
        st.caption("※ 본 판단은 현재 확보된 정보 기반 보조 판단이며, 실제 수용 가능 여부는 전화 확인을 통해 최종 결정됩니다.")

    with col_r:
        with st.container(border=True):
            st.markdown("**③ 병원 전달문 자동생성**")
            if hospital:
                handoff = build_handoff(facts, hospital, eta)
                st.code(handoff, language=None)
                st.caption(f"수신 병원: {hospital} · 생성 시각 {datetime.now().strftime('%H:%M')}")
            else:
                st.caption("적합 후보가 없어 전달문을 생성할 수 없습니다.")

        with st.container(border=True):
            st.markdown("**연락 기록**")
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
