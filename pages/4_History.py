from statistics import mean

import pandas as pd
import streamlit as st

from interviewer.feedback import Scores
from interviewer.session import MODES, Session
from interviewer.storage import delete_session, list_sessions, load_all, load_session
from interviewer.ui import show_session

st.set_page_config(page_title="History · Interviewer", page_icon="📈")
st.title("📈 History")

rows = list_sessions()
if not rows:
    st.info("No sessions yet. Every interview you finish is saved here automatically.")
    st.page_link("pages/3_Interview.py", label="Start practicing", icon="🎙️")
    st.stop()


def graded(session: Session) -> list:
    return [t.latest for t in session.answered() if t.latest.feedback]


def session_stats(session: Session) -> dict | None:
    """One row of the trend chart: average score and delivery for a session."""
    attempts = graded(session)
    if not attempts:
        return None
    scores = [mean(getattr(a.feedback.scores, f) for f in Scores.model_fields) for a in attempts]
    spoken = [a.delivery for a in attempts if a.delivery]
    row = {
        "date": session.started_at[:16].replace("T", " "),
        "Average score": round(mean(scores), 2),
        "Answers": len(attempts),
    }
    if spoken:
        row["Ums/uhs per minute"] = round(
            sum(sum(d.hesitations.values()) for d in spoken) / sum(d.minutes for d in spoken), 2
        )
        row["Words per minute"] = round(mean(d.wpm for d in spoken), 1)
    return row


stats = [s for s in (session_stats(x) for x in reversed(load_all())) if s]  # oldest first
if len(stats) >= 2:
    frame = pd.DataFrame(stats).set_index("date")
    c1, c2, c3 = st.columns(3)
    c1.metric("Sessions", len(stats))
    c2.metric("Answers", int(frame["Answers"].sum()))
    c3.metric("Average score", f"{frame['Average score'].mean():.1f}/5")
    st.markdown("**Average score per session**")
    st.line_chart(frame["Average score"], height=200)
    if "Ums/uhs per minute" in frame:
        st.markdown("**Delivery per session**")
        st.line_chart(frame[[c for c in ("Ums/uhs per minute", "Words per minute") if c in frame]], height=200)
else:
    st.caption("Finish another session to see trends over time.")

st.divider()
st.subheader("Sessions")
row = st.selectbox(
    "Pick a session",
    rows,
    format_func=lambda r: f"{r.date} · {MODES[r.mode].label} · {r.answers} answer(s)"
    + ("" if r.finished else " · unfinished"),
)
session = load_session(row.id)
if session is None:
    st.error("That session couldn't be loaded.")
    st.stop()

if not session.summary:
    st.caption("This session ended without a debrief, so there's no summary. The answers are below.")
show_session(session)

st.divider()
if st.checkbox("Delete this session", key=f"confirm_{row.id}"):
    if st.button("Delete permanently", type="primary"):
        delete_session(row.id)
        st.rerun()
