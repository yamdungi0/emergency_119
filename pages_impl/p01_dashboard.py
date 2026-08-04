from __future__ import annotations

import datetime as dt

import pandas as pd
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

    # 기획서 정의: "향후 3시간 예상"은 자정까지 남은 슬롯 전체 합이 아니라,
    # 지금 시점 바로 다음 3시간 슬롯 하나의 예측치다 (예: "오늘 20~24시 예상 17건").
    # 표시 날짜는 2026년으로 보이지만 실데이터는 2024년 패널에 있으므로,
    # 월-일·시각만으로 매칭한다 (연도는 비교하지 않음).
    next_start = pd.Timestamp(selected_date) + pd.Timedelta(hours=int(up_to_slot) + 3)
    next_end = next_start + pd.Timedelta(hours=3)
    panel = dl.load_2024_panel()
    next_window_pred = float(
        panel.loc[
            (panel["month_day"] == next_start.strftime("%m-%d")) & (panel["slot"] == next_start.hour),
            "prediction",
        ].sum()
    )

    actual_so_far = int(snapshot["actual_so_far"].sum())
    predicted_so_far = round(float(snapshot["predicted_so_far"].sum()), 1)
    delta_pct = ((actual_so_far - predicted_so_far) / predicted_so_far * 100) if predicted_so_far > 0 else 0.0
    top_type = mix.sort_values("count", ascending=False).iloc[0] if not mix.empty else None
    alert_regions = snapshot[snapshot["risk"].isin(["경계", "심각"])].sort_values("ratio_vs_baseline", ascending=False)

    k1, k2, k3, k4 = st.columns(4)
    _kpi(k1, "오늘 누적 약물 관련 신고 (00시~현재)", f"{actual_so_far}건",
         f"모델 예측 대비 {delta_pct:+.0f}%", theme.STATUS["critical"] if delta_pct > 20 else theme.TEXT_SECONDARY)
    _kpi(k2, "향후 3시간 예상", f"{next_window_pred:.0f}건",
         f"{next_start.strftime('%H:%M')}~{next_end.strftime('%H:%M')} 구간")
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
            st.markdown("**시도별 실시간 위험도 지도 · 현재 누적 기준**")
            badge_color = {
                "관심": theme.STATUS["good"], "주의": theme.STATUS["warning"],
                "경계": theme.STATUS["serious"], "심각": theme.STATUS["critical"],
            }
            map_df = snapshot.copy()
            map_df["lat"] = map_df["region"].map(lambda r: dl.REGION_COORDS[r][0])
            map_df["lon"] = map_df["region"].map(lambda r: dl.REGION_COORDS[r][1])
            map_df["marker_size"] = 16 + map_df["actual_so_far"] * 3.5

            fig_map = go.Figure()
            for risk_level in ["관심", "주의", "경계", "심각"]:
                level_df = map_df[map_df["risk"] == risk_level]
                if level_df.empty:
                    continue
                fig_map.add_trace(go.Scattermapbox(
                    lat=level_df["lat"], lon=level_df["lon"],
                    mode="markers+text",
                    marker=dict(size=level_df["marker_size"], color=badge_color[risk_level]),
                    text=[f"{r} {c}" for r, c in zip(level_df["region_short"], level_df["actual_so_far"])],
                    textposition="top center",
                    name=risk_level,
                    hovertext=[
                        f"{r}<br>실제 누적 {c}건<br>평시 대비 {ratio:.1f}배<br>위험도 {risk_level}"
                        for r, c, ratio in zip(level_df["region_short"], level_df["actual_so_far"], level_df["ratio_vs_baseline"])
                    ],
                    hoverinfo="text",
                ))
            fig_map.update_layout(
                mapbox=dict(style="carto-positron", center=dict(lat=36.4, lon=127.9), zoom=5.6),
                paper_bgcolor=theme.CARD_BG,
                margin=dict(l=0, r=0, t=0, b=0),
                height=460,
                legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="left", x=0),
            )
            st.plotly_chart(fig_map, use_container_width=True, config={"displayModeBar": False})
            st.markdown(
                '<div class="muted" style="margin-top:.4rem;">마커 크기 = 실제 누적 건수 · 색상 = 위험도 · '
                '위험도 = 현재까지 실제 신고 ÷ 동일 시점까지의 평시(모델) 예측 누적</div>',
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
