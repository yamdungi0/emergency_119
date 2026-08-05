from __future__ import annotations

import sys
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import data_loader as dl
import theme

st.set_page_config(
    page_title="119 약물안전 코파일럿 | 관리자",
    page_icon="🚑",
    layout="wide",
    initial_sidebar_state="expanded",
)
theme.inject_css()
theme.render_sidebar("관리자")

st.markdown(
    '<div class="topbar"><div>'
    '<div class="topbar-title">관리자 · 모델 검증</div>'
    '<div class="topbar-sub">백테스트 성능과 데이터 품질</div>'
    "</div></div>",
    unsafe_allow_html=True,
)

metrics = dl.load_metrics()
fi = dl.load_feature_importance()
meta = dl.load_run_metadata()

row = metrics[(metrics["level"] == "national_aggregate") & (metrics["model"] == "LightGBM_Poisson")].iloc[0]
baseline = metrics[(metrics["level"] == "national_aggregate") & (metrics["model"] == "Historical_same_weekday_slot")].iloc[0]
wmape_improve = (baseline["WMAPE"] - row["WMAPE"]) / baseline["WMAPE"] * 100

k1, k2, k3, k4 = st.columns(4)
for col, label, value, sub in [
    (k1, "MAE · 전국 3시간 단위", f"{row['MAE']:.2f}", f"기준모델 대비 {(1 - row['MAE']/baseline['MAE'])*100:+.1f}%"),
    (k2, "WMAPE", f"{row['WMAPE']*100:.1f}%", f"기준모델 대비 {-wmape_improve:+.1f}%p"),
    (k3, "Poisson deviance", f"{row['Poisson_deviance']:.2f}", f"기준모델 {baseline['Poisson_deviance']:.2f}"),
    (k4, "모델", "LightGBM Poisson", f"best_iteration {meta['best_iteration']}"),
]:
    col.markdown(
        f'<div class="card"><div class="kpi-label">{label}</div>'
        f'<div class="kpi-value" style="font-size:1.5rem;">{value}</div>'
        f'<div class="kpi-delta muted">{sub}</div></div>',
        unsafe_allow_html=True,
    )

left, right = st.columns([1.3, 1], gap="large")

with left:
    with st.container(border=True):
        st.markdown("**기준모델 대비 성능 (WMAPE, 낮을수록 좋음)**")
        agg = metrics[metrics["level"] == "national_aggregate"].sort_values("WMAPE", ascending=False)
        colors = [theme.CATEGORICAL["aqua"] if m == "LightGBM_Poisson" else theme.TEXT_MUTED for m in agg["model"]]
        fig = go.Figure(go.Bar(
            x=agg["WMAPE"] * 100, y=agg["model"], orientation="h",
            marker_color=colors, text=[f"{v*100:.1f}%" for v in agg["WMAPE"]], textposition="outside",
        ))
        fig.update_layout(**theme.plotly_layout_defaults(), height=260, xaxis_title="WMAPE (%)")
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        st.caption(f"학습 {meta['train_period']} · 테스트 {meta['test_period']} · {meta['evaluation']}")

    with st.container(border=True):
        st.markdown("**2023 백테스트 — 월별 전국 실제 대 예측 합계**")
        pred = dl.load_predictions()
        monthly = pred.groupby(pred["time_block"].dt.month).agg(y=("y", "sum"), prediction=("prediction", "sum")).reset_index()
        monthly.columns = ["month", "실제", "예측"]
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(x=monthly["month"], y=monthly["실제"], name="실제", marker_color=theme.CATEGORICAL["blue"]))
        fig2.add_trace(go.Scatter(x=monthly["month"], y=monthly["예측"], name="예측", mode="lines+markers",
                                   line=dict(color=theme.CATEGORICAL["orange"], width=2)))
        fig2.update_layout(**theme.plotly_layout_defaults(), height=280, xaxis_title="월")
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

with right:
    with st.container(border=True):
        st.markdown("**SHAP 대용 — 특성 중요도 (gain)**")
        top_fi = fi.sort_values("importance_gain", ascending=True).tail(8)
        fig3 = go.Figure(go.Bar(
            x=top_fi["importance_gain"], y=top_fi["feature"], orientation="h",
            marker_color=theme.CATEGORICAL["violet"],
        ))
        fig3.update_layout(**theme.plotly_layout_defaults(), height=300)
        st.plotly_chart(fig3, use_container_width=True, config={"displayModeBar": False})
        st.caption("예측 증가 상위 요인: 최근 신고량 증가(rolling_mean) · 동일 시간대 과거 평균 · 지역")

    with st.container(border=True):
        st.markdown("**데이터 품질**")
        st.markdown(
            f'<div class="muted">중증도 값 결측률</div>'
            f'<div style="font-weight:800;color:{theme.STATUS["critical"]}">약 45.2%</div>'
            f'<div class="muted" style="margin-top:.5rem;">활력징후·이송결과 보유율</div>'
            f'<div style="font-weight:800;">0% · 미수집</div>',
            unsafe_allow_html=True,
        )
        st.caption("환자 중증도 예측 모델은 MVP에서 제외 — 예측 대상은 지역·시간대별 신고 발생량으로 한정합니다.")

    with st.container(border=True):
        st.markdown("**사용 특성 (전체 24개)**")
        st.code(", ".join(meta["features"]), language=None)

with st.container(border=True):
    st.markdown("**비교 기준모델 전체 결과표**")
    show = metrics.copy()
    show["WMAPE"] = (show["WMAPE"] * 100).round(1)
    show.columns = ["단위", "모델", "MAE", "WMAPE(%)", "Poisson deviance"]
    st.dataframe(show, hide_index=True, use_container_width=True)

st.markdown('<div class="panel" style="margin-top:.6rem;">', unsafe_allow_html=True)
st.markdown("**AI 보조패널 감사로그**")
try:
    import sqlite3

    conn = sqlite3.connect(dl.DATA_DIR / "audit.db")
    audit = None
    try:
        import pandas as pd

        audit = pd.read_sql_query(
            "SELECT id, created_at FROM case_audit ORDER BY created_at DESC LIMIT 20", conn
        )
    finally:
        conn.close()
    if audit is not None and not audit.empty:
        st.dataframe(audit, hide_index=True, use_container_width=True)
        st.caption("화면3 AI 보조패널에서 '확인 후 저장'을 누를 때마다 여기 기록됩니다(로컬 SQLite, 배포 환경에서는 재시작 시 초기화될 수 있음).")
    else:
        st.caption("아직 저장된 사건이 없습니다. 화면3에서 '확인 후 저장'을 눌러보세요.")
except Exception:
    st.caption("아직 저장된 사건이 없습니다. 화면3에서 '확인 후 저장'을 눌러보세요.")
st.markdown("</div>", unsafe_allow_html=True)
