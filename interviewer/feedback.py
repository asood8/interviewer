"""Grading answers, and summarizing a whole session, with Claude."""

from pydantic import BaseModel, Field

from interviewer import llm, prompts
from interviewer.delivery import Delivery
from interviewer.profile import Profile
from interviewer.questions import QUESTION_TYPES, Question, format_thread


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


class SessionSummary(BaseModel):
    overall: str
    patterns: list[str]
    priorities: list[str]
    review_topics: list[str]


def evaluate(
    profile: Profile,
    question: Question,
    answer: str,
    delivery: Delivery | None = None,
    earlier: list[tuple[Question, str]] | None = None,
) -> Feedback:
    """Grade one answer. `earlier` is the conversation leading up to a follow-up question."""
    qtype = QUESTION_TYPES[question.type_key]
    covers = "\n".join(f"- {c}" for c in question.strong_answer_covers)
    parts = [f"Question type: {qtype.label}" + (f'\nProject: "{question.project_name}"' if question.project_name else "")]
    if earlier:
        parts.append(
            "This question is a follow-up. Earlier in the conversation:\n"
            + format_thread(earlier)
            + "\nGrade only the answer to the follow-up below, in the context of that conversation."
        )
    parts += [
        f"<question>\n{question.text}\n</question>",
        f"<strong_answer_covers>\n{covers}\n</strong_answer_covers>",
        f"<candidate_answer>\n{answer.strip()}\n</candidate_answer>",
        f"<delivery>\n{delivery.to_prompt()}\n</delivery>" if delivery else "Typed answer.",
        "Evaluate the answer.",
    ]
    return llm.ask_structured(
        llm.system_blocks(profile.to_prompt(), prompts.EVALUATOR),
        "\n\n".join(parts),
        Feedback,
        effort="high",
    )


def summarize(profile: Profile, answered: list[tuple[Question, str, Feedback, Delivery | None]]) -> SessionSummary:
    blocks = []
    for i, (q, answer, fb, delivery) in enumerate(answered, 1):
        kind = "follow-up" if q.is_follow_up else QUESTION_TYPES[q.type_key].label
        lines = [
            f'<turn number="{i}" kind="{kind}">',
            f"<question>{q.text}</question>",
            f"<answer>{answer.strip()}</answer>",
            f"<scores>{fb.scores.model_dump_json()}</scores>",
            f"<feedback_summary>{fb.summary}</feedback_summary>",
            "<improvements>" + " | ".join(fb.improvements) + "</improvements>",
            "<review_topics>" + " | ".join(fb.review_topics) + "</review_topics>",
        ]
        if delivery:
            lines.append(f"<delivery>{delivery.to_prompt()}</delivery>")
        lines.append("</turn>")
        blocks.append("\n".join(lines))
    return llm.ask_structured(
        llm.system_blocks(profile.to_prompt(), prompts.EVALUATOR),
        "\n\n".join(blocks) + "\n\n" + prompts.SUMMARY,
        SessionSummary,
        effort="high",
    )
