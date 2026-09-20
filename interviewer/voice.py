"""Reading questions out loud, so a session feels more like a real interview."""

import subprocess
import sys
import tempfile
from functools import lru_cache
from pathlib import Path

# pyttsx3 drives the system voice (SAPI on Windows). It doesn't survive being run repeatedly
# in a long-lived process, so each question is rendered in a short-lived subprocess instead.
SCRIPT = """
import sys, pyttsx3
engine = pyttsx3.init()
engine.setProperty("rate", 170)
engine.save_to_file(sys.argv[1], sys.argv[2])
engine.runAndWait()
"""


@lru_cache(maxsize=32)
def speak(text: str) -> bytes | None:
    """The question as spoken audio, or None if this machine has no working text-to-speech."""
    with tempfile.TemporaryDirectory() as folder:
        out = Path(folder) / "question.wav"
        try:
            result = subprocess.run(
                [sys.executable, "-c", SCRIPT, text, str(out)],
                capture_output=True, text=True, timeout=60,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except (OSError, subprocess.SubprocessError):
            return None
        if result.returncode != 0 or not out.is_file() or out.stat().st_size == 0:
            return None
        return out.read_bytes()
