"""119 약물안전 코파일럿 — 공유 디자인 토큰과 CSS.

webapp(원래 상황판 프로젝트)의 theme.py를 그대로 기준으로 삼는다 — 이 앱을
그쪽과 시각적으로 통일하기 위해 팔레트·간격 값을 다시 유도하지 않고 그대로
옮겨왔다. Navy + Red 중심, 관심·주의·경계·심각 4단계 경보색, Noto Sans KR.
"""

from __future__ import annotations

PAGE_BG = "#F5F5F6"
SIDEBAR_BG = "#1E3A78"
CARD_BG = "#FDFDFD"
CARD_BORDER = "#DCDCDD"
TEXT_PRIMARY = "#242526"
TEXT_SECONDARY = "#818285"
TEXT_MUTED = "#9A9B9E"

NAVY = "#1E3A78"
RED = "#C4402B"
LABEL_NAVY = "#162E67"

STATUS = {
    "good": "#3B6FB0",
    "warning": "#E5C24A",
    "serious": "#D97B34",
    "critical": "#C4402B",
}
ALERT_LABELS = ["관심", "주의", "경계", "심각"]

CATEGORICAL = {
    "blue": NAVY,
    "aqua": "#2E7A6C",
    "orange": "#9C6B2E",
    "yellow": "#7A8C3E",
    "magenta": "#7A4B6B",
    "violet": "#5B6472",
}

# 구버전(teammate 원본) 코드가 참조하는 짧은 별칭 — 페이지마다 다시 고치지 않도록 유지.
BLUE = NAVY
BORDER = CARD_BORDER
MUTED = TEXT_MUTED

NAV_ITEMS = [
    ("dashboard", "01", "상황판"),
    ("policy", "02", "정책분석"),
    ("intake", "03", "AI 보조패널"),
    ("card", "04", "대응카드"),
    ("hospital", "05", "병원연계"),
    ("admin", "06", "관리자"),
]

FONT_STACK = "'Noto Sans KR', -apple-system, 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif"


def logo_svg(width: int = 44, height: int = 34, on_dark: bool = True) -> str:
    body_fill = "#ffffff" if on_dark else NAVY
    parts = [
        f'<svg viewBox="0 0 170 130" width="{width}" height="{height}">',
        "<defs>",
        '<clipPath id="dc-cap1"><rect x="10" y="15" width="24" height="88" rx="12" ry="12"/></clipPath>',
        '<clipPath id="dc-cap2"><rect x="50" y="15" width="24" height="88" rx="12" ry="12"/></clipPath>',
        '<clipPath id="dc-circ"><circle cx="118" cy="46" r="31"/></clipPath>',
        "</defs>",
        f'<rect x="10" y="15" width="24" height="88" rx="12" ry="12" fill="{body_fill}"/>',
        f'<rect x="10" y="15" width="24" height="44" fill="{RED}" clip-path="url(#dc-cap1)"/>',
        f'<rect x="50" y="15" width="24" height="88" rx="12" ry="12" fill="{body_fill}"/>',
        f'<rect x="50" y="15" width="24" height="44" fill="{RED}" clip-path="url(#dc-cap2)"/>',
        f'<rect x="129" y="60" width="15" height="52" rx="7.5" fill="{body_fill}" transform="rotate(28 136.5 86)"/>',
        f'<circle cx="118" cy="46" r="31" fill="{body_fill}"/>',
        f'<rect x="87" y="15" width="62" height="31" fill="{RED}" clip-path="url(#dc-circ)"/>',
        "</svg>",
    ]
    return "".join(parts)


KPI_ICON_GLYPHS = {
    "list": '<line x1="7" y1="8" x2="17" y2="8"/><line x1="7" y1="12" x2="17" y2="12"/><line x1="7" y1="16" x2="13" y2="16"/>',
    "clock": '<circle cx="12" cy="12" r="7"/><line x1="12" y1="12" x2="12" y2="8"/><line x1="12" y1="12" x2="15" y2="13"/>',
    "pie": '<circle cx="12" cy="12" r="7"/><path d="M12 12 L12 5 A7 7 0 0 1 18.5 15.5 Z" fill="#ffffff" stroke="none"/>',
    "alert": '<path d="M12 5 L20 19 L4 19 Z"/><line x1="12" y1="10.5" x2="12" y2="14"/><circle cx="12" cy="16.5" r="0.6" fill="#ffffff" stroke="none"/>',
    "map": '<path d="M9 4 L4 6 L4 20 L9 18 L15 20 L20 18 L20 4 L15 6 L9 4Z"/><line x1="9" y1="4" x2="9" y2="18"/><line x1="15" y1="6" x2="15" y2="20"/>',
    "check": '<path d="M5 13 L10 18 L19 7"/>',
    "hospital": '<rect x="5" y="7" width="14" height="13" rx="1"/><line x1="12" y1="10" x2="12" y2="16"/><line x1="9" y1="13" x2="15" y2="13"/><path d="M9 7 L9 4 L15 4 L15 7"/>',
    "gauge": '<path d="M4 16 A8 8 0 0 1 20 16"/><line x1="12" y1="16" x2="16" y2="11"/><circle cx="12" cy="16" r="1" fill="#ffffff" stroke="none"/>',
}


def kpi_icon_svg(kind: str, bg_color: str, size: int = 34) -> str:
    glyph = KPI_ICON_GLYPHS.get(kind, KPI_ICON_GLYPHS["list"])
    parts = [
        f'<svg viewBox="0 0 24 24" width="{size}" height="{size}">',
        f'<circle cx="12" cy="12" r="12" fill="{bg_color}"/>',
        f'<g fill="none" stroke="#ffffff" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">{glyph}</g>',
        "</svg>",
    ]
    return "".join(parts)


def inject_css() -> None:
    import streamlit as st

    st.markdown(
        """
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700;900&display=swap" rel="stylesheet">
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        f"""
        <style>
        .stApp {{
            background: {PAGE_BG};
            color: {TEXT_PRIMARY};
        }}
        html, body, [class*="css"] {{
            font-family: {FONT_STACK};
        }}
        section[data-testid="stSidebar"] {{
            background: {SIDEBAR_BG};
            border-right: none;
        }}
        section[data-testid="stSidebar"] * {{
            color: #ffffff;
        }}
        section[data-testid="stSidebar"] .muted, section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {{
            color: rgba(255,255,255,0.62) !important;
        }}
        [data-testid="stSidebarNav"] a {{
            border-radius: 8px;
            margin: 2px 8px;
        }}
        [data-testid="stSidebarNav"] a:hover {{
            background: rgba(255,255,255,0.10);
        }}
        [data-testid="stSidebarNav"] a[aria-current="page"] {{
            background: rgba(255,255,255,0.16);
            font-weight: 700;
        }}
        /* Streamlit이 자동 생성하는 페이지 목록(stSidebarNav)은 항상 사이드바
           맨 위, 로고보다 먼저 렌더링된다 — DOM 순서를 바꿀 수 없으니 flex
           order로 시각 순서만 "로고 → 목차 → 하단상태"로 뒤집는다. */
        section[data-testid="stSidebar"] > div:first-child {{
            display: flex;
            flex-direction: column;
        }}
        [data-testid="stSidebarUserContent"] {{ order: 1; }}
        [data-testid="stSidebarNav"] {{ order: 2; }}
        .block-container {{
            padding-top: 2.2rem;
            padding-bottom: 1.2rem;
            padding-left: 1.3rem;
            padding-right: 1.3rem;
            max-width: 1800px;
        }}
        div[data-testid="stVerticalBlock"] {{
            gap: 0.6rem;
        }}
        div[data-testid="stHorizontalBlock"] {{
            gap: 0.5rem !important;
        }}
        h1, h2, h3, h4, p, span, label, div {{
            color: {TEXT_PRIMARY};
            font-family: {FONT_STACK};
        }}
        .muted, .small-muted {{ color: {TEXT_SECONDARY}; font-size: 0.85rem; }}
        .topbar {{
            display: flex;
            justify-content: space-between;
            align-items: baseline;
            border-bottom: 1px solid {CARD_BORDER};
            padding-bottom: 0.6rem;
            margin-bottom: 0.6rem;
        }}
        .topbar-title, .title {{ font-size: 1.6rem; font-weight: 900; letter-spacing: -0.01em; }}
        .topbar-sub {{ color: {TEXT_SECONDARY}; font-size: 0.88rem; margin-top: 0.2rem; }}
        .topbar-time {{ color: {TEXT_SECONDARY}; font-size: 0.85rem; font-family: ui-monospace, monospace; }}
        .brand {{ font-size:1.55rem; font-weight:800; color:{NAVY}; }}
        .brand .em {{ color:{RED}; margin-right:.4rem; }}
        .pill {{
            border:1px solid {NAVY}; color:{NAVY}; border-radius:10px;
            padding:.4rem .8rem; background:#eef1f8; font-weight:700; font-size:.82rem;
        }}

        .panel, .ai-panel {{
            border:1px solid {CARD_BORDER}; border-radius:12px; padding:1rem;
            background:{CARD_BG}; margin-bottom:.65rem;
        }}
        .card {{
            background: {CARD_BG};
            border: 1px solid {CARD_BORDER};
            border-radius: 8px;
            padding: 0.85rem 1.05rem;
            margin-bottom: 0.65rem;
        }}
        div[data-testid="stVerticalBlockBorderWrapper"] > div {{
            gap: 0.5rem;
        }}
        .kpi-header {{ display: flex; align-items: center; gap: 0.5rem; }}
        .kpi-label, .card-label {{ color: {LABEL_NAVY}; font-size: 0.78rem; font-weight: 700; margin-bottom: .3rem;}}
        .kpi-value, .card-value {{ font-size: 1.4rem; font-weight: 900; margin-top: 0.15rem; color: {TEXT_PRIMARY}; }}
        .kpi-delta {{ font-size: 0.78rem; margin-top: 0.2rem; }}
        .section-title, .ai-title {{ color: {LABEL_NAVY}; font-weight: 700; margin-bottom: 0.45rem; font-size: 1.05rem;}}
        div[data-testid="stDateInput"] label p {{
            color: {LABEL_NAVY} !important;
            font-weight: 700 !important;
        }}

        .badge {{
            display: inline-block;
            padding: 0.2rem 0.7rem;
            border-radius: 999px;
            font-size: 0.76rem;
            font-weight: 700;
            color: #ffffff;
        }}
        .badge-good {{ background: {STATUS['good']}; }}
        .badge-warning {{ background: {STATUS['warning']}; color: #4a3c00; }}
        .badge-serious {{ background: {STATUS['serious']}; }}
        .badge-critical {{ background: {STATUS['critical']}; }}

        .record-box {{background: #F5F5F6; border:1px solid {CARD_BORDER}; border-radius:10px; padding:.8rem; margin-bottom:.6rem;}}
        .record-head {{font-weight:800; margin-bottom:.5rem; color:{LABEL_NAVY};}}
        .metric-row {{display:grid; grid-template-columns:repeat(5, 1fr); gap:.5rem;}}
        .metric {{padding:.4rem .55rem; border-right:1px solid {CARD_BORDER};}}
        .metric:last-child {{border-right:0;}}
        .metric-label {{font-size:.74rem; color:{TEXT_SECONDARY};}}
        .metric-value {{font-weight:800; margin-top:.2rem; color:{TEXT_PRIMARY};}}
        .risk {{color:{RED};}}
        .warning-box {{border:1px solid #ecb9bb; background:#fdf4f4; border-radius:10px; padding:.8rem;}}
        .warning-title {{color:{RED}; font-size:1.02rem; font-weight:800; margin-bottom:.4rem;}}
        .warning-item {{padding:.3rem 0; font-weight:600;}}
        .mapping-box {{border:1px solid {CARD_BORDER}; background:{CARD_BG}; border-radius:10px; padding:.8rem; margin-bottom:.5rem;}}
        .map-row {{display:flex; justify-content:space-between; padding:.4rem 0; border-bottom:1px solid {PAGE_BG};}}
        .map-row:last-child {{border-bottom:none;}}
        .map-name {{color:{TEXT_SECONDARY};}}
        .map-value {{color:{NAVY}; font-weight:750;}}

        .stButton>button {{
            border-radius: 6px;
            border: 1px solid {CARD_BORDER};
            background: {CARD_BG};
            color: {TEXT_PRIMARY};
            font-family: {FONT_STACK};
            font-weight: 700;
        }}
        .stButton>button:hover {{
            border-color: {NAVY};
            color: {NAVY};
        }}
        button[kind="primary"] {{ background:{NAVY} !important; border-color:{NAVY} !important; color:#fff !important;}}
        div[data-testid="stMetric"] {{
            background: {CARD_BG};
            border: 1px solid {CARD_BORDER};
            border-radius: 8px;
            padding: 0.7rem 0.9rem;
        }}
        div[data-testid="stDateInput"] div[data-baseweb="base-input"] {{
            position: relative;
        }}
        div[data-testid="stDateInput"] div[data-baseweb="base-input"]::after {{
            content: "▾";
            position: absolute;
            right: 14px;
            top: 50%;
            transform: translateY(-50%);
            pointer-events: none;
            font-size: 13px;
            color: {TEXT_SECONDARY};
        }}
        input[data-testid="stDateInputField"] {{
            padding-right: 2.4rem !important;
            cursor: pointer;
        }}
        div[data-baseweb="calendar"] div[role="gridcell"][aria-label^="Selected"] {{
            color: #ffffff !important;
        }}
        div[data-baseweb="calendar"] div[role="gridcell"][aria-label^="Selected"] div {{
            color: #ffffff !important;
        }}
        hr {{border-color:{CARD_BORDER};}}
        </style>
        """,
        unsafe_allow_html=True,
    )


def status_badge(level: str, label: str) -> str:
    cls = {
        "관심": "good", "주의": "warning", "경계": "serious", "심각": "critical",
        "good": "good", "warning": "warning", "critical": "critical",
    }.get(level, "good")
    return f'<span class="badge badge-{cls}">{label}</span>'


def plotly_layout_defaults() -> dict:
    return dict(
        paper_bgcolor=CARD_BG,
        plot_bgcolor=CARD_BG,
        font=dict(color=TEXT_PRIMARY, size=12, family=FONT_STACK),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        margin=dict(l=10, r=10, t=30, b=10),
        xaxis=dict(gridcolor=CARD_BORDER, zerolinecolor=CARD_BORDER),
        yaxis=dict(gridcolor=CARD_BORDER, zerolinecolor=CARD_BORDER),
    )


def render_sidebar(active_label: str | None = None) -> None:
    """로고 + 하단 연동상태 박스. 실제 화면 이동은 Streamlit의 pages/ 자동
    네비게이션(사이드바 최상단에 프레임워크가 직접 그려줌)이 담당한다."""
    import datetime

    import streamlit as st

    sidebar_logo_html = (
        '<div style="display:flex;align-items:center;gap:.6rem;margin:.2rem 0 .8rem;">'
        + logo_svg(width=36, height=28, on_dark=True)
        + '<div style="line-height:1.2;">'
        + '<div style="font-weight:900;font-size:.95rem;">119 약물안전</div>'
        + '<div style="font-weight:500;font-size:.7rem;color:rgba(255,255,255,.65);">코파일럿</div>'
        + "</div></div>"
    )
    st.sidebar.markdown(sidebar_logo_html, unsafe_allow_html=True)
    st.sidebar.markdown(
        "<div style='border:1px solid rgba(255,255,255,.25);border-radius:10px;padding:10px;font-size:.78rem;'>"
        "<b>e-Triage 연계 상태</b><br><span style='color:#6be0b0'>● 정상 연동 중</span><br>"
        f"<span style='opacity:.7'>최근 연동 {datetime.datetime.now().strftime('%H:%M:%S')}</span></div>",
        unsafe_allow_html=True,
    )
