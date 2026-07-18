"""Small reusable UI elements used across Streamlit pages."""

from dataclasses import dataclass

import streamlit as st


@dataclass(frozen=True)
class Metric:
    """Presentation-only data for a dashboard metric card."""

    label: str
    value: str
    detail: str
    tone: str = "positive"


def render_metric(metric: Metric) -> None:
    """Render a compact metric card."""

    tone_class = "neutral" if metric.tone == "neutral" else ""
    st.markdown(
        f"""
        <div class="product-card">
          <div class="metric-label">{metric.label}</div>
          <div class="metric-value">{metric.value}</div>
          <div class="metric-change {tone_class}">{metric.detail}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_empty_state(icon: str, title: str, description: str, action: str) -> None:
    """Render an intentional empty state with a non-functional action affordance."""

    st.markdown(
        f"""
        <div class="empty-state">
          <div class="empty-icon">{icon}</div>
          <div class="empty-title">{title}</div>
          <div class="empty-copy">{description}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.button(action, use_container_width=False, key=f"empty_{action}")


def render_record_row(name: str, detail: str, badge: str, badge_tone: str = "neutral") -> None:
    """Render a lightweight list row suitable for preview tables."""

    left, right = st.columns([5, 1])
    with left:
        st.markdown(
            f'<div class="table-row"><div class="row-primary">{name}</div>'
            f'<div class="row-secondary">{detail}</div></div>',
            unsafe_allow_html=True,
        )
    with right:
        st.markdown(
            f'<div class="table-row" style="text-align:right; padding-top:1.05rem;">'
            f'<span class="badge badge-{badge_tone}">{badge}</span></div>',
            unsafe_allow_html=True,
        )
