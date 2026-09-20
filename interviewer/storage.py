"""Saving practice sessions to SQLite, and recordings to disk, so history survives restarts."""

import json
import re
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from statistics import mean

from interviewer.feedback import Scores
from interviewer.profile import DATA_DIR
from interviewer.questions import Question
from interviewer.session import Planned, Session

DB_PATH = DATA_DIR / "history.db"
RECORDINGS_DIR = DATA_DIR / "recordings"

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL,
    mode TEXT NOT NULL,
    finished INTEGER NOT NULL,
    answers INTEGER NOT NULL,
    data TEXT NOT NULL
);
-- One row per (session, topic), so re-saving a session never double-counts it.
CREATE TABLE IF NOT EXISTS topic_hits (
    session_id TEXT NOT NULL,
    topic_key TEXT NOT NULL,
    text TEXT NOT NULL,
    seen_at TEXT NOT NULL,
    PRIMARY KEY (session_id, topic_key)
);
CREATE TABLE IF NOT EXISTS topic_status (
    topic_key TEXT PRIMARY KEY,
    done INTEGER NOT NULL,
    done_at TEXT
);
CREATE TABLE IF NOT EXISTS saved_answers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    saved_at TEXT NOT NULL,
    question TEXT NOT NULL,
    project TEXT,
    answer TEXT NOT NULL,
    stronger TEXT
)
"""

# Scores average below this (out of 5) count as a weak spot worth redoing.
WEAK_SCORE = 3.5


@dataclass(frozen=True)
class SessionRow:
    """One row of the history list, without loading the whole session."""

    id: str
    started_at: str
    mode: str
    finished: bool
    answers: int

    @property
    def date(self) -> str:
        return self.started_at.replace("T", " ")[:19]


def _connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    return conn


def save_recordings(session: Session) -> None:
    """Write any new recordings to disk and point the attempts at them."""
    folder = RECORDINGS_DIR / session.id
    for t, turn in enumerate(session.turns):
        for a, attempt in enumerate(turn.attempts):
            if attempt.audio and not attempt.audio_path:
                folder.mkdir(parents=True, exist_ok=True)
                path = folder / f"{t:02d}_{a}.wav"
                path.write_bytes(attempt.audio)
                attempt.audio_path = str(path)


def save_session(session: Session) -> None:
    """Insert or update the session. Safe to call after every answer."""
    if not session.turns:
        return
    save_recordings(session)
    with closing(_connect()) as conn, conn:
        conn.execute(
            "INSERT INTO sessions (id, started_at, mode, finished, answers, data) VALUES (?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET finished=excluded.finished, answers=excluded.answers, data=excluded.data",
            (
                session.id,
                session.started_at,
                session.settings.mode,
                int(session.finished),
                len(session.answered()),
                json.dumps(session.to_dict()),
            ),
        )
    if session.finished:
        record_topics(session)


def list_sessions() -> list[SessionRow]:
    """Newest first. Sessions with no answers are left out."""
    with closing(_connect()) as conn:
        rows = conn.execute(
            "SELECT id, started_at, mode, finished, answers FROM sessions WHERE answers > 0 "
            "ORDER BY started_at DESC, id DESC"
        ).fetchall()
    return [SessionRow(i, started, mode, bool(done), answers) for i, started, mode, done, answers in rows]


def load_session(session_id: str) -> Session | None:
    with closing(_connect()) as conn:
        row = conn.execute("SELECT data FROM sessions WHERE id = ?", (session_id,)).fetchone()
    return Session.from_dict(json.loads(row[0])) if row else None


def load_all() -> list[Session]:
    """Every session with answers, newest first. Used for trends."""
    with closing(_connect()) as conn:
        rows = conn.execute("SELECT data FROM sessions WHERE answers > 0 ORDER BY started_at DESC, id DESC").fetchall()
    return [Session.from_dict(json.loads(r[0])) for r in rows]


def delete_session(session_id: str) -> None:
    with closing(_connect()) as conn, conn:
        conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    folder = RECORDINGS_DIR / session_id
    if folder.is_dir():
        for file in folder.iterdir():
            file.unlink()
        folder.rmdir()


def audio_source(path: str) -> bytes | None:
    """Recording bytes for playback, or None if the file is gone."""
    file = Path(path)
    return file.read_bytes() if file.is_file() else None


# --- Review topics ----------------------------------------------------------


@dataclass(frozen=True)
class Topic:
    key: str
    text: str
    times_seen: int
    last_seen: str
    done: bool


def _topic_key(text: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", text.lower()).split())


def record_topics(session: Session) -> None:
    """Collect 'what to review' items from a finished session into the review list."""
    topics: list[str] = []
    for turn in session.answered():
        if turn.latest.feedback:
            topics += turn.latest.feedback.review_topics
    if session.summary:
        topics += session.summary.review_topics
    rows = {}
    for text in topics:
        if key := _topic_key(text):
            rows[key] = (session.id, key, text.strip(), session.started_at)
    if not rows:
        return
    with closing(_connect()) as conn, conn:
        conn.executemany(
            "INSERT INTO topic_hits (session_id, topic_key, text, seen_at) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(session_id, topic_key) DO UPDATE SET text=excluded.text",
            list(rows.values()),
        )


def list_topics() -> list[Topic]:
    """Review topics, most-repeated first. Topics seen in several sessions matter most."""
    with closing(_connect()) as conn:
        rows = conn.execute(
            "SELECT h.topic_key, MAX(h.text), COUNT(*), MAX(h.seen_at), COALESCE(s.done, 0) "
            "FROM topic_hits h LEFT JOIN topic_status s ON s.topic_key = h.topic_key "
            "GROUP BY h.topic_key ORDER BY COALESCE(s.done, 0), COUNT(*) DESC, MAX(h.seen_at) DESC"
        ).fetchall()
    return [Topic(key, text, count, seen, bool(done)) for key, text, count, seen, done in rows]


def set_topic_done(key: str, done: bool) -> None:
    with closing(_connect()) as conn, conn:
        conn.execute(
            "INSERT INTO topic_status (topic_key, done, done_at) VALUES (?, ?, ?) "
            "ON CONFLICT(topic_key) DO UPDATE SET done=excluded.done, done_at=excluded.done_at",
            (key, int(done), datetime.now().isoformat(timespec="seconds") if done else None),
        )


# --- Weak spots -------------------------------------------------------------


@dataclass(frozen=True)
class WeakSpot:
    question: Question
    score: float
    when: str


def weak_spots(limit: int = 20) -> list[WeakSpot]:
    """The lowest-scoring answers, one per question, worst first. Only the latest attempt counts."""
    weak: dict[str, WeakSpot] = {}
    seen: set[str] = set()  # every question whose latest attempt we've already judged, good or bad
    for session in load_all():  # newest first, so the first time we see a question is the latest attempt
        for turn in session.answered():
            feedback = turn.latest.feedback
            key = turn.question.text.strip().lower()
            if not feedback or key in seen:
                continue
            seen.add(key)
            score = mean(getattr(feedback.scores, f) for f in Scores.model_fields)
            if score < WEAK_SCORE:
                weak[key] = WeakSpot(turn.question, round(score, 2), session.started_at[:10])
    return sorted(weak.values(), key=lambda w: w.score)[:limit]


# --- Answer bank ------------------------------------------------------------


@dataclass(frozen=True)
class SavedAnswer:
    id: int
    saved_at: str
    question: str
    project: str | None
    answer: str
    stronger: str | None


def save_answer(question: str, project: str | None, answer: str, stronger: str | None) -> None:
    with closing(_connect()) as conn, conn:
        conn.execute(
            "INSERT INTO saved_answers (saved_at, question, project, answer, stronger) VALUES (?, ?, ?, ?, ?)",
            (datetime.now().isoformat(timespec="seconds"), question, project, answer, stronger),
        )


def list_saved_answers() -> list[SavedAnswer]:
    with closing(_connect()) as conn:
        rows = conn.execute(
            "SELECT id, saved_at, question, project, answer, stronger FROM saved_answers ORDER BY saved_at DESC"
        ).fetchall()
    return [SavedAnswer(*r) for r in rows]


def delete_saved_answer(answer_id: int) -> None:
    with closing(_connect()) as conn, conn:
        conn.execute("DELETE FROM saved_answers WHERE id = ?", (answer_id,))


def weak_spot_plan(limit: int) -> list[Planned]:
    """A session plan that re-asks the lowest-scoring questions, worst first."""
    return [
        Planned(w.question.type_key, w.question.project_name, w.question.depth, w.question, w.score)
        for w in weak_spots(limit)
    ]
