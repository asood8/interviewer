# Interviewer

Interview practice built on your own material. It runs a full interview, grades every answer, and follows up
on anything you leave open. Questions come from your resume, your background and your projects, so it asks
about what you actually did.

Runs on your machine and talks to the Claude API. Nothing is hosted.

![An answer with its feedback](docs/screenshots/interview.png)

## What it covers

Fourteen question types across a whole interview:

* Resume and story: tell me about yourself, walk me through your resume
* Behavioral, in STAR shape: conflict, failure, leadership, tight deadlines, learning something fast
* Motivation and curveballs: why this role, weaknesses, what isn't on the resume
* Your questions for them, so the end of the interview gets rehearsed too
* Projects in depth: the 30-second pitch, drill-downs into one component, why you chose X over Y, the
  hardest bug, what breaks at 100x scale, explaining it to a non-engineer, concept checks on the tech you
  listed, what you personally built, and what you'd do differently

Each answer gets six scores (structure, clarity, technical depth, specificity, ownership, conciseness). You
also get what worked, what to tighten, any technical mistakes, and a stronger version of the answer written
in your own words, with `[placeholder]` wherever a fact is missing. Follow-up questions build on what you just
said, so a thin answer gets probed the way it would be in the room.

Spoken answers get delivery feedback too, worked out locally rather than by the model: speaking pace, filler
words, and any pause over three seconds along with the words you said right before it.

## Setup

You need Python 3.12 or newer and an [Anthropic API key](https://console.anthropic.com). The API is
pay-as-you-go and separate from a Claude Pro or Max subscription. A subscription gets you nothing here, so the
API account needs its own credit.

Make a `.env` file next to `app.py` (`copy .env.example .env`) with the key in it:

```
ANTHROPIC_API_KEY=sk-ant-...
```

On Windows, double-click `run.bat`. The first run builds the virtual environment and installs everything,
which takes a few minutes, then starts the app and opens a browser tab. After that it just starts. On macOS
and Linux, `./run.sh` does the same thing. To do it by hand:

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py            # then open http://localhost:8501
```

## How you use it

### Profile

Upload a resume as a PDF or paste the text, then add your projects and background. One button reads the
resume and pulls out the projects it finds. A project can also point at its GitHub repo or a folder on disk.
The app reads the README and the main source files from it, so technical questions land on the code you wrote
instead of the buzzwords in your stack.

### Project prep

Ten quick questions about one project, none of them graded. The answers become a written brief: the problem,
the architecture, the decisions you made and the alternatives you rejected, the hardest bug, the numbers, what
you'd change, and the concepts an interviewer could reasonably ask you to explain. Later questions use the
brief, and it's also the thing to reread before a real interview.

![The written-up project notes](docs/screenshots/project-prep.png)

### Interview

Six modes: free practice, a three-question drill, a deep dive on one project, a full mock interview with
feedback held until the end, a drill aimed at a job posting you paste in, and a weak-spot session that
re-asks whatever scored lowest. The interviewer can be friendly, neutral or skeptical. Skeptical pushes back
on unsupported claims and makes for the better rehearsal.

### Review and history

Study topics collect in one list, with anything that keeps coming back sorted to the top. Low-scoring
questions queue up for another attempt, and when you redo one it shows the old score next to the new one.
Answers worth keeping go in an answer bank. The cram sheet is for the ten minutes before an interview: which
project to lead with, which story fits which question, what to brush up on, and what to ask them.

![Weak spots](docs/screenshots/review-weak.png)
![Session history and trends](docs/screenshots/history.png)

## Cost and privacy

The profile is cached between calls, so a session costs cents rather than dollars. Setting
`INTERVIEWER_MODEL=claude-sonnet-5` in `.env` makes it cheaper again.

Speech-to-text runs locally through [faster-whisper](https://github.com/SYSTRAN/faster-whisper). Recordings
never leave the machine and only the transcript text goes to the API. The first recording downloads the model,
about 500 MB, which takes a minute. After that a one-minute answer takes 20 to 30 seconds to transcribe on a
normal CPU. `WHISPER_MODEL=base.en` in `.env` makes that faster.

Everything else lives in `data/`: the profile, the recordings, and a SQLite file with every session. That
folder and `.env` are gitignored, and the app only listens on localhost.

## Rough edges

Reading questions aloud uses the system voice, which needs `espeak` on Linux and sounds robotic everywhere
else. Filler-word counting depends on Whisper transcribing "um", which it usually does but not always. The
screenshots above use a sample profile rather than real data.

[OUTLINE.md](OUTLINE.md) has the original plan and the reasoning behind it.

## License

MIT. See [LICENSE](LICENSE).
