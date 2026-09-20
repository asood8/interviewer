import streamlit as st

from interviewer.questions import QUESTION_TYPES
from interviewer.session import REVIEW_QUESTIONS
from interviewer.storage import (
    delete_saved_answer,
    list_saved_answers,
    list_topics,
    set_topic_done,
    weak_spots,
)

st.set_page_config(page_title="Review · Interviewer", page_icon="📚")
st.title("📚 Review")

topics = list_topics()
weak = weak_spots()
answers = list_saved_answers()

to_review, done = [t for t in topics if not t.done], [t for t in topics if t.done]
tabs = st.tabs([f"To review ({len(to_review)})", f"Weak spots ({len(weak)})", f"Answer bank ({len(answers)})"])

with tabs[0]:
    st.caption("Everything Claude told you to study, collected from your sessions. Repeats float to the top.")
    if not topics:
        st.info("Nothing here yet. Finish a session and the things to review collect here.")
    for topic in to_review:
        seen = f" · came up in {topic.times_seen} sessions" if topic.times_seen > 1 else ""
        if st.checkbox(f"{topic.text}{seen}", key=f"topic_{topic.key}"):
            set_topic_done(topic.key, True)
            st.rerun()
    if done:
        with st.expander(f"Done ({len(done)})"):
            for topic in done:
                if not st.checkbox(topic.text, value=True, key=f"done_{topic.key}"):
                    set_topic_done(topic.key, False)
                    st.rerun()

with tabs[1]:
    st.caption("The questions your answers scored lowest on, worst first. Only your latest attempt counts.")
    if not weak:
        st.info("No weak spots. Either you haven't finished a session yet, or your answers all scored well.")
    else:
        st.page_link(
            "pages/3_Interview.py",
            label=f"Practice the worst {min(REVIEW_QUESTIONS, len(weak))} in a weak-spot review session",
            icon="🎙️",
        )
        for spot in weak:
            label = QUESTION_TYPES[spot.question.type_key].label
            if spot.question.project_name:
                label += f" · {spot.question.project_name}"
            st.markdown(f"**{spot.score:g}/5** — {spot.question.text}")
            st.caption(f"{label} · last answered {spot.when}")

with tabs[2]:
    st.caption("Your best answers, saved during sessions. Read these before a real interview.")
    if not answers:
        st.info("Nothing saved yet. Press **⭐ Save to the answer bank** under any answer's feedback.")
    for saved in answers:
        with st.expander(f"{saved.question} ({saved.saved_at[:10]})"):
            if saved.project:
                st.caption(saved.project)
            st.markdown("**Your answer**")
            st.write(saved.answer)
            if saved.stronger:
                st.markdown("**A stronger version**")
                st.info(saved.stronger)
            if st.button("Delete", key=f"del_answer_{saved.id}"):
                delete_saved_answer(saved.id)
                st.rerun()
