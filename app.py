import streamlit as st

from interviewer.ui import working_profile

st.set_page_config(page_title="Interviewer", page_icon="🎤")

st.title("🎤 Interviewer")
st.write(
    "Mock interviews built around your own resume and projects. "
    "Claude asks the questions, you answer out loud, and you get feedback on what to fix and what to study."
)

profile = working_profile()
if profile.is_empty():
    st.info("Start by filling in your **Profile**: resume, background, and projects.")
    st.page_link("pages/1_Profile.py", label="Go to Profile", icon="📝")
else:
    projects = profile.named_projects()
    prepped = [p for p in projects if p.dossier and not p.dossier.is_empty()]
    st.success(f"Profile loaded: {len(projects)} project(s), {len(prepped)} with prep notes.")
    st.page_link("pages/3_Interview.py", label="Start practicing", icon="🎙️")
    if len(prepped) < len(projects):
        st.page_link("pages/2_Project_prep.py", label="Write prep notes for a project", icon="🗂️")
    st.page_link("pages/5_Review.py", label="What to review, weak spots, answer bank", icon="📚")
    st.page_link("pages/4_History.py", label="Past sessions and progress", icon="📈")
    st.page_link("pages/1_Profile.py", label="Edit profile", icon="📝")
