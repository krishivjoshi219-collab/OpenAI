"""Animated toast notifications for Streamlit."""

from __future__ import annotations

import time

import streamlit as st


def inject_toast_container() -> None:
    """Inject the fixed toast container into the DOM once per page load."""

    st.markdown(
        """
        <div class="toast-container" id="toast-root"></div>
        """,
        unsafe_allow_html=True,
    )


def render_toast(title: str, message: str, *, icon: str = "✨", duration: float = 3.5) -> None:
    """Render a single animated toast notification.

    Args:
        title: Bold headline text.
        message: Supporting detail text.
        icon: Emoji or short string shown on the left.
        duration: Seconds before the toast auto-removes.
    """

    key = f"toast_{int(time.time() * 1000)}"
    st.markdown(
        f"""
        <div class="toast-container" id="{key}">
          <div class="toast">
            <div class="toast-icon">{icon}</div>
            <div class="toast-body">
              <div class="toast-title">{title}</div>
              <div class="toast-message">{message}</div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    _schedule_removal(key, duration)


def _schedule_removal(key: str, duration: float) -> None:
    """Schedule toast removal after a delay using a lightweight rerun trick."""

    placeholder = st.empty()
    with placeholder.container():
        st.markdown(
            f"""
            <script>
            (function() {{
                var el = document.getElementById("{key}");
                if (!el) return;
                setTimeout(function() {{
                    var toast = el.querySelector(".toast");
                    if (!toast) return;
                    toast.classList.add("removing");
                    setTimeout(function() {{ el.remove(); }}, 250);
                }}, {int(duration * 1000)});
            }})();
            </script>
            """,
            unsafe_allow_html=True,
        )
