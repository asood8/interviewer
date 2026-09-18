"""Interview sessions: modes, question plans, follow-up threads, and finishing with a debrief."""

import random
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from interviewer.delivery import Delivery
from interviewer.feedback import Feedback, SessionSummary, evaluate, summarize
from interviewer.profile import Profile
from interviewer.questions import QUESTION_TYPES, Question, generate_follow_up, generate_question, pick_project, pick_type


@dataclass(frozen=True)
class Mode:
    label: str
    description: str
    max_follow_ups: int  # per main question
    feedback_at_end: bool  # default for this mode


MODES = {
    "free": Mode(
        "Free practice",
        "Pick the question type, project, and depth. Keep going as long as you like.",
        3,
        False,
    ),
    "quick": Mode("Quick drill", "3 questions plus follow-ups. About 5 minutes.", 2, False),
    "deep_dive": Mode(
        "Project deep-dive",
        "One project, from the elevator pitch down to implementation details. About 15 minutes.",
        2,
        False,
    ),
    "mock": Mode(
        "Full mock interview",
        "A realistic interview: intro, projects, behavioral, and your questions. About 30 minutes.",
        2,
        True,
    ),
}


@dataclass(frozen=True)
class Planned:
    type_key: str  # a QUESTION_TYPES key, or "mixed"
    project_name: str | None  # None rotates through projects
    depth: str


@dataclass
class Settings:
    mode: str
    type_key: str = "mixed"
    project_name: str | None = None
    depth: str = "any"
    persona: str = "neutral"
    feedback_at_end: bool = False


def build_plan(settings: Settings, profile: Profile) -> list[Planned]:
    """The main questions for a session. Empty for free practice, which never runs out."""
    s = settings
    match s.mode:
        case "quick":
            return [Planned(s.type_key, s.project_name, s.depth)] * 3
        case "deep_dive":
            steps = [("pitch", "high"), ("drill_down", "low"), ("why_this", "any"), ("debugging", "any"), ("scaling", "any")]
            return [Planned(t, s.project_name, d) for t, d in steps]
        case "mock":
            plan = [Planned("about_me", None, "any")]
            if profile.named_projects():
                project_types = random.sample(["drill_down", "why_this", "debugging", "scaling", "ownership"], 2)
                plan += [Planned(t, None, "any") for t in project_types]
            plan += [
                Planned("behavioral", None, "any"),
                Planned(random.choice(["motivation", "curveball"]), None, "any"),
                Planned("questions_for_them", None, "any"),
            ]
            return plan
    return []


@dataclass
class Attempt:
    answer: str
    delivery: Delivery | None = None  # only for spoken answers
    audio: bytes | None = None
    feedback: Feedback | None = None  # None until graded


@dataclass
class Turn:
    question: Question
    root: int  # index in Session.turns of the main question this turn follows up on (itself if main)
    attempts: list[Attempt] = field(default_factory=list)
    follow_up: Question | None = None  # what the interviewer would ask next, given the latest attempt

    @property
    def latest(self) -> Attempt | None:
        return self.attempts[-1] if self.attempts else None


@dataclass
class Session:
    settings: Settings
    plan: list[Planned]
    previous: list[Question] = field(default_factory=list)  # asked in earlier sessions, for variety
    turns: list[Turn] = field(default_factory=list)
    main_asked: int = 0
    summary: SessionSummary | None = None
    finished: bool = False

    @property
    def mode(self) -> Mode:
        return MODES[self.settings.mode]

    @property
    def current(self) -> Turn | None:
        return self.turns[-1] if self.turns else None

    @property
    def asked(self) -> list[Question]:
        return self.previous + [t.question for t in self.turns]

    @property
    def has_more_main(self) -> bool:
        return not self.plan or self.main_asked < len(self.plan)

    def thread(self, turn: Turn) -> list[Turn]:
        """The main question and follow-ups up to and including `turn`."""
        end = self.turns.index(turn)
        return [t for t in self.turns[turn.root : end + 1] if t.root == turn.root]

    def follow_ups_left(self, turn: Turn) -> int:
        return self.mode.max_follow_ups - (len(self.thread(turn)) - 1)

    def pending_follow_up(self) -> Question | None:
        turn = self.current
        if turn and turn.follow_up and self.follow_ups_left(turn) > 0:
            return turn.follow_up
        return None

    def ask_next_main(self, profile: Profile) -> None:
        s = self.settings
        p = self.plan[self.main_asked] if self.plan else Planned(s.type_key, s.project_name, s.depth)
        type_key = pick_type(profile) if p.type_key == "mixed" else p.type_key
        project = None
        if QUESTION_TYPES[type_key].about_project:
            named = {pr.name: pr for pr in profile.named_projects()}
            project = named.get(p.project_name) or pick_project(profile, self.asked)
        q = generate_question(profile, type_key, project, p.depth, self.asked, s.persona)
        self.turns.append(Turn(q, root=len(self.turns)))
        self.main_asked += 1

    def ask_follow_up(self) -> None:
        q = self.pending_follow_up()
        assert q is not None
        self.turns.append(Turn(q, root=self.current.root))

    def advance(self, profile: Profile) -> None:
        """Move on the way a real interviewer would: follow up if there's one, else the next question, else finish."""
        if self.pending_follow_up():
            self.ask_follow_up()
        elif self.has_more_main:
            self.ask_next_main(profile)
        else:
            self.finish(profile)

    def _earlier(self, turn: Turn) -> list[tuple[Question, str]]:
        return [(t.question, t.latest.answer) for t in self.thread(turn)[:-1] if t.latest]

    def submit(self, profile: Profile, attempt: Attempt) -> None:
        """Record an answer to the current question. Grades it now unless feedback is held for the end,
        and in parallel decides on a follow-up. Nothing changes if a Claude call fails."""
        turn = self.current
        exchange = self._earlier(turn) + [(turn.question, attempt.answer)]
        with ThreadPoolExecutor() as pool:
            follow_up = None
            if self.follow_ups_left(turn) > 0:
                follow_up = pool.submit(generate_follow_up, profile, exchange, self.asked, self.settings.persona)
            feedback = None
            if not self.settings.feedback_at_end:
                feedback = pool.submit(
                    evaluate, profile, turn.question, attempt.answer, attempt.delivery, self._earlier(turn)
                )
            new_follow_up = follow_up.result() if follow_up else None
            attempt.feedback = feedback.result() if feedback else None
        turn.attempts.append(attempt)
        turn.follow_up = new_follow_up

    def answered(self) -> list[Turn]:
        return [t for t in self.turns if t.latest]

    def finish(self, profile: Profile) -> None:
        """Grade anything not yet graded (all at once), then write the session debrief."""
        ungraded = [t for t in self.answered() if t.latest.feedback is None]
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = [
                pool.submit(evaluate, profile, t.question, t.latest.answer, t.latest.delivery, self._earlier(t))
                for t in ungraded
            ]
            results = [f.result() for f in futures]
        for t, fb in zip(ungraded, results):
            t.latest.feedback = fb
        answered = self.answered()
        if answered:
            self.summary = summarize(
                profile, [(t.question, t.latest.answer, t.latest.feedback, t.latest.delivery) for t in answered]
            )
        self.finished = True
