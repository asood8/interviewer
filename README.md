# Interviewer

A local mock-interview app that practices you on **your own** resume and projects. Claude asks the kind of
questions a real interviewer would (from high-level pitches down to low-level "how does that part work"),
then grades your answer, shows a stronger version in your own voice, and tells you what to review.

See [OUTLINE.md](OUTLINE.md) for the full plan. Right now it's **phase 1**: you type your answers. Voice answers come in phase 2.

## Setup

Requires Python 3.12+ and an [Anthropic API key](https://console.anthropic.com).

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
cp .env.example .env            # then put your key in .env
streamlit run app.py
```

## Using it

1. **Profile**: paste your resume, add your background, and add each project with as much detail as you can
   (tech stack, your role, decisions, bugs, numbers). It saves automatically to `data/profile.json`.
2. **Interview**: pick a question type, project, and depth in the sidebar (or leave it on Mixed), press
   **Start**, answer, and submit. Use **Try this question again** to redo an answer right after reading the feedback.

Your profile and answers stay on your machine except for what's sent to the Claude API. `data/` and `.env`
are gitignored.
