"""Visual design tokens and global Streamlit overrides."""

# ruff: noqa: E501

import streamlit as st


def apply_global_styles() -> None:
    """Apply the product's shared visual language once per page render."""

    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@400;500;600;700;800&display=swap');

        :root {
            --ink: #16201d;
            --muted: #64706c;
            --paper: #f8faf7;
            --line: #e5eae5;
            --forest: #125b48;
            --mint: #d9f7e7;
            --lime: #c7f36b;
            --coral: #ff846d;
        }
        .stApp { background: var(--paper); color: var(--ink); }
        .stApp, .stApp button, .stApp input { font-family: 'Manrope', sans-serif; }
        #MainMenu, footer, header { visibility: hidden; }
        .block-container { max-width: 1420px; padding: 2.5rem 3rem 4rem; }
        [data-testid="stSidebar"] { background: #102a22; border-right: 0; }
        [data-testid="stSidebar"] > div:first-child { padding: 1.35rem 1rem; }
        [data-testid="stSidebar"] * { color: #edf7f1; }
        [data-testid="stSidebar"] .stRadio > div { gap: .3rem; }
        [data-testid="stSidebar"] label { border-radius: 10px; padding: .5rem .6rem; }
        [data-testid="stSidebar"] label:hover { background: rgba(217,247,231,.12); }
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { font-size: .88rem; }
        [data-testid="stSidebar"] input { accent-color: var(--lime); }
        .eyebrow { color: var(--forest); font: 500 .7rem 'DM Mono', monospace; letter-spacing: .1em; text-transform: uppercase; margin-bottom: .55rem; }
        .page-title { font-size: clamp(2rem, 3vw, 3rem); letter-spacing: -.065em; line-height: 1.02; margin: 0; color: var(--ink); }
        .page-subtitle { color: var(--muted); margin: .8rem 0 0; font-size: .98rem; max-width: 42rem; line-height: 1.65; }
        .section-title { font-size: 1.05rem; font-weight: 800; letter-spacing: -.03em; margin: 1.75rem 0 .75rem; }
        .product-card { background: #fff; border: 1px solid var(--line); border-radius: 18px; padding: 1.15rem; min-height: 100%; }
        .metric-label { color: var(--muted); font-size: .78rem; font-weight: 700; }
        .metric-value { color: var(--ink); font-size: 1.65rem; font-weight: 800; letter-spacing: -.065em; margin: .3rem 0; }
        .metric-change { color: var(--forest); font: 500 .72rem 'DM Mono', monospace; }
        .metric-change.neutral { color: var(--muted); }
        [data-testid="stMetric"] { background: #fff; border: 1px solid var(--line); border-radius: 18px; padding: 1.05rem 1.15rem; }
        [data-testid="stMetricLabel"] { color: var(--muted); font-size: .76rem; font-weight: 700; }
        [data-testid="stMetricValue"] { color: var(--ink); font-size: 1.55rem; font-weight: 800; letter-spacing: -.055em; }
        [data-testid="stVerticalBlockBorderWrapper"] { border-color: var(--line) !important; border-radius: 18px !important; background: rgba(255,255,255,.72); }
        .action-card { background: var(--forest); color: white; border-radius: 18px; padding: 1.45rem; }
        .action-card h3 { font-size: 1.15rem; letter-spacing: -.04em; margin: 0 0 .5rem; }
        .action-card p { color: #cfe7dc; font-size: .86rem; line-height: 1.55; margin: 0; }
        .table-row { border-top: 1px solid var(--line); padding: .85rem 0; }
        .table-row:first-child { border-top: 0; }
        .row-primary { font-size: .88rem; font-weight: 700; color: var(--ink); }
        .row-secondary { color: var(--muted); font-size: .76rem; margin-top: .16rem; }
        .badge { display: inline-block; border-radius: 100px; padding: .24rem .52rem; font: 500 .67rem 'DM Mono', monospace; }
        .badge-success { color: #0b6648; background: #def8e9; }
        .badge-warning { color: #865500; background: #fff0c8; }
        .badge-neutral { color: #53615c; background: #edf0ee; }
        .empty-state { border: 1px dashed #cbd6cf; border-radius: 18px; padding: 2.6rem 1.4rem; text-align: center; background: rgba(255,255,255,.58); }
        .empty-icon { font-size: 1.6rem; margin-bottom: .35rem; }
        .empty-title { font-weight: 800; letter-spacing: -.035em; }
        .empty-copy { color: var(--muted); font-size: .84rem; max-width: 25rem; margin: .4rem auto 0; line-height: 1.55; }
        .sidebar-brand { padding: .25rem .45rem 1.55rem; }
        .brand-mark { display: inline-flex; width: 30px; height: 30px; border-radius: 9px; align-items: center; justify-content: center; background: var(--lime); color: var(--forest); font-weight: 800; margin-right: .55rem; }
        .brand-name { font-size: .95rem; font-weight: 800; letter-spacing: -.04em; }
        .brand-caption { color: #9bb7aa; font: .63rem 'DM Mono', monospace; letter-spacing: .08em; text-transform: uppercase; margin-top: .45rem; }
        .sidebar-note { background: rgba(217,247,231,.1); border: 1px solid rgba(217,247,231,.13); border-radius: 12px; padding: .75rem; margin-top: 1.5rem; color: #bbd6c9; font-size: .73rem; line-height: 1.5; }
        .stButton > button { border-radius: 10px; border: 0; background: var(--forest); color: white; font-weight: 700; padding: .55rem .9rem; }
        .stButton > button:hover { background: #0b4939; color: white; border: 0; }
        .stTextInput input, .stTextArea textarea, .stSelectbox > div > div { border-radius: 10px; border-color: var(--line); }
        @media (max-width: 900px) { .block-container { padding: 1.5rem 1rem 3rem; } }
        </style>
        """,
        unsafe_allow_html=True,
    )
