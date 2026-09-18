"""Streamlit display helpers for answers, delivery, and feedback."""

from statistics import mean

import streamlit as st

from interviewer.delivery import Delivery
from interviewer.feedback import Feedback, Scores
from interviewer.session import Attempt


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
