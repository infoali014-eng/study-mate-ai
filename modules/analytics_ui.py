"""
Reusable Analytics UI Components for StudyMate AI (Phase 5D).
Stateless rendering helpers for charts, KPI blocks, timelines, achievements progress, and exports.
"""

import streamlit as st
import pandas as pd
import html as _html
from modules.components.stat_card import render_stat_card
from modules.ui import section_title
from modules.icons import icon

def render_filters(subjects: list) -> tuple:
    """Render Subject and Date Range filters side-by-side."""
    col1, col2 = st.columns(2)
    with col1:
        subject_names = ["All Subjects"] + [s["name"] for s in subjects]
        selected_sub_name = st.selectbox("Subject Filter", subject_names)
        
        # Resolve subject_id
        selected_sub_id = None
        if selected_sub_name != "All Subjects":
            for s in subjects:
                if s["name"] == selected_sub_name:
                    selected_sub_id = s["id"]
                    break
    with col2:
        date_ranges = ["All Time", "Today", "Last 7 Days", "Last 30 Days", "Last 90 Days"]
        selected_range = st.selectbox("Date Range", date_ranges)
        
    return selected_sub_id, selected_range

def render_overview_cards(data: dict):
    """Render 8 SaaS-style KPI metric cards."""
    section_title("Overview Statistics", "bar-chart-2")
    ov = data["overview"]
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        render_stat_card("Total Study Time", f"{ov['study_time_hours']} hrs", "Sessional totals", "clock", "#14B8A6", "#F0FDFA")
    with col2:
        render_stat_card("Total Subjects", ov["total_subjects"], "Organized categories", "book", "#2563EB", "#EFF6FF")
    with col3:
        render_stat_card("Notes Uploaded", ov["notes_uploaded"], "Study materials", "upload-cloud", "#EA580C", "#FFF7ED")
    with col4:
        render_stat_card("Processed Documents", ov["documents_processed"], "Compiled library vector index", "file-text", "#8B5CF6", "#F5F3FF")

    st.write("")
    col5, col6, col7, col8 = st.columns(4)
    with col5:
        render_stat_card("AI Chats", ov["ai_chats"], "Conversational sessions", "message-circle", "#16A34A", "#F0FDF4")
    with col6:
        render_stat_card("Flashcards", ov["flashcards"], "Spaced repetition cards", "layers", "#F59E0B", "#FFFBEB")
    with col7:
        render_stat_card("Quiz Attempts", ov["quiz_attempts"], "Evaluations completed", "help-circle", "#EF4444", "#FEF2F2")
    with col8:
        render_stat_card("Revision Tasks", ov["revision_plans"], "Planner goals", "calendar", "#0F9D8C", "#E6F4F1")

def render_goals_and_insights(data: dict):
    """Render study goals progress alongside quick insights."""
    col1, col2 = st.columns([1, 1])
    
    with col1:
        section_title("Today's Goals & Progress", "target")
        g = data["goals"]
        
        # Today's Progress Bar
        st.markdown(f"**Today's Focus Goal** ({g['today_hours']} / {g['today_goal']} hrs)")
        st.progress(g["today_pct"] / 100.0)
        st.caption(f"Progress: {g['today_pct']}% of daily target")
        
        st.write("")
        # Weekly Progress Bar
        st.markdown(f"**Weekly Commitment Goal** ({g['week_hours']} / {g['week_goal']} hrs)")
        st.progress(g["week_pct"] / 100.0)
        st.caption(f"Progress: {g['week_pct']}% of weekly target")

    with col2:
        section_title("Quick Insights", "zap")
        ins = data["insights"]
        
        # Format insights as a premium list
        st.markdown(
            f"""
            <div class="sm-progress-card" style="padding: 16px; border-radius: var(--radius-lg); background: var(--color-surface); border: 1px solid var(--color-border);">
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; font-size: 0.8125rem;">
                    <div><strong>Today's Focus:</strong><br><span style="color:var(--color-primary-dark); font-weight:600;">{ins['today_focus']}</span></div>
                    <div><strong>Need Revision:</strong><br><span style="color:#EF4444; font-weight:600;">{ins['need_revision']}</span></div>
                    <div><strong>Best Subject:</strong><br><span style="color:#16A34A; font-weight:600;">{ins['best_subject']}</span></div>
                    <div><strong>Weakest Subject:</strong><br><span style="color:#EA580C; font-weight:600;">{ins['weakest_subject']}</span></div>
                    <div><strong>Upcoming Task:</strong><br><span>{ins['upcoming_deadline']}</span></div>
                    <div><strong>Longest Session:</strong><br><span>{ins['longest_session_mins']} mins</span></div>
                    <div><strong>Avg Quiz Score:</strong><br><span>{ins['average_quiz_score']}%</span></div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

def render_charts(data: dict):
    """Render interactive charts for Daily/Weekly study hours."""
    col1, col2 = st.columns([1, 1])
    
    with col1:
        section_title("Study Activity (Daily)", "bar-chart-2")
        daily_data = data["activity"]["daily"]
        if daily_data:
            df = pd.DataFrame(daily_data)
            st.bar_chart(df.set_index("Date"), color="#14B8A6")
        else:
            st.info("No study sessions logged for the selected dates.")

    with col2:
        section_title("Learning Progress", "trending-up")
        prog = data["progress"]
        
        col_acc, col_ret, col_prod = st.columns(3)
        with col_acc:
            render_stat_card("Planner Completion", f"{prog['completion_percentage']}%", "Planner items completed", "calendar", "#0F9D8C", "#E6F4F1")
        with col_ret:
            render_stat_card("Study Streak", f"{prog['study_streak']} days", "Consecutive days active", "flame", "#EA580C", "#FFF7ED")
        with col_prod:
            render_stat_card("Productivity Score", f"{prog['productivity_score']}%", "Composite engagement level", "zap", "#9333EA", "#F5F3FF")

def render_performance_metrics(data: dict):
    """Render quiz accuracy, flashcard retention, and subject tables."""
    col1, col2 = st.columns([1, 1])
    
    with col1:
        section_title("Performance & Weak Topics", "target")
        perf = data["performance"]
        
        st.write(f"**Overall Quiz Accuracy:** {perf['quiz_accuracy']}%")
        st.write(f"**Flashcard Retention Score:** {perf['flashcard_retention']}%")
        
        st.write("")
        st.markdown("**Weak Topics Logged**")
        wt_list = perf["weak_topics"]
        if not wt_list:
            st.success("No weak topics tracked yet! Keep up the good work.")
        else:
            for wt in wt_list[:5]:
                st.markdown(
                    f"- **{_html.escape(wt['topic'])}** ({wt['subject_name']}) - "
                    f"Accuracy: {wt['correct']}/{wt['attempts']} answers "
                    f"| Trend: `{wt['trend']}`"
                )

    with col2:
        section_title("Subject Statistics", "book")
        sub_list = data["subjects"]["list"]
        if not sub_list:
            st.info("No subjects found.")
        else:
            df = pd.DataFrame(sub_list)
            st.dataframe(df, use_container_width=True, hide_index=True)

def render_ai_recommendations(data: dict, on_action_callback):
    """Render AI priority recommendation cards with Action keys."""
    col1, col2 = st.columns([1, 1])
    
    with col1:
        section_title("AI Study Recommendations", "lightbulb")
        recs = data["recommendations"]
        
        if not recs:
            st.info("No AI recommendations right now. Study more or hit refresh to recalculate.")
        else:
            for r in recs:
                rec_id = r["id"]
                priority_color = "#EF4444" if r["priority"] == "High" else ("#F59E0B" if r["priority"] == "Medium" else "#6b7280")
                
                # Render clean styled card
                with st.container(border=True):
                    st.markdown(
                        f"""
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <span style="font-weight:600; color:{priority_color}; font-size:0.75rem; text-transform:uppercase; letter-spacing:0.04em;">
                                {r['priority']} Priority | {int(float(r.get('confidence', 1.0)) * 100)}% Confidence
                            </span>
                        </div>
                        <div style="font-weight:600; font-size:0.875rem; margin-top:4px;">{_html.escape(r['recommendation'])}</div>
                        <div style="font-size:0.8125rem; color:var(--color-text-secondary); margin-top:2px;">{_html.escape(r['reason'])}</div>
                        """,
                        unsafe_allow_html=True
                    )
                    
                    # Renders actions inside container
                    col_pin, col_dismiss = st.columns(2)
                    with col_pin:
                        # Check if already pinned in local session state
                        is_pinned = rec_id in st.session_state.get("pinned_recs", [])
                        label = "📌 Pinned" if is_pinned else "📌 Pin"
                        if st.button(label, key=f"pin_rec_{rec_id}", use_container_width=True):
                            on_action_callback("pin", rec_id)
                    with col_dismiss:
                        if st.button("Dismiss", key=f"dismiss_rec_{rec_id}", use_container_width=True):
                            on_action_callback("dismiss", rec_id)
                            
        st.write("")
        if st.button("Refresh AI Insights", type="primary", use_container_width=True):
            on_action_callback("refresh", None)

    with col2:
        section_title("Achievements & Milestones", "award")
        ach_list = data["achievements"]
        if not ach_list:
            st.info("No achievement milestones available.")
        else:
            for ach in ach_list:
                status = "🏆 Unlocked" if ach["unlocked"] else "🔒 Locked"
                st.markdown(
                    f"""
                    <div class="sm-progress-card" style="padding: 10px; margin-bottom: 8px; border-radius: var(--radius-md); background: var(--color-surface); border: 1px solid var(--color-border);">
                        <div style="display:flex; justify-content:space-between; font-size:0.8125rem; font-weight:600;">
                            <span>{_html.escape(ach['title'])}</span>
                            <span style="color:var(--color-primary-dark);">{status}</span>
                        </div>
                        <div style="font-size:0.75rem; color:var(--color-text-secondary); margin-bottom:4px;">{ach['metric']}: {ach['current']} / {ach['target']}</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                st.progress(ach["percentage"] / 100.0)

def render_timeline(data: dict):
    """Render smart formatted sessional activity logs."""
    section_title("Recent Activity Timeline", "clock")
    timeline = data["timeline"]
    
    if not timeline:
        st.info("No recent study activity recorded in this range.")
    else:
        for idx, item in enumerate(timeline[:10]):
            icon_char = "❓" if "Quiz" in item["activity"] else ("📄" if "notes" in item["activity"] else "⏱️")
            st.markdown(
                f"""
                <div style="display:flex; align-items:center; gap:12px; padding:8px 0; border-bottom:1px solid var(--color-border);">
                    <div style="font-size:0.75rem; color:var(--color-text-secondary); min-width:85px; flex-shrink:0;">{item['time']}</div>
                    <div style="font-size:1.1rem; flex-shrink:0;">{icon_char}</div>
                    <div style="font-size:0.875rem; color:var(--color-text); font-weight:500;">{_html.escape(item['activity'])}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

def render_exports(data: dict):
    """Render PDF & CSV export capabilities."""
    st.divider()
    section_title("Export Reports", "download")
    
    col1, col2 = st.columns(2)
    with col1:
        # Generate CSV representation of Subject Statistics
        sub_list = data["subjects"]["list"]
        if sub_list:
            df = pd.DataFrame(sub_list)
            csv_data = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Export Statistics to CSV",
                data=csv_data,
                file_name="studymate_subject_statistics.csv",
                mime="text/csv",
                use_container_width=True
            )
        else:
            st.button("Export Statistics to CSV (Empty)", disabled=True, use_container_width=True)
            
    with col2:
        # Renders a printable styled HTML document container which the user can save as PDF
        pdf_html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: sans-serif; padding: 20px; color: #333; }}
                h1 {{ color: #0F9D8C; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <h1>StudyMate AI - Learning Report</h1>
            <p><strong>Generated At:</strong> {date.today().isoformat()}</p>
            <h3>Overview Metrics</h3>
            <ul>
                <li>Total Study Time: {data['overview']['study_time_hours']} hours</li>
                <li>Quiz Attempts: {data['overview']['quiz_attempts']}</li>
                <li>Revision Plans: {data['overview']['revision_plans']}</li>
            </ul>
        </body>
        </html>
        """
        st.download_button(
            label="📥 Export Study Report to PDF",
            data=pdf_html,
            file_name="studymate_learning_report.html", # HTML page can be printed/saved as PDF in browser
            mime="text/html",
            use_container_width=True
        )
