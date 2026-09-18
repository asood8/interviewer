import streamlit as st

from interviewer.profile import load_profile

st.set_page_config(page_title="Interviewer", page_icon="🎤")

st.title("🎤 Interviewer")
st.write(
    "Mock interviews built around your own resume and projects. "
    "Claude asks the questions, you answer, and you get feedback on what to fix and what to study."
)

profile = load_profile()
if profile.is_empty():
    st.info("Start by filling in your **Profile**: resume, background, and projects.")
    st.page_link("pages/1_Profile.py", label="Go to Profile", icon="📝")
else:
    st.success(f"Profile loaded: {len(profile.named_projects())} project(s).")
    st.page_link("pages/2_Interview.py", label="Start practicing", icon="🎙️")
    st.page_link("pages/1_Profile.py", label="Edit profile", icon="📝")
