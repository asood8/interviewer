"""Interview sessions: modes, question plans, follow-up threads, and finishing with a debrief."""

import random
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from datetime import datetime

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
    "jd": Mode(
        "Job-description drill",
        "Paste a job posting; the questions aim at what that role is looking for.",
        2,
        False,
    ),
    "review": Mode(
        "Weak-spot review",
        "Re-answer the questions you scored lowest on, and see whether you've improved.",
        1,
        False,
    ),
}

REVIEW_QUESTIONS = 5  # how many weak spots one review session covers


@dataclass(frozen=True)
class Planned:
    type_key: str  # a QUESTION_TYPES key, or "mixed"
    project_name: str | None  # None rotates through projects
    depth: str
    question: Question | None = None  # set to re-ask a past question verbatim
    previous_score: float | None = None  # what it scored last time


@dataclass
class Settings:
    mode: str
    type_key: str = "mixed"
    project_name: str | None = None
    depth: str = "any"
    persona: str = "neutral"
    feedback_at_end: bool = False
    job_description: str = ""


def build_plan(settings: Settings, profile: Profile) -> list[Planned]:
    """The main questions for a session. Empty for free practice, which never runs out."""
    s = settings
    match s.mode:
        case "quick":
            return [Planned(s.type_key, s.project_name, s.depth)] * 3
        case "deep_dive":
            steps = [("pitch", "high"), ("drill_down", "low"), ("why_this", "any"), ("debugging", "any"), ("scaling", "any")]
            return [Planned(t, s.project_name, d) for t, d in steps]
        case "jd":
            plan = [Planned("about_me", None, "any")]
            if profile.named_projects():
                plan += [Planned(t, None, "any") for t in ("drill_down", "why_this")]
            plan += [
                Planned("concept_check" if profile.named_projects() else "behavioral", None, "any"),
                Planned("behavioral", None, "any"),
                Planned("motivation", None, "any"),
            ]
            return plan
        case "review":
            from interviewer import storage  # imported here: storage loads sessions, which live in this module

            return storage.weak_spot_plan(REVIEW_QUESTIONS)
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


def _planned_from_dict(d: dict) -> Planned:
    question = d.get("question")
    return Planned(
        type_key=d["type_key"],
        project_name=d["project_name"],
        depth=d["depth"],
        question=Question(**question) if question else None,
        previous_score=d.get("previous_score"),
    )


@dataclass
class Attempt:
    answer: str
    delivery: Delivery | None = None  # only for spoken answers
    audio: bytes | None = None
    feedback: Feedback | None = None  # None until graded
    audio_path: str = ""  # set once the recording is saved to disk

    def to_dict(self) -> dict:
        return {
            "answer": self.answer,
            "delivery": self.delivery.to_dict() if self.delivery else None,
            "feedback": self.feedback.model_dump() if self.feedback else None,
            "audio_path": self.audio_path,
        }

    @staticmethod
    def from_dict(d: dict) -> "Attempt":
        return Attempt(
            answer=d["answer"],
            delivery=Delivery.from_dict(d["delivery"]) if d["delivery"] else None,
            feedback=Feedback.model_validate(d["feedback"]) if d["feedback"] else None,
            audio_path=d["audio_path"],
        )


@dataclass
class Turn:
    question: Question
    root: int  # index in Session.turns of the main question this turn follows up on (itself if main)
    attempts: list[Attempt] = field(default_factory=list)
    follow_up: Question | None = None  # what the interviewer would ask next, given the latest attempt
    previous_score: float | None = None  # when re-asking, what this question scored last time

    @property
    def latest(self) -> Attempt | None:
        return self.attempts[-1] if self.attempts else None

    def to_dict(self) -> dict:
        return {
            "question": asdict(self.question),
            "root": self.root,
            "attempts": [a.to_dict() for a in self.attempts],
            "follow_up": asdict(self.follow_up) if self.follow_up else None,
            "previous_score": self.previous_score,
        }

    @staticmethod
    def from_dict(d: dict) -> "Turn":
        return Turn(
            question=Question(**d["question"]),
            root=d["root"],
            attempts=[Attempt.from_dict(a) for a in d["attempts"]],
            follow_up=Question(**d["follow_up"]) if d["follow_up"] else None,
            previous_score=d.get("previous_score"),
        )


@dataclass
class Session:
    settings: Settings
    plan: list[Planned]
    previous: list[Question] = field(default_factory=list)  # asked in earlier sessions, for variety
    turns: list[Turn] = field(default_factory=list)
    main_asked: int = 0
    summary: SessionSummary | None = None
    finished: bool = False
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    started_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))

    def to_dict(self) -> dict:
        """Everything worth keeping. Recordings live on disk, referenced by Attempt.audio_path."""
        return {
            "id": self.id,
            "started_at": self.started_at,
            "settings": asdict(self.settings),
            "plan": [asdict(p) for p in self.plan],
            "turns": [t.to_dict() for t in self.turns],
            "main_asked": self.main_asked,
            "summary": self.summary.model_dump() if self.summary else None,
            "finished": self.finished,
        }

    @staticmethod
    def from_dict(d: dict) -> "Session":
        return Session(
            settings=Settings(**d["settings"]),
            plan=[_planned_from_dict(p) for p in d["plan"]],
            turns=[Turn.from_dict(t) for t in d["turns"]],
            main_asked=d["main_asked"],
            summary=SessionSummary.model_validate(d["summary"]) if d["summary"] else None,
            finished=d["finished"],
            id=d["id"],
            started_at=d["started_at"],
        )

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
        if p.question is not None:  # a weak spot being re-asked: no need to write a new question
            self.turns.append(Turn(p.question, root=len(self.turns), previous_score=p.previous_score))
            self.main_asked += 1
            return
        type_key = pick_type(profile) if p.type_key == "mixed" else p.type_key
        project = None
        if QUESTION_TYPES[type_key].about_project:
            named = {pr.name: pr for pr in profile.named_projects()}
            project = named.get(p.project_name) or pick_project(profile, self.asked)
        q = generate_question(profile, type_key, project, p.depth, self.asked, s.persona, s.job_description)
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
                follow_up = pool.submit(
                    generate_follow_up, profile, exchange, self.asked, self.settings.persona,
                    self.settings.job_description,
                )
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
