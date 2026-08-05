from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import data_loader as dl
import theme

st.set_page_config(
    page_title="119 약물안전 코파일럿 | 정책분석",
    page_icon="🚑",
    layout="wide",
    initial_sidebar_state="expanded",
)
theme.inject_css()
theme.render_sidebar("정책분석")

st.markdown(
    '<div class="topbar"><div>'
    '<div class="topbar-title">약물사고 정책·취약지역 분석</div>'
    '<div class="topbar-sub">예방·교육·기관협력 우선검토지역 — 자동 결정이 아닌 근거 설명</div>'
    "</div></div>",
    unsafe_allow_html=True,
)

POLICY_DIR = dl.DATA_DIR / "policy"
REGION_RENAME = {"강원특별자치도": "강원도"}


@st.cache_data(show_spinner=False)
def load_policy_events() -> pd.DataFrame:
    """2019~2023 소방청 구급상황관리 현황(약물 필터링본) 5개년 전체를 그대로 합친다 —
    표본을 줄이거나 특정 연도만 골라 쓰지 않는다."""
    frames = []
    for path in sorted(POLICY_DIR.glob("*.csv")):
        df = pd.read_csv(path, dtype=str, encoding="utf-8-sig")
        frames.append(df)
    events = pd.concat(frames, ignore_index=True)
    events["region"] = events["CTPV_NM"].replace(REGION_RENAME)
    events["bgng"] = pd.to_datetime(events["MDLCR_DSCSN_BGNG_DT"], format="%Y%m%d%H%M%S", errors="coerce")
    events["end"] = pd.to_datetime(events["MDLCR_DSCSN_END_DT"], format="%Y%m%d%H%M%S", errors="coerce")
    events["dur_min"] = (events["end"] - events["bgng"]).dt.total_seconds() / 60
    events["year"] = events["bgng"].dt.year
    events["hour"] = events["bgng"].dt.hour
    events["is_night"] = (events["hour"] >= 22) | (events["hour"] < 6)
    events["is_weekend"] = events["DCLR_DOW"].isin(["토요일", "일요일"])
    events = events.dropna(subset=["bgng", "region"])
    return events


@st.cache_data(show_spinner=False)
def region_policy_stats() -> pd.DataFrame:
    events = load_policy_events()
    # 상담시간 이상치(0분 이하·1일 이상) 제외 — 원 기획서 방법론과 동일한 기준.
    dur = events.dropna(subset=["dur_min"])
    dur = dur[(dur["dur_min"] > 0) & (dur["dur_min"] < 1440)]

    rows = []
    for region in dl.REGION_ORDER:
        r_all = events[events["region"] == region]
        r_dur = dur[dur["region"] == region]
        if r_all.empty:
            continue
        by_year = r_all.groupby("year").size()
        n_2019 = int(by_year.get(2019, 0))
        n_2023 = int(by_year.get(2023, 0))
        growth = ((n_2023 - n_2019) / n_2019 * 100) if n_2019 > 0 else None

        rows.append({
            "region": region,
            "region_short": dl.REGION_SHORT[region],
            "total_n": int(len(r_all)),
            "n_2019": n_2019,
            "n_2023": n_2023,
            "growth_pct": growth,
            "night_pct": float(r_all["is_night"].mean() * 100),
            "weekend_pct": float(r_all["is_weekend"].mean() * 100),
            "median_min": float(r_dur["dur_min"].median()) if len(r_dur) else None,
            "p90_min": float(r_dur["dur_min"].quantile(0.9)) if len(r_dur) else None,
            "pct_gt20": float((r_dur["dur_min"] > 20).mean() * 100) if len(r_dur) else None,
        })
    return pd.DataFrame(rows)


stats = region_policy_stats()

# 설명 가능한 다기준 우선순위 — 학습된 블랙박스 점수가 아니라, 문서가 명시한 세 지표
# (증가율·야간비율·20분초과비율)를 0~1로 정규화해 단순 평균한 것. 결정이 아니라
# "왜 이 지역이 위에 있는지" 그대로 보여주기 위한 설명용 랭킹이다.
def _normalize(s: pd.Series) -> pd.Series:
    lo, hi = s.min(), s.max()
    if hi == lo:
        return s * 0
    return (s - lo) / (hi - lo)


scoreable = stats.dropna(subset=["growth_pct", "pct_gt20"]).copy()
scoreable["score"] = (
    _normalize(scoreable["growth_pct"]) + _normalize(scoreable["night_pct"]) + _normalize(scoreable["pct_gt20"])
) / 3
scoreable = scoreable.sort_values("score", ascending=False)
top5 = scoreable.head(5)

k1, k2, k3, k4 = st.columns(4)
total_n = int(stats["total_n"].sum())
k1.markdown(f'<div class="card"><div class="kpi-label">2019~2023 약물 관련 상담</div><div class="kpi-value">{total_n:,}건</div>'
            f'<div class="kpi-delta muted">전국 17개 시도 합계</div></div>', unsafe_allow_html=True)
k2.markdown(f'<div class="card"><div class="kpi-label">최다 발생 시도</div>'
            f'<div class="kpi-value">{stats.loc[stats["total_n"].idxmax(), "region_short"]}</div>'
            f'<div class="kpi-delta muted">{int(stats["total_n"].max()):,}건</div></div>', unsafe_allow_html=True)
top_growth = scoreable.iloc[0] if len(scoreable) else None
k3.markdown(f'<div class="card"><div class="kpi-label">우선검토 1순위</div>'
            f'<div class="kpi-value">{top_growth["region_short"] if top_growth is not None else "-"}</div>'
            f'<div class="kpi-delta muted">증가율·야간비율·장시간비율 종합</div></div>', unsafe_allow_html=True)

try:
    with open(Path(__file__).resolve().parent.parent / "data_stats_2023.json", encoding="utf-8") as f:
        national = json.load(f)
    ratio20 = national["drug"]["pct_gt20"] / national["other"]["pct_gt20"]
    k4.markdown(f'<div class="card"><div class="kpi-label">약물 상담 장시간화(20분 초과)</div>'
                f'<div class="kpi-value">{ratio20:.1f}배</div>'
                f'<div class="kpi-delta muted">2023년 전체 상담 대비(직접 재현)</div></div>', unsafe_allow_html=True)
except FileNotFoundError:
    national = None
    k4.markdown('<div class="card"><div class="kpi-label">약물 상담 장시간화</div><div class="kpi-value">-</div></div>', unsafe_allow_html=True)

st.markdown("<div style='height:.3rem;'></div>", unsafe_allow_html=True)

left, right = st.columns([1.5, 1], gap="large")

with left:
    with st.container(border=True):
        st.markdown('<div class="section-title">시도별 우선검토 근거 비교</div>', unsafe_allow_html=True)
        show = scoreable[["region_short", "total_n", "growth_pct", "night_pct", "weekend_pct", "median_min", "pct_gt20", "score"]].copy()
        show.columns = ["시도", "5개년 건수", "증가율(19→23,%)", "야간비율(%)", "주말비율(%)", "상담시간 중앙값(분)", "20분초과비율(%)", "우선검토 점수"]
        for c in show.columns[2:]:
            show[c] = show[c].round(1)
        st.dataframe(show, hide_index=True, use_container_width=True, height=380)
        st.caption(
            "우선검토 점수 = (증가율·야간비율·20분초과비율을 각각 0~1로 정규화한 뒤 평균) — "
            "AI가 자동으로 지역을 확정하지 않으며, 실제 예방·교육·기관협력 대상 선정은 담당 부서 검토를 거칩니다."
        )

    with st.container(border=True):
        st.markdown('<div class="section-title">우선검토 상위 5개 시도</div>', unsafe_allow_html=True)
        fig = go.Figure(go.Bar(
            x=top5["score"], y=top5["region_short"], orientation="h",
            marker_color=theme.NAVY,
            text=[f"{v:.2f}" for v in top5["score"]], textposition="outside",
        ))
        fig.update_layout(**theme.plotly_layout_defaults(), height=220, xaxis_title="우선검토 점수(0~1)")
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

with right:
    with st.container(border=True):
        st.markdown('<div class="section-title">약물 상담 vs 전체 상담 — 소요시간</div>', unsafe_allow_html=True)
        if national:
            d, o = national["drug"], national["other"]
            rows_html = "".join(
                f'<div class="map-row"><span class="map-name">{label}</span>'
                f'<span class="map-value">약물 {d[key]:.1f}{unit} · 전체 {o[key]:.1f}{unit}</span></div>'
                for label, key, unit in [
                    ("중앙값", "median", "분"), ("P90", "p90", "분"),
                    ("10분 초과 비율", "pct_gt10", "%"), ("20분 초과 비율", "pct_gt20", "%"), ("30분 초과 비율", "pct_gt30", "%"),
                ]
            )
            st.markdown(f'<div class="mapping-box">{rows_html}</div>', unsafe_allow_html=True)
            st.caption(
                f"2023년 전국 {national['other']['n'] + national['drug']['n']:,}건(0분 이하·1일 이상 제외) 기준 저희가 직접 재현한 값입니다. "
                "기획서에 인용된 수치(예: 20분 초과 4.15배)와는 추가 필터링 기준 차이로 정확히 일치하지 않을 수 있습니다."
            )
        else:
            st.caption("전국 비교 통계 파일(data_stats_2023.json)이 없습니다.")

    with st.container(border=True):
        st.markdown('<div class="section-title">범위 밖 안내</div>', unsafe_allow_html=True)
        st.caption(
            "기획서는 '약물중환자 대응기관 접근성'도 우선검토 지표로 제시하지만, 이 MVP는 "
            "국립중앙의료원 응급의료기관 정보 API와 아직 연동되어 있지 않아 지어내지 않고 "
            "이번 버전 점수에서 제외했습니다. 화면5(병원연계)의 샘플 병원 3곳만으로는 "
            "전국 단위 접근성을 대표할 수 없기 때문입니다."
        )
