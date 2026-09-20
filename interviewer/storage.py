"""Saving practice sessions to SQLite, and recordings to disk, so history survives restarts."""

import json
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

from interviewer.profile import DATA_DIR
from interviewer.session import Session

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
)
"""


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
    conn.execute(SCHEMA)
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
