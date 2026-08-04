from __future__ import annotations

import datetime as dt

import plotly.graph_objects as go
import streamlit as st

import data_loader as dl
import theme

DEMO_YEAR = 2026

CAT_ORDER = ["약물과다", "약물중독", "약물오용", "약물부작용", "마약중독"]
CAT_COLORS = [
    theme.CATEGORICAL["blue"],
    theme.CATEGORICAL["aqua"],
    theme.CATEGORICAL["orange"],
    theme.CATEGORICAL["magenta"],
    theme.CATEGORICAL["violet"],
]


def _kpi(col, label: str, value: str, delta: str | None = None, delta_color: str = theme.TEXT_SECONDARY) -> None:
    delta_html = f'<div class="kpi-delta" style="color:{delta_color}">{delta}</div>' if delta else ""
    col.markdown(
        f"""
        <div class="card">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
            {delta_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render() -> None:
    c1, c2 = st.columns([1, 1])
    selected_date = c1.date_input(
        "기준 날짜",
        value=dt.date(DEMO_YEAR, 8, 4),
        min_value=dt.date(DEMO_YEAR, 1, 1),
        max_value=dt.date(DEMO_YEAR, 12, 31),
        format="YYYY-MM-DD",
        key="dash_date",
    )
    month_day = selected_date.strftime("%m-%d")
    up_to_slot = c2.select_slider(
        "실시간 진행 시각 — 이 시각까지 신고가 들어온 것으로 시뮬레이션",
        options=dl.SLOTS,
        value=12,
        format_func=lambda h: f"{h:02d}:00",
        key="dash_slot",
    )
    st.caption(
        "실제·예측 모두 2024년 합성 실시간 입력 샘플(SYNTHETIC_119_SIMULATOR) 기반 · "
        "예측 = 그 시점까지 누적된 데이터로 계산한 최근 7일 이동평균 + 동일 요일·시간대 평균"
    )

    series = dl.national_day_series(month_day)
    snapshot = dl.region_day_snapshot(month_day, up_to_slot)
    snapshot["risk"] = snapshot["ratio_vs_baseline"].map(dl.risk_level)
    mix = dl.category_mix(month_day, up_to_slot)

    actual_so_far = int(snapshot["actual_so_far"].sum())
    predicted_remaining = round(float(snapshot["predicted_remaining"].sum()), 1)
    predicted_so_far = round(float(snapshot["predicted_so_far"].sum()), 1)
    delta_pct = ((actual_so_far - predicted_so_far) / predicted_so_far * 100) if predicted_so_far > 0 else 0.0
    top_type = mix.sort_values("count", ascending=False).iloc[0] if not mix.empty else None
    alert_regions = snapshot[snapshot["risk"].isin(["경계", "심각"])].sort_values("ratio_vs_baseline", ascending=False)

    k1, k2, k3, k4 = st.columns(4)
    _kpi(k1, "오늘 누적 약물 관련 신고 (00시~현재)", f"{actual_so_far}건",
         f"모델 예측 대비 {delta_pct:+.0f}%", theme.STATUS["critical"] if delta_pct > 20 else theme.TEXT_SECONDARY)
    _kpi(k2, f"향후 {24 - up_to_slot}시간 예상", f"{predicted_remaining:.0f}건", "잔여 슬롯 예측 합")
    if top_type is not None:
        pct = top_type["count"] / mix["count"].sum() * 100
        _kpi(k3, "유형 구성 1위", f"{top_type['label']}", f"{pct:.0f}% ({int(top_type['count'])}건)")
    else:
        _kpi(k3, "유형 구성", "데이터 없음")
    _kpi(k4, "이상징후 발생지역", f"{len(alert_regions)}곳", "평시 대비 1.5배 이상")

    left, right = st.columns([1.5, 1])

    with left:
        with st.container(border=True):
            st.markdown("**시간대별 신고량 — 실제 대 예측 (전국 합계)**")
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=[f"{h:02d}시" for h in dl.SLOTS], y=series["prediction"],
                name="예측", mode="lines+markers",
                line=dict(color=theme.CATEGORICAL["blue"], dash="dash", width=2),
                marker=dict(size=6),
            ))
            actual_masked = series["actual"].where(series["slot"] <= up_to_slot)
            fig.add_trace(go.Scatter(
                x=[f"{h:02d}시" for h in dl.SLOTS], y=actual_masked,
                name="실제", mode="lines+markers",
                line=dict(color=theme.STATUS["critical"], width=2.5),
                marker=dict(size=7),
            ))
            fig.add_vline(x=dl.SLOTS.index(up_to_slot), line_width=1, line_dash="dot",
                           line_color=theme.TEXT_MUTED, annotation_text=f"현재 {up_to_slot:02d}:00",
                           annotation_font_color=theme.TEXT_SECONDARY)
            fig.update_layout(**theme.plotly_layout_defaults(), height=340)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        with st.container(border=True):
            st.markdown("**시도별 위험도 · 현재 누적 기준**")
            cols = st.columns(6)
            badge_color = {
                "관심": theme.STATUS["good"], "주의": theme.STATUS["warning"],
                "경계": theme.STATUS["serious"], "심각": theme.STATUS["critical"],
            }
            for i, row in snapshot.sort_values("region_short").reset_index().iterrows():
                col = cols[i % 6]
                color = badge_color[row["risk"]]
                col.markdown(
                    f"""
                    <div class="region-tile" style="border-color:{color}66;background:{color}14;">
                        <div class="region-name">{row['region_short']}</div>
                        <div class="region-count" style="color:{color}">{row['actual_so_far']}</div>
                        <div class="muted">{row['risk']}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            st.markdown(
                '<div class="muted" style="margin-top:.6rem;">위험도 = 현재까지 실제 신고 ÷ 동일 시점까지의 평시(모델) 예측 누적</div>',
                unsafe_allow_html=True,
            )

    with right:
        with st.container(border=True):
            if len(alert_regions):
                top = alert_regions.iloc[0]
                badge_label = f"이상징후 · {top['risk']}"
                st.markdown(theme.status_badge(top["risk"], badge_label), unsafe_allow_html=True)
                st.markdown(f"**{top['region_short']} · 평시 대비 {top['ratio_vs_baseline']:.1f}배**")
                st.caption(f"현재까지 실제 {int(top['actual_so_far'])}건 · 동시점 예측 {top['predicted_so_far']:.1f}건")
            else:
                st.markdown(theme.status_badge("관심", "이상징후 없음"), unsafe_allow_html=True)
                st.caption("모든 지역이 평시 대비 1.5배 미만입니다.")

        with st.container(border=True):
            st.markdown("**AI 교대 브리핑**")
            if len(alert_regions):
                top = alert_regions.iloc[0]
                brief = (
                    f"{month_day} {up_to_slot:02d}시 기준, 약물 관련 신고는 전국적으로 "
                    f"모델 예측 대비 {delta_pct:+.0f}% 수준입니다. {top['region_short']} 지역이 "
                    f"평시 대비 {top['ratio_vs_baseline']:.1f}배로 가장 두드러지며, "
                    f"주요 유형은 {top_type['label'] if top_type is not None else '미상'}입니다."
                )
            else:
                brief = (
                    f"{month_day} {up_to_slot:02d}시 기준, 약물 관련 신고는 평시 수준입니다. "
                    f"이상징후가 감지된 지역은 없습니다."
                )
            st.info(brief)
            st.caption("예측·탐지 결과만으로 생성 · 입력값에 없는 내용은 작성하지 않음")

        with st.container(border=True):
            st.markdown("**유형 분포 (현재까지)**")
            if not mix.empty:
                ordered = mix.set_index("main_symptom").reindex(CAT_ORDER + [
                    c for c in mix["main_symptom"] if c not in CAT_ORDER
                ]).dropna(subset=["count"]).reset_index()
                colors = (CAT_COLORS + [theme.TEXT_MUTED] * len(ordered))[: len(ordered)]
                fig2 = go.Figure(go.Pie(
                    labels=ordered["label"], values=ordered["count"], hole=0.55,
                    marker=dict(colors=colors, line=dict(color=theme.CARD_BG, width=2)),
                    textinfo="percent",
                ))
                fig2.update_layout(**theme.plotly_layout_defaults(), height=280, showlegend=True)
                st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})
            else:
                st.caption("표시할 데이터가 없습니다.")
