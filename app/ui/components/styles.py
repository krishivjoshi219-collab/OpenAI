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
            --shadow: 0 1px 2px rgba(22,32,29,.04), 0 4px 16px rgba(22,32,29,.06);
            --shadow-hover: 0 2px 4px rgba(22,32,29,.06), 0 8px 28px rgba(22,32,29,.10);
        }

        * { box-sizing: border-box; }
        .stApp { background: var(--paper); color: var(--ink); }
        .stApp, .stApp button, .stApp input { font-family: 'Manrope', sans-serif; }
        /* Hide Streamlit branding.  NOTE: do NOT hide `header` here — the
           header element contains the sidebar collapse/expand toggle button
           that users need on Streamlit Community Cloud and on mobile/narrow
           viewports.  Hiding the full header was the cause of "cannot open
           the menu" reports on Cloud deployments. */
        #MainMenu { visibility: hidden; }
        footer { visibility: hidden; }
        header { background: transparent !important;
                 border-bottom: none !important; }
        /* Hide only the deploy/share toolbar items Streamlit injects */
        [data-testid="stToolbarActions"] { visibility: hidden; }
        .block-container { max-width: 1420px; padding: 2.5rem 3rem 4rem; }

        /* ── Page entrance animation ───────────────────────────────────── */
        @keyframes pageFadeIn {
            from { opacity: 0; transform: translateY(8px); }
            to   { opacity: 1; transform: translateY(0); }
        }
        .block-container > div:first-of-type { animation: pageFadeIn .35s ease-out; }

        /* ── Sidebar ───────────────────────────────────────────────────── */
        [data-testid="stSidebar"] { background: #102a22; border-right: 0; }
        [data-testid="stSidebar"] > div:first-child { padding: 1.35rem 1rem; }
        [data-testid="stSidebar"] * { color: #edf7f1; }
        [data-testid="stSidebar"] .stRadio > div { gap: .3rem; }
        [data-testid="stSidebar"] label {
            border-radius: 10px;
            padding: .5rem .6rem;
            transition: background .18s ease, transform .12s ease;
            cursor: pointer;
        }
        [data-testid="stSidebar"] label:hover {
            background: rgba(217,247,231,.12);
            transform: translateX(2px);
        }
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { font-size: .88rem; }
        [data-testid="stSidebar"] input { accent-color: var(--lime); }

        /* ── Typography ────────────────────────────────────────────────── */
        .eyebrow {
            color: var(--forest);
            font: 500 .7rem 'DM Mono', monospace;
            letter-spacing: .1em;
            text-transform: uppercase;
            margin-bottom: .55rem;
            animation: pageFadeIn .4s ease-out;
        }
        .page-title {
            font-size: clamp(2rem, 3vw, 3rem);
            letter-spacing: -.065em;
            line-height: 1.02;
            margin: 0;
            color: var(--ink);
            animation: pageFadeIn .45s ease-out;
        }
        .page-subtitle {
            color: var(--muted);
            margin: .8rem 0 0;
            font-size: .98rem;
            max-width: 42rem;
            line-height: 1.65;
            animation: pageFadeIn .5s ease-out;
        }
        .section-title {
            font-size: 1.05rem;
            font-weight: 800;
            letter-spacing: -.03em;
            margin: 1.75rem 0 .75rem;
            animation: pageFadeIn .35s ease-out;
        }

        /* ── Cards & surfaces ──────────────────────────────────────────── */
        .product-card {
            background: #fff;
            border: 1px solid var(--line);
            border-radius: 18px;
            padding: 1.15rem;
            min-height: 100%;
            box-shadow: var(--shadow);
            transition: box-shadow .22s ease, transform .22s ease;
        }
        .product-card:hover {
            box-shadow: var(--shadow-hover);
            transform: translateY(-2px);
        }

        /* ── Metrics ───────────────────────────────────────────────────── */
        .metric-label { color: var(--muted); font-size: .78rem; font-weight: 700; }
        .metric-value {
            color: var(--ink);
            font-size: 1.65rem;
            font-weight: 800;
            letter-spacing: -.065em;
            margin: .3rem 0;
            transition: color .2s ease;
        }
        .metric-change { color: var(--forest); font: 500 .72rem 'DM Mono', monospace; }
        .metric-change.neutral { color: var(--muted); }

        [data-testid="stMetric"] {
            background: #fff;
            border: 1px solid var(--line);
            border-radius: 18px;
            padding: 1.05rem 1.15rem;
            box-shadow: var(--shadow);
            transition: box-shadow .22s ease, transform .22s ease;
        }
        [data-testid="stMetric"]:hover {
            box-shadow: var(--shadow-hover);
            transform: translateY(-2px);
        }
        [data-testid="stMetricLabel"] { color: var(--muted); font-size: .76rem; font-weight: 700; }
        [data-testid="stMetricValue"] {
            color: var(--ink);
            font-size: 1.55rem;
            font-weight: 800;
            letter-spacing: -.055em;
            transition: color .2s ease;
        }
        [data-testid="stVerticalBlockBorderWrapper"] {
            border-color: var(--line) !important;
            border-radius: 18px !important;
            background: rgba(255,255,255,.72);
        }

        /* ── Action card ───────────────────────────────────────────────── */
        .action-card {
            background: var(--forest);
            color: white;
            border-radius: 18px;
            padding: 1.45rem;
            box-shadow: var(--shadow);
            transition: box-shadow .22s ease, transform .22s ease;
        }
        .action-card:hover {
            box-shadow: var(--shadow-hover);
            transform: translateY(-2px);
        }
        .action-card h3 {
            font-size: 1.15rem;
            letter-spacing: -.04em;
            margin: 0 0 .5rem;
        }
        .action-card p {
            color: #cfe7dc;
            font-size: .86rem;
            line-height: 1.55;
            margin: 0;
        }

        /* ── Table rows ────────────────────────────────────────────────── */
        .table-row { border-top: 1px solid var(--line); padding: .85rem 0; }
        .table-row:first-child { border-top: 0; }
        .row-primary { font-size: .88rem; font-weight: 700; color: var(--ink); }
        .row-secondary { color: var(--muted); font-size: .76rem; margin-top: .16rem; }

        /* ── Badges ────────────────────────────────────────────────────── */
        .badge {
            display: inline-block;
            border-radius: 100px;
            padding: .24rem .52rem;
            font: 500 .67rem 'DM Mono', monospace;
            transition: transform .15s ease;
        }
        .badge:hover { transform: scale(1.05); }
        .badge-success { color: #0b6648; background: #def8e9; }
        .badge-warning { color: #865500; background: #fff0c8; }
        .badge-neutral { color: #53615c; background: #edf0ee; }

        /* ── Empty state ───────────────────────────────────────────────── */
        .empty-state {
            border: 1px dashed #cbd6cf;
            border-radius: 18px;
            padding: 2.6rem 1.4rem;
            text-align: center;
            background: rgba(255,255,255,.58);
            animation: pageFadeIn .5s ease-out;
        }
        .empty-icon {
            font-size: 1.6rem;
            margin-bottom: .35rem;
            animation: float 3s ease-in-out infinite;
        }
        @keyframes float {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-4px); }
        }
        .empty-title { font-weight: 800; letter-spacing: -.035em; }
        .empty-copy {
            color: var(--muted);
            font-size: .84rem;
            max-width: 25rem;
            margin: .4rem auto 0;
            line-height: 1.55;
        }

        /* ── Sidebar brand ──────────────────────────────────────────────── */
        .sidebar-brand { padding: .25rem .45rem 1.55rem; animation: pageFadeIn .3s ease-out; }
        .brand-mark {
            display: inline-flex;
            width: 30px;
            height: 30px;
            border-radius: 9px;
            align-items: center;
            justify-content: center;
            background: var(--lime);
            color: var(--forest);
            font-weight: 800;
            margin-right: .55rem;
            transition: transform .2s ease;
        }
        .sidebar-brand:hover .brand-mark { transform: rotate(-8deg) scale(1.05); }
        .brand-name { font-size: .95rem; font-weight: 800; letter-spacing: -.04em; }
        .brand-caption {
            color: #9bb7aa;
            font: .63rem 'DM Mono', monospace;
            letter-spacing: .08em;
            text-transform: uppercase;
            margin-top: .45rem;
        }
        .sidebar-note {
            background: rgba(217,247,231,.1);
            border: 1px solid rgba(217,247,231,.13);
            border-radius: 12px;
            padding: .75rem;
            margin-top: 1.5rem;
            color: #bbd6c9;
            font-size: .73rem;
            line-height: 1.5;
            animation: pageFadeIn .6s ease-out;
        }

        /* ── Buttons ───────────────────────────────────────────────────── */
        .stButton > button {
            border-radius: 10px;
            border: 0;
            background: var(--forest);
            color: white;
            font-weight: 700;
            padding: .55rem .9rem;
            transition: background .18s ease, transform .12s ease, box-shadow .18s ease;
            box-shadow: 0 1px 2px rgba(22,32,29,.08);
        }
        .stButton > button:hover {
            background: #0b4939;
            color: white;
            border: 0;
            transform: translateY(-1px);
            box-shadow: 0 2px 6px rgba(22,32,29,.12);
        }
        .stButton > button:active {
            transform: translateY(0);
            box-shadow: 0 1px 1px rgba(22,32,29,.08);
        }
        .stButton > button:focus-visible {
            outline: 2px solid var(--lime);
            outline-offset: 2px;
        }

        /* ── Form inputs ───────────────────────────────────────────────── */
        .stTextInput input, .stTextArea textarea, .stSelectbox > div > div {
            border-radius: 10px;
            border-color: var(--line);
            transition: border-color .18s ease, box-shadow .18s ease;
        }
        .stTextInput input:focus, .stTextArea textarea:focus {
            border-color: var(--forest);
            box-shadow: 0 0 0 3px rgba(18,91,72,.12);
        }

        /* ── Loading shimmer ───────────────────────────────────────────── */
        @keyframes shimmer {
            0% { background-position: -200% 0; }
            100% { background-position: 200% 0; }
        }
        .shimmer {
            background: linear-gradient(90deg, #edf0ee 25%, #f5f7f5 50%, #edf0ee 75%);
            background-size: 200% 100%;
            animation: shimmer 1.5s infinite;
            border-radius: 10px;
        }

        /* ── Toast notifications ───────────────────────────────────────── */
        @keyframes slideInRight {
            from { opacity: 0; transform: translateX(40px); }
            to   { opacity: 1; transform: translateX(0); }
        }
        @keyframes slideOutRight {
            from { opacity: 1; transform: translateX(0); }
            to   { opacity: 0; transform: translateX(40px); }
        }
        .toast-container {
            position: fixed;
            top: 1.2rem;
            right: 1.2rem;
            z-index: 99999;
            display: flex;
            flex-direction: column;
            gap: .6rem;
            pointer-events: none;
        }
        .toast {
            pointer-events: auto;
            background: #fff;
            border: 1px solid var(--line);
            border-radius: 14px;
            padding: .85rem 1.1rem;
            box-shadow: var(--shadow-hover);
            min-width: 280px;
            max-width: 380px;
            animation: slideInRight .28s ease-out;
            display: flex;
            align-items: flex-start;
            gap: .6rem;
        }
        .toast.removing { animation: slideOutRight .22s ease-in forwards; }
        .toast-icon { font-size: 1.1rem; line-height: 1; flex-shrink: 0; }
        .toast-body { flex: 1; }
        .toast-title { font-weight: 700; font-size: .88rem; color: var(--ink); }
        .toast-message { font-size: .82rem; color: var(--muted); margin-top: .15rem; line-height: 1.4; }

        /* ── Responsive ────────────────────────────────────────────────── */
        @media (max-width: 900px) { .block-container { padding: 1.5rem 1rem 3rem; } }

        /* ── Voice command styles ──────────────────────────────────────── */
        .voice-transcript {
            background: var(--mint);
            border: 1px solid #a3e8c3;
            border-radius: 12px;
            padding: .75rem 1rem;
            font-size: .9rem;
            font-weight: 600;
            color: var(--forest);
            margin: .6rem 0 .5rem;
            line-height: 1.5;
            animation: pageFadeIn .3s ease-out;
        }
        .voice-icon { margin-right: .4rem; }
        .voice-examples { margin-top: .25rem; }
        .voice-example-lang {
            font: 700 .75rem 'DM Mono', monospace;
            color: var(--muted);
            letter-spacing: .06em;
            text-transform: uppercase;
            margin: .5rem 0 .35rem;
        }
        .voice-example-chip {
            background: #fff;
            border: 1px solid var(--line);
            border-radius: 8px;
            padding: .4rem .7rem;
            font-size: .78rem;
            color: var(--ink);
            margin-bottom: .3rem;
            line-height: 1.45;
            transition: border-color .18s ease, transform .12s ease;
        }
        .voice-example-chip:hover {
            border-color: var(--forest);
            transform: translateY(-1px);
        }
        .voice-fill-hint {
            color: var(--muted);
            font-size: .78rem;
            margin: .25rem 0 .5rem;
            font-style: italic;
        }

        /* ── Progress bar polish ───────────────────────────────────────── */
        .stProgress > div > div > div {
            background: var(--forest);
            transition: width .4s ease;
        }

        /* ── Loading spinner ───────────────────────────────────────────── */
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        .custom-spinner {
            width: 28px;
            height: 28px;
            border: 3px solid var(--line);
            border-top-color: var(--forest);
            border-radius: 50%;
            animation: spin .7s linear infinite;
            margin: 0 auto;
        }

        /* ── Voice recording pulse ──────────────────────────────────────── */
        @keyframes pulse-ring {
            0% { transform: scale(.95); box-shadow: 0 0 0 0 rgba(255,132,109,.5); }
            70% { transform: scale(1.05); box-shadow: 0 0 0 8px rgba(255,132,109,0); }
            100% { transform: scale(.95); box-shadow: 0 0 0 0 rgba(255,132,109,0); }
        }
        .voice-recording-indicator {
            display: inline-flex;
            align-items: center;
            gap: .5rem;
            background: #fff5f3;
            border: 1px solid #ffd6cc;
            border-radius: 10px;
            padding: .45rem .85rem;
            font-size: .82rem;
            font-weight: 600;
            color: #c2410c;
            animation: pulse-ring 1.8s ease-in-out infinite;
        }
        .voice-recording-dot {
            width: 8px;
            height: 8px;
            background: #ff846d;
            border-radius: 50%;
            animation: pulse-ring 1.8s ease-in-out infinite;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
