import streamlit as st

from modules.auth import require_admin
from modules.database import (
    init_db,
)
from modules.user_repository import (
    get_all_users_with_stats,
    set_user_active,
    update_user_role,
)
from modules.ui import apply_theme, page_header, section_title, sidebar_nav


st.set_page_config(page_title="User Management - StudyMate AI", layout="wide")
admin_id = require_admin()
init_db()
apply_theme()
sidebar_nav()

page_header(
    "User Management",
    "View users, activity counts, roles, and account status without exposing secrets.",
    "Admin Controls",
)

search = st.text_input("Search users by name or email", placeholder="Search users")
users = get_all_users_with_stats(search)

section_title("Users", "users")
if not users:
    st.info("No users found.")

for user in users:
    with st.container(border=True):
        info_col, role_col, status_col = st.columns([3, 1.3, 1.3])
        with info_col:
            st.markdown(f"**{user['name']}**")
            st.caption(
                f"{user['email']} | Created: {user['created_at']} | "
                f"Subjects: {user['subject_count']} | Documents: {user['document_count']}"
            )
        with role_col:
            role = st.selectbox(
                "Role",
                ["student", "admin"],
                index=0 if user["role"] == "student" else 1,
                key=f"role_{user['id']}",
            )
            if st.button("Update Role", key=f"update_role_{user['id']}", use_container_width=True):
                ok, message = update_user_role(user["id"], role, admin_id)
                if ok:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)
        with status_col:
            is_active = st.checkbox(
                "Active",
                value=bool(user["is_active"]),
                key=f"active_{user['id']}",
            )
            if st.button("Update Status", key=f"update_status_{user['id']}", use_container_width=True):
                ok, message = set_user_active(user["id"], is_active, admin_id)
                if ok:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)
