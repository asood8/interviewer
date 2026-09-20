"""Reading a resume PDF, and pulling project entries out of it."""

import io

from pydantic import BaseModel, Field

from interviewer import llm, prompts
from interviewer.profile import Profile, Project


class ResumeError(Exception):
    """A user-facing problem reading a resume file."""


def pdf_to_text(data: bytes) -> str:
    from pypdf import PdfReader  # imported here to keep app startup fast

    try:
        reader = PdfReader(io.BytesIO(data))
        text = "\n\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as e:
        raise ResumeError(f"Couldn't read that PDF: {e}") from e
    text = "\n".join(line.rstrip() for line in text.splitlines()).strip()
    if len(text) < 100:
        raise ResumeError(
            "Almost no text came out of that PDF. It may be a scan or an image, "
            "so paste the text in by hand instead."
        )
    return text


class FoundProject(BaseModel):
    name: str
    summary: str = Field(description="One or two sentences on what it is and does.")
    tech_stack: str = Field(description="Comma-separated, as listed on the resume.")
    role: str = Field(description="Their role or team size, if the resume says. Otherwise empty.")
    dates: str = Field(description="Dates, if the resume says. Otherwise empty.")


class FoundProjects(BaseModel):
    projects: list[FoundProject]


def find_projects(profile: Profile, existing: list[str]) -> list[Project]:
    """Pull project entries out of the resume text, skipping ones already in the profile."""
    lines = [
        f"<resume>\n{profile.resume_text.strip()}\n</resume>",
        "Already in the profile (skip these): " + (", ".join(existing) if existing else "none"),
        prompts.FIND_PROJECTS,
    ]
    found = llm.ask_structured(
        llm.system_blocks(profile.to_prompt(), prompts.FIND_PROJECTS_SYSTEM),
        "\n\n".join(lines),
        FoundProjects,
        effort="medium",
    )
    return [
        Project(name=p.name, summary=p.summary, tech_stack=p.tech_stack, role=p.role, dates=p.dates)
        for p in found.projects
    ]
