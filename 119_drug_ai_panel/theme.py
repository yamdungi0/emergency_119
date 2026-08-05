from __future__ import annotations

import streamlit as st

NAVY = "#082e69"
BLUE = "#1666d9"
TEAL = "#029c9a"
RED = "#ef3d43"
ORANGE = "#ef7d1a"
BORDER = "#cad7e9"
TEXT = "#12284a"
MUTED = "#73829b"

STATUS = {"good": "#16b883", "warning": ORANGE, "critical": RED}

NAV_ITEMS = [
    ("▦", "상황판"),
    ("◫", "정책분석"),
    ("AI", "AI 보조"),
    ("☑", "대응카드"),
    ("✚", "병원연계"),
]

CSS = """
<style>
:root {
  --navy: #082e69;
  --blue: #1666d9;
  --teal: #029c9a;
  --teal-soft: #effafa;
  --red: #ef3d43;
  --orange: #ef7d1a;
  --border: #cad7e9;
  --surface: #f7f9fc;
  --text: #12284a;
}
.stApp { background: white; color: var(--text); }
[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #0c3977 0%, #06275a 100%);
}
[data-testid="stSidebar"] * { color: white; }
.block-container { padding-top: 1.1rem; padding-bottom: 2rem; max-width: 1500px; }

.topbar {
  display:flex; align-items:center; justify-content:space-between;
  border-bottom:1px solid var(--border); padding:0.2rem 0 0.8rem 0; margin-bottom:1rem;
}
.brand { font-size:1.55rem; font-weight:800; color:#0a3470; }
.brand .em { color:#e63237; margin-right:.4rem; }
.title { font-size:1.55rem; font-weight:800; margin-left:1rem; }
.pill {
  border:1px solid var(--teal); color:#018e8a; border-radius:10px;
  padding:.5rem .9rem; background:#f5ffff; font-weight:700;
}
.small-muted { color:#73829b; font-size:.83rem; }

.panel {
  border:1px solid var(--border); border-radius:14px; padding:1rem;
  background:white; box-shadow:0 1px 3px rgba(12,49,104,.05);
}
.ai-panel {
  border:2px solid var(--teal); border-radius:15px; padding:1rem;
  background:linear-gradient(180deg, #f3ffff 0%, #ffffff 25%);
}
.section-title {font-size:1.25rem; font-weight:800; color:#15345f; margin-bottom:.65rem;}
.ai-title {font-size:1.25rem; font-weight:800; color:#008e8a; margin-bottom:.65rem;}
.card {
  border:1px solid var(--border); border-radius:11px; padding:.75rem .85rem;
  min-height:84px; background:white;
}
.card-label {font-size:.78rem; color:#6b7d99; margin-bottom:.35rem;}
.card-value {font-size:1.05rem; font-weight:800; color:#1167d8;}
.card-teal .card-value {color:#008d89;}
.card-orange .card-value {color:#ef6d00;}
.card-red .card-value {color:#e5353b;}
.warning-box {
  border:1px solid #f2c7c9; background:#fff8f8; border-radius:12px; padding:.8rem;
}
.warning-title {color:#e5333a; font-size:1.1rem; font-weight:800; margin-bottom:.45rem;}
.warning-item {padding:.34rem 0; font-weight:650;}
.mapping-box {
  border:1px solid var(--border); background:#fff; border-radius:12px; padding:.8rem;
}
.map-row {display:flex; justify-content:space-between; padding:.33rem 0; border-bottom:1px solid #edf1f7;}
.map-row:last-child {border-bottom:none;}
.map-name {color:#687997;}
.map-value {color:#159654; font-weight:750;}
.record-box {background:#f7f9fc; border:1px solid var(--border); border-radius:11px; padding:.8rem; margin-bottom:.75rem;}
.record-head {font-weight:800; margin-bottom:.55rem;}
.metric-row {display:grid; grid-template-columns:repeat(5, 1fr); gap:.5rem;}
.metric {padding:.55rem; border-right:1px solid #dae3ef;}
.metric:last-child {border-right:0;}
.metric-label {font-size:.76rem; color:#77859c;}
.metric-value {font-weight:800; margin-top:.22rem;}
.risk {color:#ef3d43;}
.status-ok {color:#16b883; font-weight:800;}
.badge {display:inline-block; padding:.28rem .7rem; border-radius:999px; font-size:.78rem; font-weight:800; color:#fff;}
.badge-good {background:#16b883;}
.badge-warning {background:#ef7d1a;}
.badge-critical {background:#ef3d43;}
div[data-testid="stButton"] button {
  border-radius:9px; min-height:3rem; font-weight:800;
}
button[kind="primary"] { background:#078f8e !important; border-color:#078f8e !important; }
hr {border-color:#e4eaf3;}
</style>
"""


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def status_badge(kind: str, label: str) -> str:
    cls = {"good": "badge-good", "warning": "badge-warning", "critical": "badge-critical"}.get(kind, "badge-good")
    return f'<span class="badge {cls}">{label}</span>'


def render_sidebar(active_label: str) -> None:
    import datetime

    st.sidebar.markdown("## 119 약물안전")
    st.sidebar.caption("e-Triage 연계형 AI 의사결정 지원")
    st.sidebar.markdown("---")
    for icon, name in NAV_ITEMS:
        if name == active_label:
            st.sidebar.markdown(
                f"<div style='background:#1e6cdd;padding:13px;border-radius:10px;"
                f"font-size:18px;font-weight:800;margin:8px 0'>{icon}&nbsp;&nbsp;{name}</div>",
                unsafe_allow_html=True,
            )
        else:
            st.sidebar.markdown(
                f"<div style='padding:12px 6px;font-size:17px;margin:5px 0'>{icon}&nbsp;&nbsp;{name}</div>",
                unsafe_allow_html=True,
            )
    st.sidebar.markdown("<div style='height:80px'></div>", unsafe_allow_html=True)
    st.sidebar.markdown(
        "<div style='border:1px solid #4f80bd;border-radius:10px;padding:12px;'>"
        "<b>e-Triage 연계 상태</b><br><span style='color:#45e0b2'>● 정상 연동 중</span><br>"
        f"<span style='font-size:12px'>최근 연동 {datetime.datetime.now().strftime('%H:%M:%S')}</span></div>",
        unsafe_allow_html=True,
    )
