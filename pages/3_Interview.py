import streamlit as st

from interviewer.delivery import Delivery, analyze
from interviewer.llm import LLMError
from interviewer.questions import DEPTHS, PERSONAS, QUESTION_TYPES
from interviewer.session import MODES, Attempt, Session, Settings, build_plan
from interviewer.storage import save_session
from interviewer.ui import answer_input, bullets, show_attempt, show_session, working_profile

st.set_page_config(page_title="Interview · Interviewer", page_icon="🎙️")
st.title("🎙️ Interview")

profile = working_profile()
if profile.is_empty():
    st.warning("Your profile is empty. Add your resume and projects first.")
    st.page_link("pages/1_Profile.py", label="Go to Profile", icon="📝")
    st.stop()

state = st.session_state
state.setdefault("session", None)
state.setdefault("past_questions", [])  # from earlier sessions, so questions don't repeat
state.setdefault("last_settings", Settings(mode="free"))
session: Session | None = state.session
projects = profile.named_projects()


def run(action, spinner: str) -> bool:
    """Run a Claude-backed action with a spinner, then save. Shows the error and returns False if it fails."""
    with st.spinner(spinner):
        try:
            action()
        except LLMError as e:
            st.error(str(e))
            return False
    if state.session:
        save_session(state.session)
    return True


def end_session() -> None:
    state.past_questions += [t.question for t in session.turns]
    state.session = None


with st.sidebar:
    speak = st.radio("Answer by", ["Speaking", "Typing"], horizontal=True) == "Speaking"
    if session and not session.finished:
        st.divider()
        st.markdown(f"**{session.mode.label}**")
        if session.plan:
            st.progress(session.main_asked / len(session.plan), f"Question {session.main_asked} of {len(session.plan)}")
        else:
            st.caption(f"{len(session.turns)} question(s) so far")
        if session.answered():
            if st.button("End session and see debrief", width="stretch"):
                if run(lambda: session.finish(profile), "Reviewing your answers..."):
                    st.rerun()
        elif st.button("Cancel session", width="stretch"):
            end_session()
            st.rerun()

# --- Setup ------------------------------------------------------------------


def render_setup() -> None:
    last: Settings = state.last_settings
    modes = list(MODES)
    mode = st.radio(
        "Mode",
        modes,
        index=modes.index(last.mode),
        format_func=lambda m: MODES[m].label,
        captions=[MODES[m].description for m in modes],
    )
    settings = Settings(mode=mode, persona=last.persona)

    if mode in ("free", "quick"):
        types = ["mixed", *QUESTION_TYPES]
        settings.type_key = st.selectbox(
            "Question type",
            types,
            index=types.index(last.type_key),
            format_func=lambda k: "Mixed (random)" if k == "mixed" else QUESTION_TYPES[k].label,
        )
    about_project = mode in ("deep_dive", "mock") or settings.type_key == "mixed" or QUESTION_TYPES[settings.type_key].about_project

    if mode == "deep_dive":
        if not projects:
            st.error("Add a project to your profile first.")
            st.stop()
        names = [p.name for p in projects]
        settings.project_name = st.selectbox(
            "Project", names, index=names.index(last.project_name) if last.project_name in names else 0
        )
    elif mode in ("free", "quick") and about_project and projects:
        options = [None, *(p.name for p in projects)]
        settings.project_name = st.selectbox(
            "Project",
            options,
            index=options.index(last.project_name) if last.project_name in options else 0,
            format_func=lambda n: "Rotate through all" if n is None else n,
        )
        depths = list(DEPTHS)
        settings.depth = st.radio(
            "Depth",
            depths,
            index=depths.index(last.depth),
            format_func={"any": "Any", "high": "High level", "low": "Low level"}.get,
            horizontal=True,
        )

    personas = list(PERSONAS)
    settings.persona = st.radio(
        "Interviewer", personas, index=personas.index(last.persona), format_func=str.capitalize, horizontal=True,
        help="\n\n".join(f"**{k.capitalize()}**: {v}" for k, v in PERSONAS.items()),
    )
    settings.feedback_at_end = st.toggle(
        "Hold feedback until the end",
        value=MODES[mode].feedback_at_end,
        key=f"feedback_at_end_{mode}",
        help="More realistic: the interviewer moves straight on (or follows up) and you get all the feedback at the end.",
    )

    if st.button("Start", type="primary"):
        state.last_settings = settings
        new = Session(settings, build_plan(settings, profile), previous=list(state.past_questions))
        if run(lambda: new.ask_next_main(profile), "Thinking of a question..."):
            state.session = new
            st.rerun()


if session is None:
    render_setup()
    st.stop()

# --- Debrief ----------------------------------------------------------------


def render_debrief() -> None:
    st.header("Session debrief")
    show_session(session)
    if st.button("Start a new session", type="primary"):
        end_session()
        st.rerun()


if session.finished:
    render_debrief()
    st.stop()

# --- Current question -------------------------------------------------------

turn = session.current
q = turn.question
label = QUESTION_TYPES[q.type_key].label
if q.project_name:
    label += f" · {q.project_name}"
if q.is_follow_up:
    label = "Follow-up · " + label
st.caption(label)
st.markdown(f"### {q.text}")

holding = session.settings.feedback_at_end
retrying = state.get("retrying_turn") == len(session.turns)

# With feedback shown per answer, the answered question stays on screen with its feedback and choices.
if turn.attempts and not holding:
    for i, a in reversed(list(enumerate(turn.attempts[:-1], 1))):
        with st.expander(f"Attempt {i}"):
            show_attempt(a, "Your answer")
    show_attempt(turn.latest, f"Your answer (attempt {len(turn.attempts)})")
    with st.expander("What a strong answer covers"):
        bullets(q.strong_answer_covers)
    st.divider()

    if not retrying:
        follow_up = session.pending_follow_up()
        cols = st.columns(3 if follow_up else 2)
        if cols[0].button("🔁 Try again", width="stretch"):
            state.retrying_turn = len(session.turns)
            st.rerun()
        if follow_up and cols[1].button("💬 Answer the follow-up", type="primary", width="stretch"):
            session.ask_follow_up()
            st.rerun()
        if session.has_more_main:
            if cols[-1].button("➡️ Next question", width="stretch"):
                if run(lambda: session.ask_next_main(profile), "Thinking of a question..."):
                    st.rerun()
        elif cols[-1].button("🏁 Finish and see debrief", width="stretch"):
            if run(lambda: session.finish(profile), "Writing your debrief..."):
                st.rerun()
        st.stop()

if turn.attempts and holding and not retrying:
    # Only happens if the answer was saved but loading the next question failed.
    st.info("Your answer is saved.")
    if st.button("Continue", type="primary"):
        if run(lambda: session.advance(profile), "The interviewer is thinking..."):
            st.rerun()
    st.stop()

# --- Answer -----------------------------------------------------------------


def submit(answer: str, delivery: Delivery | None = None, audio: bytes | None = None) -> None:
    if not answer.strip():
        st.warning("There's no answer to submit yet.")
        return

    def action():
        session.submit(profile, Attempt(answer, delivery, audio))
        if holding:
            session.advance(profile)

    spinner = "The interviewer is thinking..." if holding else "Reviewing your answer..."
    if run(action, spinner):
        state.retrying_turn = None
        st.rerun()


# A fresh key per question and attempt clears the inputs.
attempt_key = f"{len(session.turns)}_{len(turn.attempts)}_{id(session)}"

if result := answer_input(profile, attempt_key, speak):
    submit(*result)
