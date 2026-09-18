import hashlib
from dataclasses import dataclass

import streamlit as st

from interviewer.delivery import Delivery, analyze
from interviewer.feedback import Feedback, evaluate
from interviewer.llm import LLMError
from interviewer.profile import load_profile
from interviewer.questions import DEPTHS, QUESTION_TYPES, Question, generate_question, pick_project, pick_type
from interviewer.speech import transcribe

st.set_page_config(page_title="Interview · Interviewer", page_icon="🎙️")
st.title("🎙️ Interview")

profile = load_profile()
if profile.is_empty():
    st.warning("Your profile is empty. Add your resume and projects first.")
    st.page_link("pages/1_Profile.py", label="Go to Profile", icon="📝")
    st.stop()



@dataclass
class Attempt:
    answer: str
    feedback: Feedback
    delivery: Delivery | None = None  # only for spoken answers
    audio: bytes | None = None


state = st.session_state
state.setdefault("asked", [])  # every question asked this session, for variety
state.setdefault("question", None)  # the current Question
state.setdefault("attempts", [])  # Attempts at the current question

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
    speak = st.radio("Answer by", ["Speaking", "Typing"], horizontal=True) == "Speaking"
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


def show_delivery(d: Delivery) -> None:
    c1, c2, c3, c4 = st.columns(4)
    seconds = round(d.duration)
    c1.metric("Length", f"{seconds // 60}:{seconds % 60:02d}")
    c2.metric("Pace", f"{d.wpm:.0f} wpm")
    c3.metric("Ums / uhs", sum(d.hesitations.values()))
    c4.metric("Long pauses", len(d.long_pauses))
    notes = d.notes()
    if notes:
        st.markdown("\n".join(f"- {n}" for n in notes))
    else:
        st.markdown("- Delivery looked good: steady pace, few fillers, no long pauses.")
    details = []
    if d.crutches:
        details.append("Crutch words: " + ", ".join(f'"{w}" x{n}' for w, n in d.crutches.most_common()))
    for p in d.long_pauses:
        details.append(f'Paused {p.seconds:.1f}s after "...{p.after}"')
    if d.thinking_time >= 2:
        details.append(f"{d.thinking_time:.0f}s of thinking before you started (that's fine)")
    if details:
        st.caption(" · ".join(details))


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


def show_attempt(a: Attempt, number: int) -> None:
    st.markdown(f"**Your answer** (attempt {number})")
    if a.audio:
        st.audio(a.audio, format="audio/wav")
    st.write(a.answer)
    if a.delivery:
        st.markdown("#### Delivery")
        show_delivery(a.delivery)
    st.markdown("#### Content")
    show_feedback(a.feedback)


# Earlier attempts at this question, most recent first.
for i, a in reversed(list(enumerate(state.attempts[:-1]))):
    with st.expander(f"Attempt {i + 1}"):
        show_attempt(a, i + 1)

if state.attempts:
    show_attempt(state.attempts[-1], len(state.attempts))
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


def submit(answer: str, delivery: Delivery | None = None, audio: bytes | None = None) -> None:
    if not answer.strip():
        st.warning("There's no answer to submit yet.")
        return
    with st.spinner("Reviewing your answer..."):
        try:
            fb = evaluate(profile, q, answer, delivery)
        except LLMError as e:
            st.error(str(e))
            return
    state.attempts.append(Attempt(answer, fb, delivery, audio))
    state.retrying = False
    st.rerun()


if not state.attempts or state.get("retrying"):
    # A fresh key per attempt clears the inputs on retry and on new questions.
    attempt_key = f"{len(state.asked)}_{len(state.attempts)}"

    if not speak:
        answer = st.text_area("Your answer", key=f"answer_{attempt_key}", height=250)
        if st.button("Submit answer"):
            submit(answer)
        st.stop()

    audio = st.audio_input("Record your answer", key=f"audio_{attempt_key}")
    if audio is None:
        st.caption("Press the mic, answer out loud like you would in the real interview, then press stop.")
        st.stop()

    data = audio.getvalue()
    digest = hashlib.sha1(data).hexdigest()
    if state.get("transcript_digest") != digest:
        with st.spinner("Transcribing... (the first time also downloads the speech model, which takes a minute)"):
            try:
                state.transcript = transcribe(data, profile)
            except Exception as e:
                st.error(f"Transcription failed: {e}")
                st.stop()
        state.transcript_digest = digest

    transcript = state.transcript
    if not transcript.words:
        st.warning("Didn't catch any speech in that recording. Check your mic and record again.")
        st.stop()

    answer = st.text_area(
        "Transcript (fix any misheard words, then submit)",
        value=transcript.text,
        key=f"transcript_{digest[:12]}",
        height=200,
    )
    if st.button("Submit answer", type="primary"):
        submit(answer, analyze(transcript), data)
