from datetime import date

import streamlit as st

from interviewer.llm import LLMError
from interviewer.profile import Profile, Project
from interviewer.repo import RepoError, digest, is_url
from interviewer.resume import ResumeError, find_projects, pdf_to_text
from interviewer.ui import autosave, working_profile

st.set_page_config(page_title="Profile · Interviewer", page_icon="📝")
st.title("📝 Profile")
st.caption("Everything here is saved automatically to `data/profile.json` (never committed to git).")

p: Profile = working_profile()

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

st.subheader("Resume")
upload = st.file_uploader("Upload a PDF", type="pdf", key="resume_pdf")
if upload is not None and st.button("Read this PDF"):
    try:
        p.resume_text = pdf_to_text(upload.getvalue())
        st.session_state.pop("resume_text", None)  # let the box below pick up the new text
        st.rerun()
    except ResumeError as e:
        st.error(str(e))

p.resume_text = st.text_area(
    "Resume text (edit anything the PDF got wrong)", value=p.resume_text, key="resume_text", height=300,
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

        proj.repo = st.text_input(
            "Repo (GitHub URL or a folder on this computer)", value=proj.repo, key=f"{k}_repo",
            help="Claude reads the README and the main source files, so it can ask about your actual code.",
        )
        c1, c2 = st.columns(2)
        if proj.repo.strip() and c1.button("Read the code", key=f"{k}_read"):
            spinner = "Cloning and reading the repo..." if is_url(proj.repo) else "Reading the repo..."
            with st.spinner(spinner):
                try:
                    proj.code = digest(proj.repo, proj.id)
                    proj.code_updated = date.today().isoformat()
                    st.rerun()
                except RepoError as e:
                    st.error(str(e))
        if proj.code:
            c2.caption(f"{len(proj.code):,} characters of code read on {proj.code_updated}")
            if c2.button("Forget the code", key=f"{k}_forget"):
                proj.code = proj.code_updated = ""
                st.rerun()

        if proj.dossier and not proj.dossier.is_empty():
            st.page_link("pages/2_Project_prep.py", label="Prep notes written · edit them", icon="🗂️")
        elif proj.name:
            st.page_link("pages/2_Project_prep.py", label="Write prep notes for this project", icon="🗂️")
        if st.button("Delete project", key=f"{k}_delete", type="tertiary"):
            p.projects.remove(proj)
            st.rerun()

c1, c2 = st.columns(2)
if c1.button("➕ Add project"):
    p.projects.append(Project())
    st.rerun()
if p.resume_text.strip() and c2.button("🔍 Find projects in my resume"):
    with st.spinner("Reading your resume..."):
        try:
            st.session_state.found_projects = find_projects(p, [pr.name for pr in p.named_projects()])
        except LLMError as e:
            st.error(str(e))

found = st.session_state.get("found_projects")
if found:
    st.subheader("Found in your resume")
    st.caption("Tick the ones to add, then fill in the details above.")
    for i, candidate in enumerate(found):
        st.checkbox(f"**{candidate.name}** — {candidate.summary}", key=f"found_{i}")
    if st.button("Add selected", type="primary"):
        p.projects += [c for i, c in enumerate(found) if st.session_state.get(f"found_{i}")]
        for i in range(len(found)):
            st.session_state.pop(f"found_{i}", None)
        st.session_state.found_projects = None
        st.rerun()
elif found is not None and "found_projects" in st.session_state:
    st.info("No new projects found in your resume.")

autosave(p)
