"""Shared color tokens and CSS for the 119 약물안전 상황판.

Palette, type scale and the capsule "119" mark are taken as-is from the design
handoff (design_handoff_fire_chemical_color_system/) — Navy + Red core, a
4-step 관심-주의-경계-심각 alert scale, Noto Sans KR. Values are not
re-derived; only mapped onto this app's components.
"""

from __future__ import annotations

PAGE_BG = "#F5F5F6"
SIDEBAR_BG = "#1E3A78"       # Navy — handoff's top-nav color, used here as the sidebar
CARD_BG = "#FDFDFD"
CARD_BORDER = "#DCDCDD"
TEXT_PRIMARY = "#242526"
TEXT_SECONDARY = "#818285"
TEXT_MUTED = "#9A9B9E"

NAVY = "#1E3A78"
RED = "#C4402B"
LABEL_NAVY = "#162E67"  # 01 상황판 섹션 제목·KPI 라벨 전용 지정색

# Status / alert palette — fixed, reserved for severity only (handoff: "Red는
# 위험·경보 전용, 일반 UI엔 미사용"). Keys kept stable for the rest of the app;
# labels are 관심·주의·경계·심각 (재난 예경보 4단계 관례).
STATUS = {
    "good": "#3B6FB0",       # 관심 (LV.1)
    "warning": "#E5C24A",    # 주의 (LV.2)
    "serious": "#D97B34",    # 경계 (LV.3)
    "critical": "#C4402B",   # 심각 (LV.4) = Red
}
ALERT_LABELS = ["관심", "주의", "경계", "심각"]

# Chart / UI-accent palette — deliberately distinct from the 4 alert hues so a
# category color is never mistaken for a severity color.
CATEGORICAL = {
    "blue": NAVY,        # brand primary — nav, links, primary series
    "aqua": "#2E7A6C",   # teal
    "orange": "#9C6B2E", # bronze
    "yellow": "#7A8C3E", # olive
    "magenta": "#7A4B6B",# plum
    "violet": "#5B6472", # slate
}

NAV_ITEMS = [
    ("dashboard", "01", "상황판"),
    ("intake", "02", "접수"),
    ("card", "03", "상담카드"),
    ("hospital", "04", "기관연계"),
    ("transport", "05", "이송결정"),
    ("admin", "06", "검증"),
]

FONT_STACK = "'Noto Sans KR', -apple-system, 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif"


def logo_svg(width: int = 44, height: int = 34, on_dark: bool = True) -> str:
    """119 캡슐(알약) 심볼 — design_handoff의 좌표를 그대로 사용.

    단일 라인 문자열이어야 함: st.markdown은 4칸 이상 들여쓰기된 줄을 코드블록으로
    처리해 HTML을 그대로 텍스트로 출력해버리므로, 여러 줄 들여쓰기 SVG를 피한다.
    """
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
    # 단순 도형(선/원/사각형)만 사용 — 정교한 아이콘 폰트 없이도 안정적으로 그려진다.
    "list": '<line x1="7" y1="8" x2="17" y2="8"/><line x1="7" y1="12" x2="17" y2="12"/><line x1="7" y1="16" x2="13" y2="16"/>',
    "clock": '<circle cx="12" cy="12" r="7"/><line x1="12" y1="12" x2="12" y2="8"/><line x1="12" y1="12" x2="15" y2="13"/>',
    "pie": '<circle cx="12" cy="12" r="7"/><path d="M12 12 L12 5 A7 7 0 0 1 18.5 15.5 Z" fill="#ffffff" stroke="none"/>',
    "alert": '<path d="M12 5 L20 19 L4 19 Z"/><line x1="12" y1="10.5" x2="12" y2="14"/><circle cx="12" cy="16.5" r="0.6" fill="#ffffff" stroke="none"/>',
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
        .block-container {{
            padding-top: 3.0rem;
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
        .muted {{ color: {TEXT_SECONDARY}; font-size: 0.85rem; }}
        .topbar {{
            display: flex;
            justify-content: space-between;
            align-items: baseline;
            border-bottom: 1px solid {CARD_BORDER};
            padding-bottom: 0.6rem;
            margin-bottom: 0.6rem;
        }}
        .topbar-title {{ font-size: 1.6rem; font-weight: 900; letter-spacing: -0.01em; }}
        .topbar-sub {{ color: {TEXT_SECONDARY}; font-size: 0.88rem; margin-top: 0.2rem; }}
        .topbar-time {{ color: {TEXT_SECONDARY}; font-size: 0.85rem; font-family: ui-monospace, monospace; }}

        .card {{
            background: {CARD_BG};
            border: 1px solid {CARD_BORDER};
            border-radius: 8px;
            padding: 0.85rem 1.05rem;
            margin-bottom: 0.65rem;
        }}
        /* st.container(border=True) is used for cards — its own radius/border
           (auto-generated class, not reliably targetable) is close enough to
           .card as-is, so it's left unstyled here. */
        div[data-testid="stVerticalBlockBorderWrapper"] > div {{
            gap: 0.5rem;
        }}
        .kpi-header {{ display: flex; align-items: center; gap: 0.5rem; }}
        .kpi-label {{ color: {LABEL_NAVY}; font-size: 0.78rem; font-weight: 700; }}
        .kpi-value {{ font-size: 1.6rem; font-weight: 900; margin-top: 0.15rem; }}
        .kpi-delta {{ font-size: 0.78rem; margin-top: 0.2rem; }}
        .section-title {{ color: {LABEL_NAVY}; font-weight: 700; margin-bottom: 0.45rem; }}
        /* "기준 날짜" 입력 라벨 전용 — data-testid는 Streamlit 버전이 바뀌어도
           안정적인 접근성 훅이라 내부 클래스 해시보다 안전하다. */
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


        .stButton>button {{
            border-radius: 6px;
            border: 1px solid {CARD_BORDER};
            background: {CARD_BG};
            color: {TEXT_PRIMARY};
            font-family: {FONT_STACK};
        }}
        .stButton>button:hover {{
            border-color: {NAVY};
            color: {NAVY};
        }}
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
        /* 캘린더 팝업에서 선택된 날짜는 Navy 원(::after)이 뒤에 깔리는데 숫자 글자색이
           그대로 어두운 색이라 안 보였다 — 흰 글자로 덮어씀. aria-label은 BaseWeb
           datepicker가 항상 "Selected..."로 시작하게 채워주는 접근성 속성이라
           내부 클래스 해시보다 안정적인 훅이다. */
        div[data-baseweb="calendar"] div[role="gridcell"][aria-label^="Selected"] {{
            color: #ffffff !important;
        }}
        div[data-baseweb="calendar"] div[role="gridcell"][aria-label^="Selected"] div {{
            color: #ffffff !important;
        }}
        section[data-testid="stSidebar"] .stButton>button {{
            background: transparent;
            border: 1px solid rgba(255,255,255,0.18);
            color: rgba(255,255,255,0.88);
        }}
        section[data-testid="stSidebar"] .stButton>button:hover {{
            border-color: #ffffff;
            color: #ffffff;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def status_badge(level: str, label: str) -> str:
    cls = {"관심": "good", "주의": "warning", "경계": "serious", "심각": "critical"}.get(level, "good")
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
