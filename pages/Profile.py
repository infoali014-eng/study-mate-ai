import html
import streamlit as st

st.set_page_config(page_title="Profile Settings - StudyMate AI", layout="wide")

from modules.auth import require_login
from modules.database import init_db
from modules.ui import apply_theme, page_header, sidebar_nav, section_title, render_tip
from modules.profile_repository import ProfileRepository

user_id = require_login()
init_db()
apply_theme()
sidebar_nav()

page_header(
    "Profile Settings",
    "Manage your personal information, username, and profile avatar.",
    "Settings",
)

# Fetch latest user profile details (automatically uses cache or queries DB)
profile = ProfileRepository.get_profile(user_id)
if not profile:
    st.error("Could not load your profile. Please try again.")
    st.stop()

# Initialize session state for edit fields to preserve them across uploads
if "profile_full_name" not in st.session_state:
    st.session_state.profile_full_name = profile.get("full_name") or ""
if "profile_username" not in st.session_state:
    st.session_state.profile_username = profile.get("username") or ""
if "profile_bio" not in st.session_state:
    st.session_state.profile_bio = profile.get("bio") or ""

# ─────────────────────────────────────────────────────────────────────────────
# 1. Profile Picture Management
# ─────────────────────────────────────────────────────────────────────────────
section_title("Profile Picture", "user")

left_col, right_col = st.columns([1, 3])

with left_col:
    # Render large preview of current avatar
    avatar_url = st.session_state.get("profile_image_url") or profile.get("profile_image_url")
    if avatar_url:
        st.markdown(
            f"""
            <div style="display:flex; justify-content:center; margin-bottom:12px;">
                <img src="{html.escape(avatar_url)}" style="width:128px; height:128px; border-radius:50%; object-fit:cover; border:2px solid var(--color-primary); box-shadow:var(--shadow-md);">
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Delete Picture", use_container_width=True, key="del_avatar_btn"):
            if ProfileRepository.delete_profile_picture(user_id):
                st.success("Profile picture deleted.")
                st.rerun()
            else:
                st.error("Failed to delete picture.")
    else:
        initials = "".join(p[0] for p in (st.session_state.profile_full_name or "Student").split()[:2]).upper() or "ST"
        st.markdown(
            f"""
            <div style="display:flex; justify-content:center; margin-bottom:12px;">
                <div style="width:128px; height:128px; border-radius:50%; background:var(--color-primary-muted); color:var(--color-primary-dark); font-weight:700; font-size:2.5rem; display:flex; align-items:center; justify-content:center; border:2px dashed var(--color-primary-light); box-shadow:var(--shadow-sm);">
                    {html.escape(initials)}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

with right_col:
    uploaded_file = st.file_uploader(
        "Upload new profile picture (PNG, JPG, JPEG, WEBP - Max 5MB)",
        type=["png", "jpg", "jpeg", "webp"],
        help="Images will be cropped to square automatically."
    )
    if uploaded_file is not None:
        file_bytes = uploaded_file.read()
        file_size = len(file_bytes)
        
        if file_size > 5 * 1024 * 1024:
            st.error("File size exceeds 5MB limit. Please choose a smaller image.")
        else:
            with st.spinner("Processing & uploading image..."):
                new_url = ProfileRepository.upload_profile_picture(
                    user_id=user_id,
                    image_bytes=file_bytes,
                    file_name=uploaded_file.name,
                    file_size=file_size
                )
                if new_url:
                    st.success("Profile picture updated successfully!")
                    st.rerun()
                else:
                    st.error("Failed to process and upload profile image.")

st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# 2. Account Details Form
# ─────────────────────────────────────────────────────────────────────────────
section_title("Account Details", "settings")

with st.form("profile_form", clear_on_submit=False):
    # Full Name input
    full_name = st.text_input("Full Name *", value=st.session_state.profile_full_name)
    
    # Username input
    username = st.text_input("Username", value=st.session_state.profile_username, placeholder="e.g. ali_shair")
    st.caption("Optional. Only letters, numbers, and underscores are allowed (3–30 characters).")
    
    # Read-only Email
    st.text_input("Email Address", value=profile.get("email", ""), disabled=True)
    if profile.get("email_verified"):
        st.markdown(
            '<div style="margin-top:-10px; margin-bottom:15px; font-size:0.75rem; color:var(--color-success); font-weight:600; display:flex; align-items:center; gap:4px;">'
            'Verified Account'
            '</div>',
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            '<div style="margin-top:-10px; margin-bottom:15px; font-size:0.75rem; color:var(--color-text-muted); font-weight:500;">'
            'Verification pending'
            '</div>',
            unsafe_allow_html=True
        )
        
    # Bio input
    bio = st.text_area("Bio / About Me", value=st.session_state.profile_bio, placeholder="Write a short description about yourself...")
    
    col_submit, col_cancel = st.columns([1, 4])
    with col_submit:
        save_btn = st.form_submit_button("Save Changes", use_container_width=True, type="primary")
    with col_cancel:
        cancel_btn = st.form_submit_button("Cancel", use_container_width=False)

if save_btn:
    # 1. Validate Full Name
    if not full_name or len(full_name.strip()) < 2 or len(full_name.strip()) > 100:
        st.error("Full Name is required and must be between 2 and 100 characters.")
    else:
        # 2. Validate Username
        is_valid_user, user_err = ProfileRepository.validate_username(username)
        if not is_valid_user:
            st.error(user_err)
        # 3. Check Username Uniqueness
        elif username and not ProfileRepository.is_username_available(username, exclude_user_id=user_id):
            st.error("This username is already taken. Please choose another one.")
        else:
            # 4. Save Profile
            if ProfileRepository.update_profile(
                user_id=user_id,
                full_name=full_name.strip(),
                username=username.strip() if username else None,
                bio=bio.strip() if bio else None
            ):
                # Update session states immediately
                st.session_state.profile_full_name = full_name.strip()
                st.session_state.profile_username = username.strip() if username else ""
                st.session_state.profile_bio = bio.strip() if bio else ""
                
                st.success("Profile updated successfully!")
                st.rerun()
            else:
                st.error("Failed to update profile. Please try again.")

if cancel_btn:
    st.switch_page("pages/1_Dashboard.py")

render_tip("Your credentials and verification details are securely stored. Read-only fields cannot be edited from this settings page.")
