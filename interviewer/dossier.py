"""Building a project dossier by interviewing the candidate about one project."""

from pydantic import BaseModel, Field

from interviewer import llm, prompts
from interviewer.profile import Dossier, Profile, Project

MAX_QUESTIONS = 10  # per round of dossier-building


class NextQuestion(BaseModel):
    question: str | None = Field(
        description="The next question to ask, or null if there's enough to write the dossier."
    )


def _context(project: Project, transcript: list[tuple[str, str]]) -> list[str]:
    parts = [f'Project: "{project.name}"']
    if project.dossier and not project.dossier.is_empty():
        parts.append(f"<existing_notes>\n{project.dossier.to_prompt()}\n</existing_notes>")
    if transcript:
        exchange = "\n".join(f"<q>{q}</q>\n<a>{a.strip()}</a>" for q, a in transcript)
        parts.append(f"<conversation_so_far>\n{exchange}\n</conversation_so_far>")
    return parts


def next_question(profile: Profile, project: Project, transcript: list[tuple[str, str]]) -> str | None:
    """The next thing to ask about this project, or None when there's enough for a dossier."""
    if len(transcript) >= MAX_QUESTIONS:
        return None
    lines = [
        *_context(project, transcript),
        f"You have asked {len(transcript)} question(s) so far and may ask up to {MAX_QUESTIONS}.",
        "Ask the next question, or return null if you have enough.",
    ]
    return llm.ask_structured(
        llm.system_blocks(profile.to_prompt(), prompts.DOSSIER_INTERVIEWER),
        "\n\n".join(lines),
        NextQuestion,
        effort="medium",
    ).question


def write_dossier(profile: Profile, project: Project, transcript: list[tuple[str, str]]) -> Dossier:
    """Turn the conversation (and any existing notes) into the project dossier."""
    lines = [*_context(project, transcript), prompts.DOSSIER_WRITER]
    return llm.ask_structured(
        llm.system_blocks(profile.to_prompt(), prompts.DOSSIER_INTERVIEWER),
        "\n\n".join(lines),
        Dossier,
        effort="high",
    )
