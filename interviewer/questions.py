"""Question types, picking what to ask next, and generating questions with Claude."""

import random
from collections import Counter
from dataclasses import dataclass, field

from pydantic import BaseModel, Field

from interviewer import llm, prompts
from interviewer.profile import Profile, Project


@dataclass(frozen=True)
class QuestionType:
    label: str
    description: str
    about_project: bool


QUESTION_TYPES: dict[str, QuestionType] = {
    "pitch": QuestionType(
        "Elevator pitch",
        "Ask them to explain a project briefly, in a set time (30 seconds, 2 minutes, etc.).",
        True,
    ),
    "drill_down": QuestionType(
        "Drill-down",
        "Pick one specific component or feature of the project and ask how it works.",
        True,
    ),
    "why_this": QuestionType(
        "Why this, not that",
        "Ask why they chose a specific technology, design, or approach over a reasonable alternative.",
        True,
    ),
    "debugging": QuestionType(
        "Debugging story",
        "Ask about the hardest bug or technical problem they hit and how they solved it.",
        True,
    ),
    "scaling": QuestionType(
        "Scaling / what-if",
        "Ask what would break or change under much more load, data, or users, or how they'd add a feature.",
        True,
    ),
    "non_technical": QuestionType(
        "Explain to a non-engineer",
        "Ask them to explain the project (or part of it) to a recruiter or product manager.",
        True,
    ),
    "concept_check": QuestionType(
        "Concept check",
        "Ask how an underlying technology or concept used in the project works in general.",
        True,
    ),
    "ownership": QuestionType(
        "Ownership",
        "Ask exactly which parts they personally built and which decisions were theirs.",
        True,
    ),
    "retrospective": QuestionType(
        "Retrospective",
        "Ask what they would change if they rebuilt it, or what they learned.",
        True,
    ),
    "about_me": QuestionType(
        "Tell me about yourself",
        "Ask them to introduce themselves or walk through their resume.",
        False,
    ),
    "behavioral": QuestionType(
        "Behavioral",
        "A behavioral question (conflict, failure, leadership, tight deadline, learning fast, etc.) "
        "that expects a STAR-style story.",
        False,
    ),
    "motivation": QuestionType(
        "Motivation",
        "Why this kind of role, what they're looking for, where they want to go.",
        False,
    ),
    "curveball": QuestionType(
        "Curveball",
        "A common but uncomfortable question: weaknesses, gaps, something not on the resume, etc.",
        False,
    ),
    "questions_for_them": QuestionType(
        "Your questions for them",
        "Ask whether they have questions for you. Their answer is the questions they would ask.",
        False,
    ),
}

DEPTHS = {
    "any": "Any depth that fits the question type.",
    "high": "High level: the big picture, purpose, and overall design.",
    "low": "Low level: implementation details, specific code paths, edge cases, and internals.",
}

# Mixed mode favors project questions, since explaining projects is the main thing to practice.
PROJECT_WEIGHT = 3


class GeneratedQuestion(BaseModel):
    question: str = Field(description="The question, as the interviewer would say it.")
    strong_answer_covers: list[str] = Field(description="3-6 short points a strong answer would cover.")


@dataclass
class Question:
    text: str
    type_key: str
    project_name: str | None
    depth: str
    strong_answer_covers: list[str] = field(default_factory=list)


def pick_type(profile: Profile) -> str:
    keys = list(QUESTION_TYPES)
    if not profile.named_projects():
        keys = [k for k in keys if not QUESTION_TYPES[k].about_project]
    weights = [PROJECT_WEIGHT if QUESTION_TYPES[k].about_project else 1 for k in keys]
    return random.choices(keys, weights=weights)[0]


def pick_project(profile: Profile, asked: list[Question]) -> Project:
    """Rotate through projects: pick randomly among the least-asked-about ones."""
    projects = profile.named_projects()
    counts = Counter(q.project_name for q in asked)
    fewest = min(counts[p.name] for p in projects)
    return random.choice([p for p in projects if counts[p.name] == fewest])


def generate_question(
    profile: Profile,
    type_key: str,
    project: Project | None,
    depth: str,
    asked: list[Question],
) -> Question:
    qtype = QUESTION_TYPES[type_key]
    lines = [f"Question type: {qtype.label}. {qtype.description}"]
    if qtype.about_project and project:
        lines.append(f'Project: "{project.name}"')
        lines.append(f"Depth: {DEPTHS[depth]}")
    if asked:
        history = "\n".join(f"- {q.text}" for q in asked[-30:])
        lines.append(f"<already_asked>\n{history}\n</already_asked>")
    lines.append("Write the next question.")

    result = llm.ask_structured(
        llm.system_blocks(profile.to_prompt(), prompts.INTERVIEWER),
        "\n\n".join(lines),
        GeneratedQuestion,
        effort="medium",
    )
    return Question(
        text=result.question,
        type_key=type_key,
        project_name=project.name if qtype.about_project and project else None,
        depth=depth,
        strong_answer_covers=result.strong_answer_covers,
    )
