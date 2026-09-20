# Interviewer

A local mock-interview app that practices you on **your own** resume and projects. Claude asks the kind of
questions a real interviewer would (from high-level pitches down to low-level "how does that part work"),
then grades your answer, shows a stronger version in your own voice, and tells you what to review.

See [OUTLINE.md](OUTLINE.md) for the full plan; all of it is built.

## Setup

Requires Python 3.12+ and an [Anthropic API key](https://console.anthropic.com). The API is pay-as-you-go and
billed separately from a Claude Pro or Max subscription, which does **not** include API credit.

Put your key in a `.env` file first (`copy .env.example .env`, then edit it):

```
ANTHROPIC_API_KEY=sk-ant-...
```

**Windows:** double-click `run.bat`. The first run creates the virtual environment and installs everything,
then starts the app and opens your browser. Later runs just start it.

**Everything else:**

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py            # then open http://localhost:8501
```

The app listens on this computer only, so nothing is served to your network.

## Using it

1. **Profile**: upload your resume as a PDF (or paste the text), add your background, and add each project
   with as much detail as you can: tech stack, your role, decisions, bugs, numbers. **Find projects in my
   resume** pulls project entries out of the resume so you don't have to type them. Each project can also
   point at a **repo** (a GitHub URL or a folder on your computer); Claude reads the README and main source
   files so it can ask about the code you actually wrote. It all saves automatically to `data/profile.json`.
2. **Project prep** (do this before your first interview): Claude asks you about one project, about 10
   questions, nothing graded, then writes up the notes: the problem, how it's built, your key decisions, the
   hardest bug, the numbers, what you personally built, what you'd change, the concepts you should know cold,
   and the facts you still need to go find out. Edit anything it got wrong. Every later question and
   evaluation is grounded in these notes, so questions get much more specific.
3. **Interview**: pick a mode:
   - **Free practice**: choose the question type, project, and depth yourself, as many questions as you like
   - **Quick drill**: 3 questions plus follow-ups
   - **Project deep-dive**: one project, from the elevator pitch down to implementation details
   - **Full mock interview**: intro, projects, behavioral, and your questions for them, with feedback held until the end
   - **Job-description drill**: paste a posting and get questions aimed at that role
   - **Weak-spot review**: re-answer the questions you scored lowest on

   Record your answer with the mic (or switch to typing in the sidebar), fix any misheard words in the
   transcript, and submit. The interviewer follows up on what you actually said when there's something to dig
   into, like a vague claim or a detail worth going deeper on. You can also pick a friendly, neutral, or skeptical
   interviewer, and have the questions read out loud by your computer's voice. Every session ends with a
   debrief: average scores, patterns across your answers, and what to work on next.

4. **Review**: everything Claude told you to study, collected in one list (repeats float to the top, tick
   them off as you go); your **weak spots**, the questions your latest answers scored lowest on, which you can
   re-answer in a weak-spot review session that shows whether the second attempt beat the first; and your
   **answer bank** of answers worth keeping, saved with the ⭐ button under any answer's feedback. The
   **cram sheet** tab writes the page to read ten minutes before a real interview: what to lead with, which
   of your stories to use, what to brush up on, your own habits to avoid, and what to ask them.
5. **History**: every session is saved as you go, so nothing is lost if you close the app. Reopen any past
   session with its feedback, replay your own recordings, and watch your average score and filler-word rate
   over time.

Speech-to-text runs locally with [faster-whisper](https://github.com/SYSTRAN/faster-whisper). The first
recording downloads the speech model (about 500 MB for `small.en`), which takes a minute. After that, a one-minute
answer takes roughly 20-30 seconds to transcribe on a typical CPU. Set `WHISPER_MODEL=base.en` in `.env` if
that's too slow.

Your profile, recordings, and session history stay on your machine, in `data/` (profile JSON, `history.db`,
and the recordings). Only text is sent to the Claude API. `data/` and `.env` are gitignored.
