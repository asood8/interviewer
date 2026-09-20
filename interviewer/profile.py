"""The candidate profile: resume, background, and projects, stored as JSON in data/."""

import uuid
from pathlib import Path

from pydantic import BaseModel, Field

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
PROFILE_PATH = DATA_DIR / "profile.json"


# Dossier sections, in the order they're written and displayed.
DOSSIER_SECTIONS = {
    "problem": "The problem",
    "architecture": "How it's built",
    "decisions": "Key decisions",
    "hardest_problem": "Hardest problem",
    "impact": "Results and numbers",
    "contribution": "What I built",
    "what_id_change": "What I'd do differently",
}
DOSSIER_LISTS = {
    "concepts_to_know": "Concepts to know cold",
    "open_questions": "Still to find out",
}


class Dossier(BaseModel):
    """Organized notes about one project: the facts, ready to study and to ground questions in."""

    problem: str = ""
    architecture: str = ""
    decisions: str = ""
    hardest_problem: str = ""
    impact: str = ""
    contribution: str = ""
    what_id_change: str = ""
    concepts_to_know: list[str] = []
    open_questions: list[str] = []

    def is_empty(self) -> bool:
        return not any(getattr(self, f).strip() for f in DOSSIER_SECTIONS)

    def to_prompt(self) -> str:
        parts = [f"{label}: {getattr(self, key).strip()}" for key, label in DOSSIER_SECTIONS.items() if getattr(self, key).strip()]
        for key, label in DOSSIER_LISTS.items():
            if items := [i for i in getattr(self, key) if i.strip()]:
                parts.append(f"{label}: " + "; ".join(items))
        return "\n".join(parts)


class Project(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:8])
    name: str = ""
    summary: str = ""
    tech_stack: str = ""
    role: str = ""
    dates: str = ""
    notes: str = ""
    dossier: Dossier | None = None
    repo: str = ""  # GitHub URL or local folder
    code: str = ""  # digest of that repo, from interviewer.repo.digest
    code_updated: str = ""  # when the digest was taken


class Profile(BaseModel):
    name: str = ""
    target_roles: str = ""
    background: str = ""
    resume_text: str = ""
    other: str = ""
    projects: list[Project] = []

    def is_empty(self) -> bool:
        return not (self.resume_text.strip() or self.background.strip() or self.named_projects())

    def named_projects(self) -> list[Project]:
        return [p for p in self.projects if p.name.strip()]

    def to_prompt(self) -> str:
        """Render the profile as tagged text for Claude. Deterministic, so it caches well."""
        parts = ["<candidate_profile>"]
        for tag, value in [
            ("name", self.name),
            ("target_roles", self.target_roles),
            ("background", self.background),
            ("resume", self.resume_text),
            ("other_info", self.other),
        ]:
            if value.strip():
                parts.append(f"<{tag}>\n{value.strip()}\n</{tag}>")
        for p in self.named_projects():
            fields = [
                ("summary", p.summary),
                ("tech_stack", p.tech_stack),
                ("role", p.role),
                ("dates", p.dates),
                ("notes", p.notes),
            ]
            body = "\n".join(f"{k}: {v.strip()}" for k, v in fields if v.strip())
            if p.dossier and not p.dossier.is_empty():
                body += f"\n<dossier>\n{p.dossier.to_prompt()}\n</dossier>"
            if p.code.strip():
                body += f"\n<code>\n{p.code.strip()}\n</code>"
            parts.append(f'<project name="{p.name.strip()}">\n{body}\n</project>')
        parts.append("</candidate_profile>")
        return "\n\n".join(parts)


def load_profile() -> Profile:
    if PROFILE_PATH.exists():
        return Profile.model_validate_json(PROFILE_PATH.read_text(encoding="utf-8"))
    return Profile()


def save_profile(profile: Profile) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    PROFILE_PATH.write_text(profile.model_dump_json(indent=2), encoding="utf-8")
