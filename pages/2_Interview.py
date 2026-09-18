import streamlit as st

from interviewer.feedback import Feedback, evaluate
from interviewer.llm import LLMError
from interviewer.profile import load_profile
from interviewer.questions import DEPTHS, QUESTION_TYPES, Question, generate_question, pick_project, pick_type

st.set_page_config(page_title="Interview · Interviewer", page_icon="🎙️")
st.title("🎙️ Interview")

profile = load_profile()
if profile.is_empty():
    st.warning("Your profile is empty. Add your resume and projects first.")
    st.page_link("pages/1_Profile.py", label="Go to Profile", icon="📝")
    st.stop()

state = st.session_state
state.setdefault("asked", [])  # every question asked this session, for variety
state.setdefault("question", None)  # the current Question
state.setdefault("attempts", [])  # (answer, Feedback) pairs for the current question

# --- Settings ---------------------------------------------------------------

projects = profile.named_projects()
with st.sidebar:
    st.header("Question settings")
    type_key = st.selectbox(
        "Type",
        ["mixed", *QUESTION_TYPES],
        format_func=lambda k: "Mixed (random)" if k == "mixed" else QUESTION_TYPES[k].label,
    )
    about_project = type_key == "mixed" or QUESTION_TYPES[type_key].about_project
    project_name = st.selectbox(
        "Project",
        ["any", *(p.name for p in projects)],
        format_func=lambda n: "Rotate through all" if n == "any" else n,
        disabled=not about_project or not projects,
    )
    depth = st.radio(
        "Depth",
        list(DEPTHS),
        format_func={"any": "Any", "high": "High level", "low": "Low level"}.get,
        horizontal=True,
        disabled=not about_project,
    )
    st.caption(f"{len(state.asked)} question(s) asked this session.")


def new_question() -> bool:
    chosen_type = pick_type(profile) if type_key == "mixed" else type_key
    project = None
    if QUESTION_TYPES[chosen_type].about_project:
        if not projects:
            st.error("Add at least one project to your profile for project questions.")
            return False
        if project_name == "any":
            project = pick_project(profile, state.asked)
        else:
            project = next(p for p in projects if p.name == project_name)
    with st.spinner("Thinking of a question..."):
        try:
            q = generate_question(profile, chosen_type, project, depth, state.asked)
        except LLMError as e:
            st.error(str(e))
            return False
    state.question = q
    state.asked.append(q)
    state.attempts = []
    state.retrying = False
    return True


if st.button("New question" if state.question else "Start", type="primary"):
    new_question()

q: Question | None = state.question
if q is None:
    st.info("Pick a question type in the sidebar (or leave it on Mixed), then press **Start**.")
    st.stop()

# --- Question ---------------------------------------------------------------

label = QUESTION_TYPES[q.type_key].label
if q.project_name:
    label += f" · {q.project_name}"
st.caption(label)
st.markdown(f"### {q.text}")

# --- Feedback ---------------------------------------------------------------


def show_feedback(fb: Feedback) -> None:
    st.write(fb.summary)
    scores = fb.scores.model_dump()
    for col, (name, score) in zip(st.columns(len(scores)), scores.items()):
        col.metric(name.capitalize(), f"{score}/5")

    sections = [
        ("✅ What worked", fb.strengths),
        ("🔧 What to improve", fb.improvements),
        ("⚠️ Technical issues", fb.technical_issues),
        ("🕳️ Missed points", fb.missed_points),
    ]
    for title, items in sections:
        if items:
            st.markdown(f"**{title}**")
            st.markdown("\n".join(f"- {item}" for item in items))

    st.markdown("**💬 A stronger version**")
    st.info(fb.stronger_answer)

    if fb.review_topics:
        st.markdown("**📚 Review before your next interview**")
        st.markdown("\n".join(f"- {t}" for t in fb.review_topics))


# Earlier attempts at this question, most recent first.
for i, (answer, fb) in reversed(list(enumerate(state.attempts[:-1]))):
    with st.expander(f"Attempt {i + 1} · your answer and feedback"):
        st.markdown("**Your answer**")
        st.write(answer)
        show_feedback(fb)

if state.attempts:
    answer, fb = state.attempts[-1]
    st.markdown(f"**Your answer** (attempt {len(state.attempts)})")
    st.write(answer)
    st.divider()
    show_feedback(fb)
    with st.expander("What a strong answer covers"):
        st.markdown("\n".join(f"- {c}" for c in q.strong_answer_covers))
    st.divider()
    c1, c2 = st.columns(2)
    if c1.button("🔁 Try this question again", width="stretch"):
        state.retrying = True
        st.rerun()
    if c2.button("➡️ Next question", width="stretch") and new_question():
        st.rerun()

# --- Answer -----------------------------------------------------------------

if not state.attempts or state.get("retrying"):
    # A fresh key per attempt clears the text box on retry and on new questions.
    answer_key = f"answer_{len(state.asked)}_{len(state.attempts)}"
    answer = st.text_area("Your answer", key=answer_key, height=250)
    if st.button("Submit answer"):
        if not answer.strip():
            st.warning("Write an answer first.")
            st.stop()
        with st.spinner("Reviewing your answer..."):
            try:
                fb = evaluate(profile, q, answer)
            except LLMError as e:
                st.error(str(e))
                st.stop()
        state.attempts.append((answer, fb))
        state.retrying = False
        st.rerun()
