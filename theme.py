"""Shared color tokens and CSS for the 119 약물안전 상황판 demo.

Dark surfaces + status/categorical hues follow the validated palette in the
dataviz skill (references/palette.md) — status and categorical steps are used
unmodified; only the page background is nudged toward navy to match the
approved screen mockups (소방청/화면이미지 초안).
"""

from __future__ import annotations

PAGE_BG = "#0b0f19"
SIDEBAR_BG = "#0a0e17"
CARD_BG = "#121a2b"
CARD_BORDER = "#232c42"
TEXT_PRIMARY = "#f5f7fa"
TEXT_SECONDARY = "#8b93a7"
TEXT_MUTED = "#5b6478"

# Status palette — fixed, never repurposed as a categorical series.
STATUS = {
    "good": "#0ca30c",       # 정상
    "warning": "#fab219",    # 주의
    "serious": "#ec835a",    # 경계
    "critical": "#d03b3b",   # 심각
}

# Categorical palette — fixed hue order (dataviz skill, dark-mode steps).
CATEGORICAL = {
    "blue": "#3987e5",
    "orange": "#d95926",
    "aqua": "#199e70",
    "yellow": "#c98500",
    "magenta": "#d55181",
    "violet": "#9085e9",
}

NAV_ITEMS = [
    ("dashboard", "01", "상황판"),
    ("intake", "02", "접수"),
    ("card", "03", "상담카드"),
    ("hospital", "04", "기관연계"),
    ("transport", "05", "이송결정"),
    ("admin", "06", "검증"),
]


def inject_css() -> None:
    import streamlit as st

    st.markdown(
        f"""
        <style>
        .stApp {{
            background: {PAGE_BG};
            color: {TEXT_PRIMARY};
        }}
        section[data-testid="stSidebar"] {{
            background: {SIDEBAR_BG};
            border-right: 1px solid {CARD_BORDER};
        }}
        .block-container {{
            padding-top: 4.5rem;
            padding-bottom: 3rem;
            max-width: 1400px;
        }}
        h1, h2, h3, h4, p, span, label, div {{
            color: {TEXT_PRIMARY};
        }}
        .muted {{ color: {TEXT_SECONDARY}; font-size: 0.85rem; }}
        .topbar {{
            display: flex;
            justify-content: space-between;
            align-items: baseline;
            border-bottom: 1px solid {CARD_BORDER};
            padding-bottom: 0.9rem;
            margin-bottom: 1.1rem;
        }}
        .topbar-title {{ font-size: 1.5rem; font-weight: 800; }}
        .topbar-sub {{ color: {TEXT_SECONDARY}; font-size: 0.88rem; margin-top: 0.15rem; }}
        .topbar-time {{ color: {TEXT_SECONDARY}; font-size: 0.85rem; font-family: monospace; }}

        .card {{
            background: {CARD_BG};
            border: 1px solid {CARD_BORDER};
            border-radius: 14px;
            padding: 1.05rem 1.2rem;
            margin-bottom: 1rem;
        }}
        .kpi-label {{ color: {TEXT_SECONDARY}; font-size: 0.82rem; }}
        .kpi-value {{ font-size: 1.9rem; font-weight: 800; margin-top: 0.15rem; }}
        .kpi-delta {{ font-size: 0.82rem; margin-top: 0.2rem; }}

        .badge {{
            display: inline-block;
            padding: 0.15rem 0.6rem;
            border-radius: 999px;
            font-size: 0.78rem;
            font-weight: 700;
            border: 1px solid transparent;
        }}
        .badge-good {{ color: {STATUS['good']}; background: rgba(12,163,12,0.14); border-color: rgba(12,163,12,0.4);}}
        .badge-warning {{ color: {STATUS['warning']}; background: rgba(250,178,25,0.14); border-color: rgba(250,178,25,0.4);}}
        .badge-serious {{ color: {STATUS['serious']}; background: rgba(236,131,90,0.14); border-color: rgba(236,131,90,0.4);}}
        .badge-critical {{ color: {STATUS['critical']}; background: rgba(208,59,59,0.14); border-color: rgba(208,59,59,0.4);}}

        .region-tile {{
            border-radius: 10px;
            padding: 0.55rem 0.4rem;
            text-align: center;
            border: 1px solid {CARD_BORDER};
        }}
        .region-name {{ font-size: 0.72rem; color: {TEXT_SECONDARY}; }}
        .region-count {{ font-size: 1.15rem; font-weight: 800; }}

        .stButton>button {{
            border-radius: 10px;
            border: 1px solid {CARD_BORDER};
            background: {CARD_BG};
            color: {TEXT_PRIMARY};
        }}
        .stButton>button:hover {{
            border-color: {CATEGORICAL['blue']};
            color: {CATEGORICAL['blue']};
        }}
        div[data-testid="stMetric"] {{
            background: {CARD_BG};
            border: 1px solid {CARD_BORDER};
            border-radius: 12px;
            padding: 0.7rem 0.9rem;
        }}
        .nav-btn-active > button {{
            border-color: {CATEGORICAL['blue']} !important;
            color: {CATEGORICAL['blue']} !important;
            background: rgba(57,135,229,0.12) !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def status_badge(level: str, label: str) -> str:
    cls = {"정상": "good", "주의": "warning", "경계": "serious", "심각": "critical"}.get(level, "good")
    return f'<span class="badge badge-{cls}">{label}</span>'


def plotly_layout_defaults() -> dict:
    return dict(
        paper_bgcolor=CARD_BG,
        plot_bgcolor=CARD_BG,
        font=dict(color=TEXT_PRIMARY, size=12),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        margin=dict(l=10, r=10, t=30, b=10),
        xaxis=dict(gridcolor=CARD_BORDER, zerolinecolor=CARD_BORDER),
        yaxis=dict(gridcolor=CARD_BORDER, zerolinecolor=CARD_BORDER),
    )
