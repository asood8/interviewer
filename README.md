# Interviewer

A mock interviewer that only asks about your own resume and projects. You answer out loud, it tells you what
was weak. Built for the gap between having good projects and being able to explain them: the questions get
more specific than "what does it do", which is usually where answers fall apart.

It runs on your machine and talks to the Claude API. Nothing is hosted.

![An answer with its feedback](docs/screenshots/interview.png)

## What it actually does

You give it your resume and a page of notes per project. It asks the kind of question an interviewer would
ask about *that* project, you answer out loud, and it grades the answer: six scores, what worked, what to
fix, anything you got technically wrong, and a rewritten version of your answer in your own words with
`[placeholder]` wherever a fact is missing. Then it usually follows up on whatever was vague, which is where
real interviews find the gaps.

Spoken answers get a second kind of feedback the model isn't involved in: speaking pace, how many times you
said "um", and where you paused for more than three seconds. The pauses are the interesting part, since they
tend to land exactly where the prepared material ran out.

## Setup

You need Python 3.12 or newer and an [Anthropic API key](https://console.anthropic.com). Note that the API is
pay-as-you-go and separate from a Claude Pro or Max subscription: the subscription gets you nothing here, the
API account needs its own credit.

Make a `.env` file next to `app.py` (`copy .env.example .env`) with the key in it:

```
ANTHROPIC_API_KEY=sk-ant-...
```

On Windows, double-click `run.bat`. The first run builds the virtual environment and installs everything,
which takes a few minutes, then it starts the app and opens a browser tab. After that it just starts.
On macOS and Linux, `./run.sh` does the same thing. To do it by hand:

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py            # then open http://localhost:8501
```

## How you use it

**Start with the profile.** Upload a resume as a PDF or paste the text in, then add the projects. There's a
button that reads the resume and pulls out the projects it finds, which saves some typing. A project can also
point at its GitHub repo or a folder on disk, and the app reads the README and main source files so questions
can get into the actual code.

**Then do the project prep.** It asks about ten questions on one project, nothing graded, and writes up the
answers: the problem, how it's built, the decisions made and the ones rejected, the hardest bug, the numbers,
what you'd change. Every question after that is grounded in these notes. The writeup is also the thing worth
rereading before an interview, since most stumbling comes from never having said any of it out loud in order.

![The written-up project notes](docs/screenshots/project-prep.png)

**Then interview.** Six modes: free practice, a three-question drill, a deep dive on one project, a full mock
interview (feedback held until the end, like the real thing), a drill aimed at a job posting you paste in, and
a weak-spot session that re-asks the questions you did worst on. The interviewer can be friendly, neutral or
skeptical. Skeptical pushes back on anything unsupported, which is uncomfortable and more useful.

**Review and history.** Everything Claude says to study piles up in one list, and topics that keep coming back
sort to the top. The worst-scoring questions are listed separately for another attempt, and when you redo one
it shows the old score next to the new one. There's also a cram sheet for the ten minutes before a real
interview: which project to lead with, which story to use where, what to brush up on, and which habits to
watch for.

![Weak spots](docs/screenshots/review-weak.png)
![Session history and trends](docs/screenshots/history.png)

## Cost and privacy

The profile is cached between calls, so a session costs cents rather than dollars. Setting
`INTERVIEWER_MODEL=claude-sonnet-5` in `.env` makes it cheaper again.

Speech-to-text runs locally through [faster-whisper](https://github.com/SYSTRAN/faster-whisper), so recordings
never leave the machine; only the transcript text goes to the API. The first recording downloads the model,
about 500 MB, which takes a minute. After that a one-minute answer takes 20-30 seconds to transcribe on a
normal CPU, and `WHISPER_MODEL=base.en` in `.env` makes that faster.

Everything else lives in `data/`: the profile, the recordings, and a SQLite file with every session. That
folder and `.env` are gitignored, and the app only listens on localhost.

## Rough edges

Reading questions aloud uses the system voice, which needs `espeak` on Linux and sounds like a robot
everywhere. The filler-word counting depends on Whisper transcribing "um", which it does most of the time but
not always. The screenshots above use a sample profile rather than real data.

[OUTLINE.md](OUTLINE.md) has the original plan and the reasoning behind it.

## License

MIT. See [LICENSE](LICENSE).
