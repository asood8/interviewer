"""Delivery metrics computed locally from a timestamped transcript: pace, fillers, pauses, length."""

import re
from collections import Counter
from dataclasses import dataclass

from interviewer.speech import Transcript

# Hesitation sounds: always fillers.
HESITATIONS = {"um", "umm", "uh", "uhh", "uhm", "er", "erm", "ah", "hmm", "mm"}
# Verbal crutches: often fillers, but sometimes real words ("I'd like to"), so reported separately.
CRUTCH_WORDS = {"like", "basically", "actually", "literally", "honestly", "right"}
CRUTCH_PHRASES = ["you know", "i mean", "kind of", "sort of"]

LONG_PAUSE_SECONDS = 3.0
TARGET_WPM = (130, 160)
LONG_ANSWER_SECONDS = 180


@dataclass
class Pause:
    seconds: float
    after: str  # the few words spoken just before the pause


@dataclass
class Delivery:
    duration: float  # seconds from the first word to the last
    thinking_time: float  # silence before the first word
    word_count: int
    wpm: float
    hesitations: Counter
    crutches: Counter
    long_pauses: list[Pause]

    @property
    def minutes(self) -> float:
        return max(self.duration, 1.0) / 60

    @property
    def hesitations_per_min(self) -> float:
        return sum(self.hesitations.values()) / self.minutes

    @property
    def crutches_per_min(self) -> float:
        return sum(self.crutches.values()) / self.minutes

    def notes(self) -> list[str]:
        """Plain-language observations, worst first."""
        notes = []
        lo, hi = TARGET_WPM
        if self.word_count >= 20:
            if self.wpm > hi + 20:
                notes.append(f"You spoke fast ({self.wpm:.0f} wpm). Aim for {lo}-{hi}. Slow down on key points.")
            elif self.wpm < lo - 30:
                notes.append(f"You spoke slowly ({self.wpm:.0f} wpm). Aim for {lo}-{hi}.")
        if sum(self.hesitations.values()) >= 3 and self.hesitations_per_min >= 4:
            notes.append(
                f"{sum(self.hesitations.values())} ums/uhs ({self.hesitations_per_min:.1f}/min). "
                "Try pausing silently instead. A short silence sounds more confident than a filler."
            )
        if sum(self.crutches.values()) >= 3 and self.crutches_per_min >= 4:
            top = ", ".join(f'"{w}" x{n}' for w, n in self.crutches.most_common(3))
            notes.append(f"Frequent crutch words: {top}.")
        if self.long_pauses:
            notes.append(
                f"{len(self.long_pauses)} long pause(s) mid-answer. That usually means you lost the thread. "
                "Having a structure in mind before you start helps."
            )
        if self.duration > LONG_ANSWER_SECONDS:
            notes.append(f"Long answer ({self.duration / 60:.1f} min). Most answers should land in 1-2 minutes.")
        return notes

    def to_prompt(self) -> str:
        """A summary for the evaluator, so it can judge length and flow of a spoken answer."""
        pauses = "; ".join(f'{p.seconds:.1f}s after "{p.after}"' for p in self.long_pauses) or "none"
        return (
            f"Spoken answer. Length: {self.duration:.0f}s, {self.word_count} words, {self.wpm:.0f} wpm. "
            f"Thinking time before starting: {self.thinking_time:.1f}s. "
            f"Hesitations (um/uh): {sum(self.hesitations.values())}. "
            f"Long pauses: {pauses}."
        )


def _norm(word: str) -> str:
    return re.sub(r"[^a-z']", "", word.lower())


def analyze(t: Transcript) -> Delivery:
    words = t.words
    if not words:
        return Delivery(0, t.duration, 0, 0, Counter(), Counter(), [])

    normed = [_norm(w.text) for w in words]
    hesitations = Counter(n for n in normed if n in HESITATIONS)
    crutches = Counter(n for n in normed if n in CRUTCH_WORDS)
    joined = " " + " ".join(normed) + " "
    for phrase in CRUTCH_PHRASES:
        if n := joined.count(f" {phrase} "):
            crutches[phrase] = n

    pauses = []
    for i in range(1, len(words)):
        gap = words[i].start - words[i - 1].end
        if gap >= LONG_PAUSE_SECONDS:
            before = " ".join(w.text for w in words[max(0, i - 4) : i])
            pauses.append(Pause(gap, before))

    duration = words[-1].end - words[0].start
    spoken = [n for n in normed if n and n not in HESITATIONS]
    wpm = len(spoken) / (max(duration, 1.0) / 60)
    return Delivery(
        duration=duration,
        thinking_time=words[0].start,
        word_count=len(spoken),
        wpm=wpm,
        hesitations=hesitations,
        crutches=crutches,
        long_pauses=pauses,
    )
