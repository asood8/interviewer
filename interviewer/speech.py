"""Local speech-to-text with faster-whisper, keeping word timestamps for delivery metrics."""

import io
import os
import re
from dataclasses import dataclass
from functools import cache

from interviewer.profile import Profile

# small.en is a good balance of accuracy and speed on CPU. Try base.en if it's too slow,
# or medium.en if it mishears technical terms. Set WHISPER_DEVICE=cuda to use an NVIDIA GPU.
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "small.en")
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")

# Whisper normally cleans up disfluencies. A prompt that contains them nudges it
# to transcribe "um" and "uh" verbatim, which we need in order to count them.
FILLER_PROMPT = "Umm, so, uh, I built the, like, backend and, um, the... uh, frontend. Hmm."


@dataclass
class Word:
    text: str
    start: float
    end: float


@dataclass
class Transcript:
    text: str
    words: list[Word]
    duration: float  # length of the whole recording, in seconds


@cache
def _model():
    from faster_whisper import WhisperModel  # slow import, so only when first needed

    compute_type = "int8" if WHISPER_DEVICE == "cpu" else "default"
    return WhisperModel(WHISPER_MODEL, device=WHISPER_DEVICE, compute_type=compute_type)


def vocabulary(profile: Profile) -> str:
    """Project names and tech from the profile, so Whisper spells jargon correctly."""
    terms: dict[str, str] = {}  # lowercase -> original, to dedupe case-insensitively
    for p in profile.named_projects():
        for t in [p.name, *re.split(r"[,;/\n]", p.tech_stack)]:
            if t.strip():
                terms.setdefault(t.strip().lower(), t.strip())
    return ", ".join(terms.values())[:500]


def transcribe(audio: bytes, profile: Profile) -> Transcript:
    segments, info = _model().transcribe(
        io.BytesIO(audio),
        language="en",
        word_timestamps=True,
        initial_prompt=FILLER_PROMPT,
        hotwords=vocabulary(profile) or None,
        condition_on_previous_text=False,
    )
    words = [
        Word(w.word.strip(), w.start, w.end)
        for seg in segments
        for w in (seg.words or [])
        if w.word.strip()
    ]
    text = " ".join(w.text for w in words)
    return Transcript(text=text, words=words, duration=info.duration)
