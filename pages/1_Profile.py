import streamlit as st

from interviewer.profile import Profile, Project, load_profile, save_profile

st.set_page_config(page_title="Profile · Interviewer", page_icon="📝")
st.title("📝 Profile")
st.caption("Everything here is saved automatically to `data/profile.json` (never committed to git).")

# The working copy lives in session state so edits survive switching pages.
if "profile" not in st.session_state:
    st.session_state.profile = load_profile()
p: Profile = st.session_state.profile

st.header("About you")
p.name = st.text_input("Name", value=p.name, key="name")
p.target_roles = st.text_input(
    "Target roles", value=p.target_roles, key="target_roles",
    placeholder="e.g. Software engineering intern, backend developer",
)
p.background = st.text_area(
    "Background", value=p.background, key="background", height=150,
    placeholder="Education, experience, what you're interested in, what you want next...",
)
p.resume_text = st.text_area(
    "Resume (paste the text)", value=p.resume_text, key="resume_text", height=300,
)
p.other = st.text_area(
    "Anything else an interviewer might ask about", value=p.other, key="other", height=100,
    placeholder="Clubs, hackathons, awards, hobbies, gaps, why you switched majors...",
)

st.header("Projects")
st.caption(
    "The more detail you add here, the more specific (and useful) the questions get. "
    "Notes can be messy: decisions you made, bugs you hit, numbers, anything you remember."
)

for proj in list(p.projects):
    with st.expander(proj.name or "New project", expanded=not proj.name):
        k = proj.id
        proj.name = st.text_input("Name", value=proj.name, key=f"{k}_name")
        proj.summary = st.text_area("What it is / what it does", value=proj.summary, key=f"{k}_summary")
        proj.tech_stack = st.text_input("Tech stack", value=proj.tech_stack, key=f"{k}_tech")
        c1, c2 = st.columns(2)
        proj.role = c1.text_input("Your role / team size", value=proj.role, key=f"{k}_role")
        proj.dates = c2.text_input("Dates", value=proj.dates, key=f"{k}_dates")
        proj.notes = st.text_area("Notes", value=proj.notes, key=f"{k}_notes", height=200)
        if st.button("Delete project", key=f"{k}_delete", type="tertiary"):
            p.projects.remove(proj)
            st.rerun()

if st.button("➕ Add project"):
    p.projects.append(Project())
    st.rerun()

if p != load_profile():
    save_profile(p)
    st.toast("Saved")
