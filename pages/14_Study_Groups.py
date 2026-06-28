import html
import streamlit as st
from pathlib import Path

from modules.auth import require_login
from modules.database import (
    create_study_group,
    join_study_group,
    get_user_study_groups,
    get_group_members,
    get_group_subjects,
    get_group_leaderboard,
    get_documents,
    add_subject,
    get_connection,
)
from modules.ui import apply_theme, page_header, sidebar_nav, section_title
from contextlib import closing

# Require login & initialize UI
user_id = require_login()
apply_theme()
sidebar_nav()

page_header(
    "Study Groups",
    "Collaborate, share study notes, and compete with your classmates.",
    "Shared Workspace"
)

# Custom premium CSS for Study Groups page
st.markdown(
    """
    <style>
        .group-card {
            border: 1px solid rgba(148, 163, 184, 0.2) !important;
            border-radius: 18px !important;
            padding: 18px !important;
            background: linear-gradient(135deg, rgba(255, 255, 255, 0.95), rgba(245, 243, 255, 0.95)) !important;
            box-shadow: 0 8px 30px rgba(124, 58, 237, 0.04) !important;
            margin-bottom: 20px;
        }
        .code-badge {
            display: inline-block;
            background: linear-gradient(135deg, #F3E8FF, #E9D5FF) !important;
            color: #6B21A8 !important;
            font-size: 1.3rem !important;
            font-weight: 800 !important;
            letter-spacing: 0.05em !important;
            padding: 8px 20px !important;
            border-radius: 12px !important;
            border: 1.5px dashed #A855F7 !important;
            font-family: monospace !important;
            margin: 10px 0 !important;
            text-align: center;
        }
        .leaderboard-rank {
            width: 28px;
            height: 28px;
            border-radius: 50%;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-weight: 800;
            font-size: 0.88rem;
            margin-right: 8px;
        }
        .rank-1 { background-color: #FEF08A; color: #854D0E; border: 1.5px solid #EAB308; }
        .rank-2 { background-color: #E2E8F0; color: #475569; border: 1.5px solid #94A3B8; }
        .rank-3 { background-color: #FFEDD5; color: #9A3412; border: 1.5px solid #EA580C; }
        .rank-other { background-color: #F1F5F9; color: #64748B; border: 1.5px solid #CBD5E1; }
        
        .study-active-dot {
            width: 10px;
            height: 10px;
            background-color: #22C55E;
            border-radius: 50%;
            display: inline-block;
            margin-right: 6px;
            box-shadow: 0 0 8px #22C55E;
        }
        .study-inactive-dot {
            width: 10px;
            height: 10px;
            background-color: #94A3B8;
            border-radius: 50%;
            display: inline-block;
            margin-right: 6px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# Fetch user groups
user_groups = get_user_study_groups(user_id)

# Top action row: Join / Create group toggle
col_left, col_right = st.columns([0.7, 0.3])

with col_right:
    with st.popover("➕ Options", use_container_width=True):
        with st.container(height=450, border=False):
            st.markdown("### Create a Study Group")
            g_name = st.text_input("Group Name", placeholder="e.g. AP Calculus Study Group", key="new_group_name")
            g_desc = st.text_area("Description", placeholder="We share notes and quiz each other on Math.", key="new_group_desc")
            if st.button("Create Group", type="primary", use_container_width=True):
                if g_name.strip():
                    group_id, invite_code = create_study_group(g_name, g_desc, user_id)
                    if group_id:
                        st.success(f"Group created! Share Code: {invite_code}")
                        st.rerun()
                    else:
                        st.error("Error creating group.")
                else:
                    st.warning("Group Name is required.")
    
            st.markdown("---")
            st.markdown("### Join a Study Group")
            join_code = st.text_input("Enter Invite Code", placeholder="e.g. ABCD-1234", key="join_group_code")
            if st.button("Join Group", use_container_width=True):
                if join_code.strip():
                    g_name_joined, error = join_study_group(join_code, user_id)
                    if error:
                        st.warning(error)
                    else:
                        st.success(f"Successfully joined: {g_name_joined}!")
                        st.rerun()
                else:
                    st.warning("Invite code is required.")

with col_left:
    if user_groups:
        group_options = {g["name"]: g for g in user_groups}
        selected_name = st.selectbox(
            "Select Workspace", 
            options=list(group_options.keys()),
            help="Switch between your active study groups."
        )
        selected_group = group_options[selected_name]
    else:
        st.info("You are not in any study groups yet. Create one or join with a code using the Options menu.")
        selected_group = None

if selected_group:
    group_id = selected_group["id"]
    st.markdown(f"### 📍 {selected_group['name']}")
    if selected_group["description"]:
        st.caption(f"*{selected_group['description']}*")
        
    st.markdown("---")
    
    # 3-Column layout
    workspace_col1, workspace_col2, workspace_col3 = st.columns([0.33, 0.38, 0.29])
    
    with workspace_col1:
        section_title("Invite Code", "key")
        with st.container(border=True):
            st.write("Share this code with your classmates:")
            st.markdown(f'<div class="code-badge">{selected_group["invite_code"]}</div>', unsafe_allow_html=True)
            st.caption("Double click to copy code. Anyone with this code can join and view your shared subjects.")
            
        section_title("Group Members", "users")
        members = get_group_members(group_id)
        with st.container(border=True):
            st.markdown(f"**Members count:** `{len(members)}`")
            for m in members:
                # Query recent completed Pomodoro sessions as a metric for activity
                with closing(get_connection()) as conn:
                    recent_study = conn.execute(
                        "SELECT completed_at FROM study_sessions WHERE user_id = ? ORDER BY completed_at DESC LIMIT 1",
                        (m["id"],)
                    ).fetchone()
                
                is_active = False
                if recent_study:
                    # If study session was completed in last 2 hours, show active co-study indicator
                    from datetime import datetime
                    try:
                        completed_time = datetime.strptime(recent_study[0], "%Y-%m-%d %H:%M:%S")
                        if (datetime.now() - completed_time).total_seconds() < 7200:
                            is_active = True
                    except Exception:
                        pass
                
                dot_html = '<span class="study-active-dot"></span>' if is_active else '<span class="study-inactive-dot"></span>'
                role_badge = f"`{m['role']}`" if m["role"] != "member" else ""
                st.markdown(f"{dot_html} **{html.escape(m['name'])}** {role_badge}", unsafe_allow_html=True)

    with workspace_col2:
        section_title("Shared Notes Library", "book")
        
        # Form to add a new shared subject
        with st.popover("📁 New Shared Subject", use_container_width=True):
            st.markdown("### Create Shared Subject")
            subj_name = st.text_input("Subject Name", placeholder="e.g. Physics Unit 2")
            subj_desc = st.text_area("Description", placeholder="Notes for AP Physics Unit 2")
            if st.button("Create Shared Subject", use_container_width=True):
                if subj_name.strip():
                    new_id = add_subject(subj_name, subj_desc, user_id=user_id, group_id=group_id)
                    if new_id:
                        st.success(f"Subject '{subj_name}' created!")
                        st.rerun()
                    else:
                        st.error("Error creating subject.")
                else:
                    st.warning("Subject name is required.")
        
        group_subjects = get_group_subjects(group_id)
        if group_subjects:
            for s in group_subjects:
                with st.expander(f"📁 {s['name']}", expanded=True):
                    docs = get_documents(subject_id=s["id"])
                    if docs:
                        for doc in docs:
                            doc_id = doc["id"]
                            st.write(f"📄 **{doc['file_name']}**")
                            # Add download/preview link
                            col_dl, col_prev = st.columns(2)
                            with col_dl:
                                file_path = Path(doc["file_path"])
                                if file_path.exists():
                                    with open(file_path, "rb") as f:
                                        st.download_button(
                                            "⬇ Download",
                                            data=f.read(),
                                            file_name=doc["file_name"],
                                            key=f"dl_{doc_id}"
                                        )
                            with col_prev:
                                # Simple preview option if preview is supported
                                if st.button("👁 Preview", key=f"prev_{doc_id}"):
                                    st.session_state.preview_document_id = doc_id
                                    st.info(f"Go to 'Study Library' page to preview document: {doc['file_name']}")
                    else:
                        st.caption("No notes uploaded to this shared subject. Go to 'Upload Notes' to add PDFs.")
        else:
            st.info("No shared subjects found. Create a subject using the button above.")

    with workspace_col3:
        section_title("Quiz Leaderboard", "award")
        leaderboard = get_group_leaderboard(group_id)
        
        with st.container(border=True):
            if leaderboard:
                st.write("Practice quiz high scores:")
                for idx, row in enumerate(leaderboard):
                    rank = idx + 1
                    rank_class = f"rank-{rank}" if rank <= 3 else "rank-other"
                    badge = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else f"#{rank}"
                    st.markdown(
                        f"""
                        <div style="display: flex; align-items: center; margin-bottom: 12px;">
                            <span class="leaderboard-rank {rank_class}">{badge}</span>
                            <div style="flex-grow: 1;">
                                <div style="font-weight: 700; color: #1e1b4b;">{html.escape(row['user_name'])}</div>
                                <div style="font-size: 0.75rem; color: #64748B;">{html.escape(row['subject_name'])}</div>
                            </div>
                            <div style="font-weight: 800; color: #8B5CF6; font-size: 1.1rem;">{int(row['max_score'])}%</div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
            else:
                st.caption("No quiz scores logged yet. Study shared notes, complete quizzes, and see your rank here!")
