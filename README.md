# Interviewer

I have decent projects on my resume and I'm bad at talking about them. Ask me anything more specific than
"what does it do" and I lose the thread. So I built this: a mock interviewer that only asks about my own
resume and projects, listens to me answer out loud, and then tells me what was weak.

It runs on your machine and talks to the Claude API. Nothing is hosted.

![An answer with its feedback](docs/screenshots/interview.png)

## What it actually does

You give it your resume and a page of notes per project. It asks the kind of question an interviewer would
ask about *that* project, you answer out loud, and it grades the answer: six scores, what worked, what to
fix, anything you got technically wrong, and a rewritten version of your answer in your own words with
`[placeholder]` wherever you're missing a fact. Then it usually follows up on whatever you were vague about,
which is the part I found most useful and least comfortable.

Spoken answers get a second kind of feedback the model isn't involved in: speaking pace, how many times you
said "um", and where you paused for more than three seconds. The pauses are the interesting bit, since they
land exactly where you ran out of prepared material.

## Setup

You need Python 3.12 or newer and an [Anthropic API key](https://console.anthropic.com). Note that the API is
pay-as-you-go and separate from a Claude Pro or Max subscription: the subscription gets you nothing here, you
have to put a few dollars of credit on the API account.

Make a `.env` file next to `app.py` (`copy .env.example .env`) with your key in it:

```
ANTHROPIC_API_KEY=sk-ant-...
```

On Windows, double-click `run.bat`. The first run builds the virtual environment and installs everything,
which takes a few minutes, then it starts the app and opens a browser tab. After that it just starts.
On macOS and Linux, `./run.sh` does the same thing. If you'd rather do it by hand:

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py            # then open http://localhost:8501
```

## How you use it

**Start with your profile.** Upload your resume as a PDF or paste the text in, then add your projects.
There's a button that reads the resume and pulls out the projects it finds, which saves some typing. You can
also point a project at its GitHub repo or a folder on disk, and it'll read the README and the main source
files so the questions can get into your actual code.

**Then do the project prep.** This is the part I'd skip if I were you, and I'd be wrong to. It asks about ten
questions about one project, nothing graded, and writes up what you tell it: the problem, how it's built, the
decisions you made and what you rejected, the hardest bug, the numbers, what you'd change. Every question
after that is grounded in these notes, and honestly the writeup alone fixed half my problem, because most of
my stumbling was never having said this stuff out loud in order.

![The written-up project notes](docs/screenshots/project-prep.png)

**Then interview.** Six modes: free practice, a three-question drill, a deep dive on one project, a full mock
interview (feedback held until the end, like the real thing), a drill aimed at a job posting you paste in, and
a weak-spot session that re-asks the questions you did worst on. You can make the interviewer friendly,
neutral or skeptical. Skeptical is unpleasant and probably the most useful.

**Review and history.** Everything Claude tells you to study piles up in one list, and topics that keep coming
back sort to the top. Your worst-scoring questions are listed separately so you can go again at them, and when
you do, it shows the old score next to the new one. There's also a cram sheet for the ten minutes before a
real interview: which project to lead with, which story to use where, what to brush up on, and your own bad
habits to watch for.

![Weak spots](docs/screenshots/review-weak.png)
![Session history and trends](docs/screenshots/history.png)

## Cost and privacy

Your profile is cached between calls, so a session costs cents rather than dollars. If you want it cheaper,
put `INTERVIEWER_MODEL=claude-sonnet-5` in `.env`.

Speech-to-text runs locally through [faster-whisper](https://github.com/SYSTRAN/faster-whisper), so your
recordings never leave the machine; only the transcript text goes to the API. The first recording downloads
the model, about 500 MB, which takes a minute. After that a one-minute answer takes 20-30 seconds to
transcribe on a normal CPU, and `WHISPER_MODEL=base.en` in `.env` makes that faster if you're impatient.

Everything else lives in `data/`: your profile, the recordings, and a SQLite file with every session. That
folder and `.env` are gitignored, and the app only listens on localhost.

## Rough edges

Reading questions aloud uses the system voice, which needs `espeak` on Linux and sounds like a robot
everywhere. The filler-word counting depends on Whisper transcribing "um", which it does most of the time but
not always. The screenshots above use a made-up profile, not mine.

[OUTLINE.md](OUTLINE.md) has the original plan and the reasoning behind it, if you want to see where this was
going.

## License

MIT. See [LICENSE](LICENSE).
