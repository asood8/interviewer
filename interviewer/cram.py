"""A one-page sheet to read just before a real interview."""

from pydantic import BaseModel, Field

from interviewer import llm, prompts
from interviewer.profile import Profile


class CramSheet(BaseModel):
    summary: str = Field(description="2-4 sentences: how to pitch yourself for this interview.")
    lead_with: list[str] = Field(description="The projects and experience to lead with, and why they fit.")
    stories: list[str] = Field(description="Which of their stories to use for which likely question.")
    concepts: list[str] = Field(description="Concepts to brush up, most likely to come up first.")
    watch_outs: list[str] = Field(description="Their own habits to avoid, from past feedback.")
    questions_to_ask: list[str] = Field(description="Good questions for them to ask the interviewer.")


SECTIONS = [
    ("lead_with", "Lead with"),
    ("stories", "Stories to use"),
    ("concepts", "Brush up on"),
    ("watch_outs", "Watch out for"),
    ("questions_to_ask", "Ask them"),
]


def make_cram_sheet(profile: Profile, job_description: str, review_topics: list[str], weak_spots: list[str]) -> CramSheet:
    parts = []
    if job_description.strip():
        parts.append(f"<job_description>\n{job_description.strip()}\n</job_description>")
    if review_topics:
        parts.append("<review_list>\n" + "\n".join(f"- {t}" for t in review_topics[:40]) + "\n</review_list>")
    if weak_spots:
        parts.append("<weak_answers>\n" + "\n".join(f"- {w}" for w in weak_spots[:20]) + "\n</weak_answers>")
    parts.append(prompts.CRAM_SHEET)
    return llm.ask_structured(
        llm.system_blocks(profile.to_prompt(), prompts.EVALUATOR),
        "\n\n".join(parts),
        CramSheet,
        effort="high",
    )


def to_markdown(sheet: CramSheet, title: str = "Cram sheet") -> str:
    lines = [f"# {title}", "", sheet.summary]
    for key, heading in SECTIONS:
        if items := getattr(sheet, key):
            lines += ["", f"## {heading}", ""] + [f"- {item}" for item in items]
    return "\n".join(lines) + "\n"
