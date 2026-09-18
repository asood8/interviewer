# Interviewer

A local mock-interview app that practices you on **your own** resume and projects. Claude asks the kind of
questions a real interviewer would (from high-level pitches down to low-level "how does that part work"),
then grades your answer, shows a stronger version in your own voice, and tells you what to review.

See [OUTLINE.md](OUTLINE.md) for the full plan. Phases 1-3 are done: session modes, follow-up questions, and
spoken or typed answers. Spoken answers also get delivery feedback (pace, ums and uhs, long pauses, length).

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
2. **Interview**: pick a mode:
   - **Free practice**: choose the question type, project, and depth yourself, as many questions as you like
   - **Quick drill**: 3 questions plus follow-ups
   - **Project deep-dive**: one project, from the elevator pitch down to implementation details
   - **Full mock interview**: intro, projects, behavioral, and your questions for them, with feedback held until the end

   Record your answer with the mic (or switch to typing in the sidebar), fix any misheard words in the
   transcript, and submit. The interviewer follows up on what you actually said when there's something to dig
   into, like a vague claim or a detail worth going deeper on. You can also pick a friendly, neutral, or skeptical
   interviewer. Every session ends with a debrief: average scores, patterns across your answers, and what to work on next.

Speech-to-text runs locally with [faster-whisper](https://github.com/SYSTRAN/faster-whisper). The first
recording downloads the speech model (about 500 MB for `small.en`), which takes a minute. After that, a one-minute
answer takes roughly 20-30 seconds to transcribe on a typical CPU. Set `WHISPER_MODEL=base.en` in `.env` if
that's too slow.

Your profile and recordings stay on your machine. Only the text transcript is sent to the Claude API. `data/` and `.env`
are gitignored.
