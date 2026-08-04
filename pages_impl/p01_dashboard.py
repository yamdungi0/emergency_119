from __future__ import annotations

import datetime as dt

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import data_loader as dl
import theme

DEMO_YEAR = 2026

# 밝은 톤 — 유형 분포 도넛과 "유형 구성 1위" KPI가 같은 색을 공유한다.
# 레드(RED)는 앱 전역에서 경보 전용 색이라 일반 유형 구분에는 쓰지 않고,
# 대신 따뜻한 주황→차가운 청록·블루·바이올렛으로 대비를 준다.
CAT_ORDER = ["약물과다", "약물중독", "약물오용", "약물부작용", "마약중독"]
CAT_COLORS = ["#4C6FE7", "#F2994A", "#2FB6A5", "#8B6FE0", "#E8748F"]
CAT_COLOR_MAP = dict(zip(CAT_ORDER, CAT_COLORS))


def _title(text: str) -> None:
    st.markdown(f'<div class="section-title">{text}</div>', unsafe_allow_html=True)


def _kpi(col, label: str, value: str, delta: str | None = None,
         delta_color: str = theme.TEXT_SECONDARY, value_color: str | None = None,
         icon: str | None = None, icon_color: str = theme.NAVY) -> None:
    delta_html = f'<div class="kpi-delta" style="color:{delta_color}">{delta}</div>' if delta else ""
    value_style = f"color:{value_color};" if value_color else ""
    icon_html = theme.kpi_icon_svg(icon, icon_color) if icon else ""
    col.markdown(
        f"""
        <div class="card">
            <div class="kpi-header">
                {icon_html}
                <div class="kpi-label">{label}</div>
            </div>
            <div class="kpi-value" style="{value_style}">{value}</div>
            {delta_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render() -> None:
    # 응급 상황판 특성상 스크롤 없이 한 화면에 다 보이도록 3열로 배치한다:
    # 왼쪽=핵심 지표, 가운데=날짜·그래프·브리핑, 오른쪽=유형분포·지도·이상징후.
    kpi_col, main_col, side_col = st.columns([0.9, 2.1, 1.7], gap="small")

    panel = dl.load_2024_panel()

    with main_col:
        selected_date = st.date_input(
            "기준 날짜",
            value=dt.date(DEMO_YEAR, 8, 4),
            min_value=dt.date(DEMO_YEAR, 1, 1),
            max_value=dt.date(DEMO_YEAR, 12, 31),
            format="YYYY-MM-DD",
            key="dash_date",
        )
        month_day = selected_date.strftime("%m-%d")
        chart_box = st.container(border=True)
        up_to_slot = st.select_slider(
            "실시간 진행 시각 — 이 시각까지 신고가 들어온 것으로 시뮬레이션",
            options=dl.SLOTS,
            value=12,
            format_func=lambda h: f"{h:02d}:00",
            key="dash_slot",
        )
        briefing_box = st.container(border=True)

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

    with kpi_col:
        _kpi(st, "오늘 누적 약물 관련 신고 (00시~현재)", f"{actual_so_far}건",
             f"모델 예측 대비 {delta_pct:+.0f}%", theme.STATUS["critical"] if delta_pct > 20 else theme.TEXT_SECONDARY,
             icon="list", icon_color=theme.CATEGORICAL["blue"])
        _kpi(st, "향후 3시간 예상", f"{next_window_pred:.0f}건",
             f"{next_start.strftime('%H:%M')}~{next_end.strftime('%H:%M')} 구간",
             icon="clock", icon_color=theme.CATEGORICAL["aqua"])
        if top_type is not None:
            pct = top_type["count"] / mix["count"].sum() * 100
            top_color = CAT_COLOR_MAP.get(top_type["main_symptom"], theme.TEXT_PRIMARY)
            _kpi(st, "유형 구성 1위", f"{top_type['label']}", f"{pct:.0f}% ({int(top_type['count'])}건)",
                 value_color=top_color, icon="pie", icon_color=theme.CATEGORICAL["magenta"])
        else:
            _kpi(st, "유형 구성", "데이터 없음", icon="pie", icon_color=theme.CATEGORICAL["magenta"])
        _kpi(st, "이상징후 발생지역", f"{len(alert_regions)}곳", "평시 대비 1.5배 이상",
             icon="alert", icon_color=theme.STATUS["critical"])

        with st.container(border=True):
            _title("유형 분포")
            if not mix.empty:
                ordered = mix.set_index("main_symptom").reindex(CAT_ORDER + [
                    c for c in mix["main_symptom"] if c not in CAT_ORDER
                ]).dropna(subset=["count"]).reset_index()
                colors = (CAT_COLORS + [theme.TEXT_MUTED] * len(ordered))[: len(ordered)]
                fig2 = go.Figure(go.Pie(
                    labels=ordered["label"], values=ordered["count"], hole=0.55,
                    marker=dict(colors=colors, line=dict(color=theme.CARD_BG, width=2)),
                    textinfo="percent", textfont=dict(size=9),
                ))
                layout_defaults = theme.plotly_layout_defaults()
                layout_defaults["margin"] = dict(l=4, r=4, t=4, b=4)
                layout_defaults["legend"] = dict(
                    orientation="h", yanchor="top", y=-0.05, xanchor="center", x=0.5,
                    font=dict(size=9),
                )
                fig2.update_layout(**layout_defaults, height=250, showlegend=True)
                st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})
            else:
                st.caption("표시할 데이터가 없습니다.")

    with chart_box:
        _title("시간대별 신고량 — 실제 대 예측 (전국 합계)")
        fig = go.Figure()
        # x축은 하루 마지막 3시간 구간(21시~24시)의 끝을 보여주기 위해 "24시" 눈금을
        # 하나 더 붙인다 — 실제 슬롯은 00,03,...,21시 8개뿐이라 데이터 점은 없다.
        slot_labels = [f"{h:02d}시" for h in dl.SLOTS] + ["24시"]

        actual_masked = series["actual"].where(series["slot"] <= up_to_slot)
        fig.add_trace(go.Scatter(
            x=slot_labels[:-1], y=actual_masked,
            name="실제", mode="lines+markers",
            line=dict(color=theme.STATUS["critical"], width=2.5),
            marker=dict(size=7),
        ))

        # 예측은 "지금(up_to_slot)"부터 하루 끝(21시 슬롯)까지 이어 그린다 — 각 슬롯의
        # 예측값 자체가 causal(그 시점까지의 데이터만 사용)하게 3시간 단위로 계산된
        # 것이므로, 이어 그려도 미래를 미리 아는 게 아니라 "3시간마다 갱신되는 예측을
        # 누적해 보여주는 것"이다. 실제선 끝(지금)에서 시작해 자연스럽게 이어진다.
        now_actual = float(series.loc[series["slot"] == up_to_slot, "actual"].iloc[0])
        future_mask = series["slot"] >= up_to_slot
        pred_x = [f"{h:02d}시" for h in series.loc[future_mask, "slot"]]
        pred_y = series.loc[future_mask, "prediction"].tolist()
        pred_x[0], pred_y[0] = f"{up_to_slot:02d}시", now_actual
        fig.add_trace(go.Scatter(
            x=pred_x, y=pred_y,
            name="예측", mode="lines+markers",
            line=dict(color=theme.CATEGORICAL["blue"], dash="dash", width=2),
            marker=dict(size=6),
        ))

        # 카테고리 축은 실제로 데이터가 찍힌 x값만 눈금으로 인식하므로, "24시"는
        # 어느 트레이스에도 없으면 아예 표시되지 않는다 — 보이지 않는 더미 점으로
        # 카테고리 존재만 등록한다.
        fig.add_trace(go.Scatter(
            x=["24시"], y=[None], mode="markers",
            marker=dict(opacity=0), showlegend=False, hoverinfo="skip",
        ))

        fig.add_vline(x=dl.SLOTS.index(up_to_slot), line_width=1, line_dash="dot",
                       line_color=theme.TEXT_MUTED, annotation_text=f"현재 {up_to_slot:02d}:00",
                       annotation_font_color=theme.TEXT_SECONDARY)
        layout_defaults = theme.plotly_layout_defaults()
        layout_defaults["xaxis"] = {**layout_defaults["xaxis"], "categoryorder": "array", "categoryarray": slot_labels}
        fig.update_layout(**layout_defaults, height=320)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with briefing_box:
        _title("AI 교대 브리핑")
        if len(alert_regions):
            top = alert_regions.iloc[0]
            brief = (
                f"{month_day} {up_to_slot:02d}시 기준, 약물 관련 신고는 전국적으로 "
                f"모델 예측 대비 {delta_pct:+.0f}% 수준입니다. {top['region_short']} 지역이 "
                f"실제 {int(top['actual_so_far'])}건(평시 대비 {top['ratio_vs_baseline']:.1f}배)으로 가장 두드러지며, "
                f"주요 유형은 {top_type['label'] if top_type is not None else '미상'}입니다."
            )
        else:
            brief = (
                f"{month_day} {up_to_slot:02d}시 기준, 약물 관련 신고는 평시 수준입니다. "
                f"이상징후가 감지된 지역은 없습니다."
            )
        st.info(brief)
        st.caption("예측·탐지 결과만으로 생성 · 입력값에 없는 내용은 작성하지 않음")

    with side_col:
        with st.container(border=True):
            _title("시도별 실시간 위험도 지도")
            # 색상만으로 4단계(관심/주의/경계/심각)를 다 구분하면 채도 차이가 작아
            # 가독성이 떨어졌다 — "0건(비활동)/신고 있음/이상징후" 3단계로 단순화해
            # 색 대비를 뚜렷하게 준다. 관심·주의는 "신고 있음"으로, 경계·심각은
            # "이상징후"로 묶고, 실제 누적이 0인 지역은 별도로 회색 처리한다.
            # 색은 임의 hex 대신 앱 디자인 시스템의 기존 팔레트(theme.STATUS)를 그대로
            # 재사용해 나머지 화면과 톤이 어긋나지 않도록 한다.
            MAP_TIER_COLOR = {"0건": "#AEB4C2", "신고 있음": theme.STATUS["warning"], "이상징후": theme.STATUS["critical"]}
            NAVY_OUTLINE = "#12285A"
            map_df = snapshot.copy()
            map_df["lat"] = map_df["region"].map(lambda r: dl.REGION_COORDS[r][0])
            map_df["lon"] = map_df["region"].map(lambda r: dl.REGION_COORDS[r][1])
            geojson = dl.load_province_geojson()

            def _map_tier(row):
                if row["actual_so_far"] == 0:
                    return "0건"
                if row["risk"] in ("경계", "심각"):
                    return "이상징후"
                return "신고 있음"

            map_df["map_tier"] = map_df.apply(_map_tier, axis=1)

            # 점 마커 대신 시도 영역 자체를 위험도 색으로 채운다(코로플레스) — 지역별
            # 경계가 실제 면적으로 보여 한눈에 들어오도록. 시도명 텍스트는 그 위에 겹쳐 표시.
            fig_map = go.Figure()
            for tier in ["0건", "신고 있음", "이상징후"]:
                level_df = map_df[map_df["map_tier"] == tier]
                if level_df.empty:
                    continue
                fig_map.add_trace(go.Choroplethmapbox(
                    geojson=geojson,
                    featureidkey="properties.name",
                    locations=level_df["region"],
                    z=[1] * len(level_df),
                    colorscale=[[0, MAP_TIER_COLOR[tier]], [1, MAP_TIER_COLOR[tier]]],
                    showscale=False,
                    marker=dict(opacity=0.85, line=dict(color=NAVY_OUTLINE, width=1)),
                    name=tier,
                    text=[
                        f"{r}<br>실제 누적 {c}건<br>평시 대비 {ratio:.1f}배<br>위험도 {risk}"
                        for r, c, ratio, risk in zip(
                            level_df["region_short"], level_df["actual_so_far"],
                            level_df["ratio_vs_baseline"], level_df["risk"],
                        )
                    ],
                    hoverinfo="text",
                ))
                fig_map.add_trace(go.Scattermapbox(
                    lat=level_df["lat"], lon=level_df["lon"],
                    mode="text",
                    text=[f"{r} {c}" for r, c in zip(level_df["region_short"], level_df["actual_so_far"])],
                    # Mapbox GL 텍스트는 페이지 CSS 폰트가 아니라 지도 스타일이 제공하는
                    # 글리프 서버 폰트만 쓴다 — family를 안 주면 기본값이 한글을 이상하게
                    # 렌더링해서, CARTO 글리프 서버가 실제로 제공하는 한글 고딕(나눔바른고딕)
                    # 폰트스택을 명시한다.
                    textfont=dict(size=10, color=NAVY_OUTLINE, family="Open Sans Regular, NanumBarunGothic Regular"),
                    showlegend=False,
                    hoverinfo="skip",
                ))
            fig_map.update_layout(
                # carto-positron 기본 스타일은 지도 자체 지명 라벨(평양·원산·남포 등 북한
                # 지명, 잘린 영문 도시명)이 우리가 그리는 시도명·건수 텍스트와 겹쳐서
                # 가독성이 떨어졌다 — CARTO의 무료·토큰 불필요 "라벨 없음" 스타일로 교체해
                # 배경 지도에는 지명 없이 경계·색상만 남기고, 라벨은 우리 마커 텍스트만 보이게 한다.
                mapbox=dict(
                    style="https://basemaps.cartocdn.com/gl/positron-nolabels-gl-style/style.json",
                    center=dict(lat=36.4, lon=127.9), zoom=5.4,
                ),
                paper_bgcolor=theme.CARD_BG,
                margin=dict(l=0, r=0, t=0, b=0),
                height=460,
                showlegend=False,
            )
            # Choroplethmapbox는 Plotly 기본 범례에서 색상 견본이 제대로 안 나오는
            # 경우가 있어(showscale=False와 결합 시 특히), 직접 만든 HTML 범례를 쓴다.
            legend_html = "".join(
                f'<span style="display:inline-flex;align-items:center;gap:.3rem;margin-right:1rem;">'
                f'<span style="width:10px;height:10px;border-radius:50%;background:{color};'
                f'display:inline-block;border:1px solid {NAVY_OUTLINE}55;"></span>'
                f'<span style="font-size:.78rem;color:{theme.TEXT_SECONDARY};">{tier}</span></span>'
                for tier, color in MAP_TIER_COLOR.items()
            )
            st.markdown(f'<div style="margin-bottom:.4rem;">{legend_html}</div>', unsafe_allow_html=True)
            st.plotly_chart(fig_map, use_container_width=True, config={"displayModeBar": False})
            st.markdown(
                '<div class="muted" style="margin-top:.3rem;font-size:.72rem;">영역 색상=위험도 · 숫자=실제 누적</div>',
                unsafe_allow_html=True,
            )

        with st.container(border=True):
            if len(alert_regions):
                top = alert_regions.iloc[0]
                badge_label = f"이상징후 · {top['risk']}"
                st.markdown(theme.status_badge(top["risk"], badge_label), unsafe_allow_html=True)
                # 배수(3.2배)를 맨 앞에 크게 보여주면, 원래 발생이 드문 지역에서는
                # 건수 1~2개 차이만으로도 배수가 크게 튀어 과장돼 보인다 — 실제 건수를
                # 먼저 보여주고 배수는 괄호로 보조정보만 남긴다.
                st.markdown(f"**{top['region_short']} · 실제 {int(top['actual_so_far'])}건** (평시 대비 {top['ratio_vs_baseline']:.1f}배)")
                st.caption(
                    f"평소 이 시간대 평균 {top['predicted_so_far']:.1f}건 · "
                    "발생 건수가 적은 지역일수록 배수는 민감하게 움직입니다"
                )
            else:
                st.markdown(theme.status_badge("관심", "이상징후 없음"), unsafe_allow_html=True)
                st.caption("모든 지역이 평시 대비 1.5배 미만입니다.")
