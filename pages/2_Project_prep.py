import streamlit as st

from interviewer.dossier import MAX_QUESTIONS, next_question, write_dossier
from interviewer.llm import LLMError
from interviewer.profile import DOSSIER_LISTS, DOSSIER_SECTIONS
from interviewer.ui import answer_input, autosave, working_profile

st.set_page_config(page_title="Project prep · Interviewer", page_icon="🗂️")
st.title("🗂️ Project prep")
st.caption(
    "Before you can explain a project well, the facts have to be organized. Claude asks you about one "
    "project, then writes it up: the problem, how it's built, your decisions, the hardest bug, the numbers, "
    "and what you should be able to explain. Interview questions are then grounded in these notes."
)

profile = working_profile()
projects = profile.named_projects()
if not projects:
    st.warning("Add a project to your profile first.")
    st.page_link("pages/1_Profile.py", label="Go to Profile", icon="📝")
    st.stop()

state = st.session_state
state.setdefault("prep", None)  # {"project_id", "transcript", "question"} while building
prep = state.prep

names = [p.name for p in projects]
locked = next((p for p in projects if prep and p.id == prep["project_id"]), None)
if locked:
    project = locked
    st.selectbox("Project", names, index=names.index(project.name), disabled=True)
else:
    project = projects[names.index(st.selectbox("Project", names))]

with st.sidebar:
    speak = st.radio("Answer by", ["Speaking", "Typing"], horizontal=True) == "Speaking"


def run(action, spinner: str):
    """Run a Claude-backed action with a spinner. Shows the error and returns None if it fails."""
    with st.spinner(spinner):
        try:
            return action(), True
        except LLMError as e:
            st.error(str(e))
            return None, False


def clear_edits() -> None:
    """Drop the editor's widget state, so it doesn't overwrite a freshly written dossier."""
    for key in [*DOSSIER_SECTIONS, *DOSSIER_LISTS]:
        st.session_state.pop(f"{project.id}_{key}", None)


def start(fresh: bool) -> None:
    if fresh:
        project.dossier = None
        clear_edits()
    result, ok = run(lambda: next_question(profile, project, []), "Thinking of the first question...")
    if ok:
        state.prep = {"project_id": project.id, "transcript": [], "question": result}
        st.rerun()


def finish(transcript: list[tuple[str, str]]) -> None:
    dossier, ok = run(lambda: write_dossier(profile, project, transcript), "Writing up the dossier...")
    if ok:
        project.dossier = dossier
        clear_edits()
        autosave(profile)
        state.prep = None
        st.rerun()


# --- Building ---------------------------------------------------------------

if prep:
    transcript: list[tuple[str, str]] = prep["transcript"]
    question = prep["question"]

    if transcript:
        with st.expander(f"{len(transcript)} answer(s) so far"):
            for q, a in transcript:
                st.markdown(f"**{q}**")
                st.write(a)

    if question is None:
        finish(transcript)
        st.stop()

    st.caption(f"Question {len(transcript) + 1} of up to {MAX_QUESTIONS} · not graded, just gathering facts")
    st.markdown(f"### {question}")

    if result := answer_input(profile, f"prep_{project.id}_{len(transcript)}", speak, submit_label="Next"):
        transcript.append((question, result[0]))
        nxt, ok = run(lambda: next_question(profile, project, transcript), "Thinking...")
        if ok:
            prep["question"] = nxt
            st.rerun()

    c1, c2 = st.columns(2)
    if c1.button("Skip this question", width="stretch"):
        transcript.append((question, "(skipped)"))
        nxt, ok = run(lambda: next_question(profile, project, transcript), "Thinking...")
        if ok:
            prep["question"] = nxt
            st.rerun()
    if c2.button("Write it up now", width="stretch"):
        finish(transcript)
    st.stop()

# --- The dossier ------------------------------------------------------------

dossier = project.dossier
if dossier is None or dossier.is_empty():
    st.info(f"No notes for **{project.name}** yet. Expect about {MAX_QUESTIONS} questions, 10-15 minutes.")
    if st.button("Start", type="primary"):
        start(fresh=True)
    st.stop()

st.caption("Edit anything that's wrong or missing. Changes save automatically.")
for key, label in DOSSIER_SECTIONS.items():
    setattr(dossier, key, st.text_area(label, value=getattr(dossier, key), key=f"{project.id}_{key}", height=140))
for key, label in DOSSIER_LISTS.items():
    text = st.text_area(
        label, value="\n".join(getattr(dossier, key)), key=f"{project.id}_{key}", height=120,
        help="One per line.",
    )
    setattr(dossier, key, [line.strip() for line in text.splitlines() if line.strip()])

c1, c2, c3 = st.columns(3)
if c1.button("Add more detail", type="primary", width="stretch"):
    start(fresh=False)
if c2.button("Rebuild from scratch", width="stretch"):
    start(fresh=True)
if c3.button("Delete notes", width="stretch"):
    project.dossier = None
    clear_edits()
    autosave(profile)
    st.rerun()

autosave(profile)
