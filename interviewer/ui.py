"""Streamlit display helpers for answers, delivery, and feedback."""

import hashlib
from statistics import mean

import streamlit as st

from interviewer.delivery import Delivery, analyze
from interviewer.feedback import Feedback, Scores
from interviewer.profile import Profile, load_profile, save_profile
from interviewer.session import Attempt
from interviewer.speech import transcribe


def bullets(items: list[str]) -> None:
    st.markdown("\n".join(f"- {item}" for item in items))


def show_delivery(d: Delivery) -> None:
    c1, c2, c3, c4 = st.columns(4)
    seconds = round(d.duration)
    c1.metric("Length", f"{seconds // 60}:{seconds % 60:02d}")
    c2.metric("Pace", f"{d.wpm:.0f} wpm")
    c3.metric("Ums / uhs", sum(d.hesitations.values()))
    c4.metric("Long pauses", len(d.long_pauses))
    bullets(d.notes() or ["Delivery looked good: steady pace, few fillers, no long pauses."])
    details = []
    if d.crutches:
        details.append("Crutch words: " + ", ".join(f'"{w}" x{n}' for w, n in d.crutches.most_common()))
    for p in d.long_pauses:
        details.append(f'Paused {p.seconds:.1f}s after "...{p.after}"')
    if d.thinking_time >= 2:
        details.append(f"{d.thinking_time:.0f}s of thinking before you started (that's fine)")
    if details:
        st.caption(" · ".join(details))


def show_scores(scores: dict[str, float]) -> None:
    for col, (name, score) in zip(st.columns(len(scores)), scores.items()):
        col.metric(name.capitalize(), f"{round(score, 1):g}/5")


def average_scores(feedback: list[Feedback]) -> dict[str, float]:
    return {name: mean(getattr(fb.scores, name) for fb in feedback) for name in Scores.model_fields}


def show_feedback(fb: Feedback) -> None:
    st.write(fb.summary)
    show_scores(fb.scores.model_dump())
    sections = [
        ("✅ What worked", fb.strengths),
        ("🔧 What to improve", fb.improvements),
        ("⚠️ Technical issues", fb.technical_issues),
        ("🕳️ Missed points", fb.missed_points),
    ]
    for title, items in sections:
        if items:
            st.markdown(f"**{title}**")
            bullets(items)
    st.markdown("**💬 A stronger version**")
    st.info(fb.stronger_answer)
    if fb.review_topics:
        st.markdown("**📚 Review before your next interview**")
        bullets(fb.review_topics)


def show_attempt(a: Attempt, label: str) -> None:
    st.markdown(f"**{label}**")
    if a.audio:
        st.audio(a.audio, format="audio/wav")
    st.write(a.answer)
    if a.delivery:
        st.markdown("#### Delivery")
        show_delivery(a.delivery)
    if a.feedback:
        st.markdown("#### Content")
        show_feedback(a.feedback)


def working_profile() -> Profile:
    """One shared, editable copy of the profile per browser session, so pages don't clobber each other."""
    if "profile" not in st.session_state:
        st.session_state.profile = load_profile()
    return st.session_state.profile


def autosave(profile: Profile) -> None:
    if profile != load_profile():
        save_profile(profile)
        st.toast("Saved")


def answer_input(
    profile: Profile, key: str, speak: bool, label: str = "Your answer", submit_label: str = "Submit answer"
) -> tuple[str, Delivery | None, bytes | None] | None:
    """The answer box: mic or keyboard. Returns (answer, delivery, audio) once submitted, else None."""
    state = st.session_state
    if not speak:
        answer = st.text_area(label, key=f"answer_{key}", height=250)
        if st.button(submit_label, type="primary"):
            if answer.strip():
                return answer, None, None
            st.warning("There's nothing to submit yet.")
        return None

    audio = st.audio_input("Record your answer", key=f"audio_{key}")
    if audio is None:
        st.caption("Press the mic, answer out loud like you would in the real interview, then press stop.")
        return None

    data = audio.getvalue()
    digest = hashlib.sha1(data).hexdigest()
    if state.get("transcript_digest") != digest:
        with st.spinner("Transcribing... (the first time also downloads the speech model, which takes a minute)"):
            try:
                state.transcript = transcribe(data, profile)
            except Exception as e:
                st.error(f"Transcription failed: {e}")
                return None
        state.transcript_digest = digest

    transcript = state.transcript
    if not transcript.words:
        st.warning("Didn't catch any speech in that recording. Check your mic and record again.")
        return None

    answer = st.text_area(
        "Transcript (fix any misheard words, then submit)",
        value=transcript.text,
        key=f"transcript_{digest[:12]}",
        height=200,
    )
    if st.button(submit_label, type="primary"):
        if answer.strip():
            return answer, analyze(transcript), data
        st.warning("There's nothing to submit yet.")
    return None
