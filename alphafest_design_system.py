"""AlphaFest Design System 1.0.

Componentes visuais reutilizáveis. Não contém regras de negócio.
"""
from __future__ import annotations

import html
import streamlit as st

COLORS = {
    "blue": "#0A67E8",
    "blue_dark": "#063B82",
    "blue_soft": "#EAF3FF",
    "pink": "#F03C9B",
    "white": "#FFFFFF",
    "surface": "#F5F8FC",
    "text": "#18324F",
    "muted": "#62758A",
    "border": "#DCE7F4",
    "success": "#1E9E62",
    "warning": "#D89B16",
    "danger": "#D9485F",
}


def inject_design_system() -> None:
    """Injeta o tema apenas na página que chamar esta função."""
    st.markdown(
        f"""
        <style>
        :root {{
            --af-blue: {COLORS['blue']};
            --af-blue-dark: {COLORS['blue_dark']};
            --af-blue-soft: {COLORS['blue_soft']};
            --af-pink: {COLORS['pink']};
            --af-surface: {COLORS['surface']};
            --af-text: {COLORS['text']};
            --af-muted: {COLORS['muted']};
            --af-border: {COLORS['border']};
        }}
        .af-page-title {{font-size: 30px; line-height: 1.15; font-weight: 800; color: var(--af-blue-dark); margin: 0;}}
        .af-page-subtitle {{font-size: 15px; line-height: 1.45; color: var(--af-muted); margin: 6px 0 20px;}}
        .af-section-title {{font-size: 19px; line-height: 1.25; font-weight: 750; color: var(--af-blue-dark); margin: 0 0 8px;}}
        .af-card-title {{font-size: 16px; line-height: 1.25; font-weight: 750; color: var(--af-blue-dark); margin: 0;}}
        .af-body {{font-size: 14px; line-height: 1.5; color: var(--af-text);}}
        .af-small {{font-size: 12px; line-height: 1.45; color: var(--af-muted);}}
        .af-hero {{
            background: linear-gradient(135deg, #FFFFFF 0%, #EEF6FF 100%);
            border: 1px solid var(--af-border); border-radius: 20px; padding: 22px 24px;
            margin-bottom: 16px; box-shadow: 0 8px 24px rgba(6,59,130,.07); position: relative; overflow: hidden;
        }}
        .af-hero:after {{content:""; position:absolute; width:130px; height:130px; border-radius:50%; right:-45px; top:-65px; background:rgba(10,103,232,.10);}}
        .af-feature-card {{
            background:#fff; border:1px solid var(--af-border); border-radius:16px; padding:16px;
            min-height:116px; box-shadow:0 6px 18px rgba(6,59,130,.06);
        }}
        .af-feature-icon {{font-size:24px; margin-bottom:8px;}}
        .af-status-strip {{
            background:#fff; border:1px solid var(--af-border); border-radius:16px; padding:14px 16px; margin:8px 0 16px;
        }}
        .af-preview-shell {{
            background:#fff; border:1px solid var(--af-border); border-radius:18px; padding:15px;
            box-shadow:0 8px 22px rgba(6,59,130,.08); position:sticky; top:70px;
        }}
        .af-score {{font-size:28px; font-weight:850; color:var(--af-blue); line-height:1;}}
        .af-badge {{display:inline-block; font-size:12px; font-weight:700; padding:5px 9px; border-radius:999px; background:var(--af-blue-soft); color:var(--af-blue-dark);}}
        div[data-testid="stButton"] > button[kind="primary"], div[data-testid="stDownloadButton"] > button {{
            background:var(--af-blue)!important; color:#fff!important; border:1px solid var(--af-blue)!important;
            border-radius:12px!important; min-height:42px!important; font-size:14px!important; font-weight:750!important;
        }}
        div[data-testid="stButton"] > button[kind="primary"]:hover, div[data-testid="stDownloadButton"] > button:hover {{
            background:var(--af-blue-dark)!important; border-color:var(--af-blue-dark)!important;
        }}
        div[data-testid="stTextInput"] label, div[data-testid="stTextArea"] label,
        div[data-testid="stSelectbox"] label, div[data-testid="stMultiSelect"] label,
        div[data-testid="stFileUploader"] label, div[data-testid="stRadio"] label {{
            font-size:14px!important; font-weight:650!important; color:var(--af-text)!important;
        }}
        div[data-testid="stTextInput"] input, div[data-testid="stTextArea"] textarea {{font-size:14px!important;}}
        div[data-baseweb="tab-list"] button {{font-size:14px!important; font-weight:700!important;}}
        </style>
        """,
        unsafe_allow_html=True,
    )


def hero(title: str, subtitle: str, badge: str = "") -> None:
    badge_html = f'<span class="af-badge">{html.escape(badge)}</span>' if badge else ""
    st.markdown(
        f'<div class="af-hero">{badge_html}<div class="af-page-title">{html.escape(title)}</div>'
        f'<div class="af-page-subtitle">{html.escape(subtitle)}</div></div>',
        unsafe_allow_html=True,
    )


def feature_card(title: str, description: str, icon: str) -> None:
    st.markdown(
        f'<div class="af-feature-card"><div class="af-feature-icon">{html.escape(icon)}</div>'
        f'<div class="af-card-title">{html.escape(title)}</div>'
        f'<div class="af-small" style="margin-top:6px">{html.escape(description)}</div></div>',
        unsafe_allow_html=True,
    )


def section_title(title: str, subtitle: str = "") -> None:
    subtitle_html = f'<div class="af-small">{html.escape(subtitle)}</div>' if subtitle else ""
    st.markdown(f'<div class="af-section-title">{html.escape(title)}</div>{subtitle_html}', unsafe_allow_html=True)
