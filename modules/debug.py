"""
Debugging and status rendering module for StudyMate AI (Phase 1).
Contains status display helpers for developers when running in Debug Mode.
"""

import os
import streamlit as st
from modules.supabase_client import health_check, validate_credentials


def render_supabase_status() -> None:
    """
    If DEBUG mode is enabled, validate Supabase credentials and perform a health check.
    Displays connection status at the bottom of the Streamlit sidebar.
    Uses st.session_state caching to avoid hitting the database on every rerun.
    """
    # Load debug status from env or streamlit secrets
    debug_mode = False

    # Check Streamlit secrets first
    try:
        if hasattr(st, "secrets") and st.secrets is not None:
            debug_mode = str(st.secrets.get("DEBUG", "false")).lower() in ("true", "1")
    except Exception:
        pass

    # Check environment variables
    if not debug_mode:
        debug_mode = os.getenv("DEBUG", "false").lower() in ("true", "1")

    if not debug_mode:
        return

    st.sidebar.markdown("<hr>", unsafe_allow_html=True)
    st.sidebar.markdown("##### 🛠️ Developer Debug")

    # 1. Validate credentials
    is_valid, err_msg = validate_credentials()
    if not is_valid:
        st.sidebar.error(f"✗ Supabase Config: {err_msg}")
        return

    # 2. Perform connection health check (cached to avoid redundant queries)
    if "supabase_connection_status" not in st.session_state:
        st.session_state.supabase_connection_status = health_check()

    status = st.session_state.supabase_connection_status
    if status:
        st.sidebar.markdown(
            '<div style="color: #4CAF50; font-weight: bold; margin-bottom: 5px;">✓ Connected to Supabase</div>',
            unsafe_allow_html=True
        )
    else:
        st.sidebar.markdown(
            '<div style="color: #F44336; font-weight: bold; margin-bottom: 5px;">✗ Supabase unavailable</div>',
            unsafe_allow_html=True
        )
        if st.sidebar.button("Retry Supabase Connection", key="retry_supabase_btn", use_container_width=True):
            st.session_state.supabase_connection_status = health_check()
            st.rerun()
