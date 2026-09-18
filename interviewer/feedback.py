"""Grading an answer with Claude."""

from pydantic import BaseModel, Field

from interviewer import llm, prompts
from interviewer.delivery import Delivery
from interviewer.profile import Profile
from interviewer.questions import QUESTION_TYPES, Question


class Scores(BaseModel):
    structure: int = Field(description="1-5")
    clarity: int = Field(description="1-5")
    depth: int = Field(description="1-5")
    specificity: int = Field(description="1-5")
    ownership: int = Field(description="1-5")
    conciseness: int = Field(description="1-5")


class Feedback(BaseModel):
    summary: str = Field(description="2-3 sentence overall verdict, addressed to the candidate as 'you'.")
    scores: Scores
    strengths: list[str] = Field(description="What worked and should be kept.")
    improvements: list[str] = Field(description="The most important things to fix, most important first.")
    technical_issues: list[str] = Field(description="Incorrect or shaky technical claims. Empty if none.")
    missed_points: list[str] = Field(description="Points a strong answer covers that this answer missed.")
    stronger_answer: str = Field(description="A stronger version of the answer in the candidate's voice.")
    review_topics: list[str] = Field(description="Concrete things to study or prepare before the next interview.")


def evaluate(profile: Profile, question: Question, answer: str, delivery: Delivery | None = None) -> Feedback:
    qtype = QUESTION_TYPES[question.type_key]
    covers = "\n".join(f"- {c}" for c in question.strong_answer_covers)
    user = (
        f"Question type: {qtype.label}\n"
        + (f'Project: "{question.project_name}"\n' if question.project_name else "")
        + f"<question>\n{question.text}\n</question>\n\n"
        f"<strong_answer_covers>\n{covers}\n</strong_answer_covers>\n\n"
        f"<candidate_answer>\n{answer.strip()}\n</candidate_answer>\n\n"
        + (f"<delivery>\n{delivery.to_prompt()}\n</delivery>\n\n" if delivery else "Typed answer.\n\n")
        + "Evaluate the answer."
    )
    return llm.ask_structured(
        llm.system_blocks(profile.to_prompt(), prompts.EVALUATOR),
        user,
        Feedback,
        effort="high",
    )
