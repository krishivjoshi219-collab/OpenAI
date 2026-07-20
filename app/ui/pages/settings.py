"""Settings page layout."""

import streamlit as st

from app.i18n import t
from app.ui.components.layout import render_page_header, render_section_title


def render() -> None:
    """Render presentation-only workspace settings."""

    render_page_header(
        t("settings.eyebrow"),
        t("settings.title"),
        t("settings.subtitle"),
    )
    render_section_title(t("settings.section.profile"))
    left, right = st.columns(2, gap="large")
    with left:
        st.text_input(t("settings.label.biz_name"), placeholder=t("settings.ph.biz_name"))
        st.text_input(t("settings.label.biz_email"), placeholder=t("settings.ph.biz_email"))
    with right:
        st.selectbox(t("settings.label.currency"), [
            t("settings.opt.currency.usd"),
            t("settings.opt.currency.eur"),
            t("settings.opt.currency.inr"),
        ])
        st.selectbox(t("settings.label.timezone"), [
            t("settings.opt.tz.kolkata"),
            t("settings.opt.tz.london"),
            t("settings.opt.tz.newyork"),
        ])
    render_section_title(t("settings.section.notif"))
    st.toggle(t("settings.toggle.summary"), value=True, help=t("settings.help.summary"))
    st.toggle(t("settings.toggle.alerts"), value=True, help=t("settings.help.alerts"))
    st.button(t("settings.btn.save"), type="primary")
