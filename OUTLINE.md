# Interviewer — Project Outline

A local app for voice-based mock interviews. You give it your resume, your projects, and your background once.
It asks you the questions a real interviewer would ask, listens to your spoken answers, and tells you what went
well, what didn't, and what to study.

**Main goal:** get better at explaining my own projects, both the high-level story ("what is it and why does it
matter") and the low-level details ("why did you use X, how does Y actually work, what broke").

---

## 1. Core loop

```
Profile (resume, projects, background)
        │
        ▼
Pick a session mode ──► Claude asks a question ──► I answer out loud
                               ▲                          │
                               │                  speech-to-text + timing
                               │                          │
                        follow-up question ◄── Claude evaluates the answer
                                                          │
                                                          ▼
                                           Feedback + what to review
                                                          │
                                                          ▼
                                           Saved to history / weak spots
```

---

## 2. Tech stack

| Piece | Choice | Why |
|---|---|---|
| Language | Python | |
| GUI | **Streamlit** | Fast to build, runs in the browser, has a built-in mic recorder (`st.audio_input`). No frontend code needed. |
| LLM | Claude API (`anthropic` SDK) | Opus 5 for evaluation and feedback, Sonnet 5 for generating questions (cheaper, faster). |
| Speech-to-text | **faster-whisper** (runs locally) | Free and private, and it gives word timestamps, which we need to measure pace and pauses. The Claude API doesn't accept audio directly. |
| Text-to-speech (optional) | `edge-tts` or `pyttsx3` | Reads the question out loud so it feels like a real interview. |
| Storage | JSON files + SQLite in `data/` | Simple. The `data/` folder is gitignored because it holds personal info. |
| Config | `.env` for `ANTHROPIC_API_KEY` | `.env` is gitignored. Commit a `.env.example`. |

> Note: Whisper tends to drop filler words ("um", "uh", "like"). To count them, pass an `initial_prompt`
> containing fillers (e.g. "Umm, so, uh, I, like, built...") so the model transcribes them word for word.

---

## 3. Profile (the "about me" data)

Stored in `data/profile/`, editable at any time from a **Profile** page in the GUI.

- **Resume:** upload a PDF. Claude reads it directly, and the extracted text is saved so you can edit it.
- **Background:** education, target roles, companies, years of experience, what you want next.
- **Projects** (most important). One entry per project:
  - name, one-line summary, tech stack, dates, team size, your role
  - optional **link to the repo or local path**. The app pulls the README and a few key source files so Claude
    can ask *grounded* low-level questions about your actual code, not generic ones.
  - free-form notes (anything you remember: bugs, decisions, results)
- **Job description** (optional): paste a JD to aim a session at a specific role.
- **Story bank:** behavioral stories (conflict, failure, leadership, tight deadline, etc.), built over time.

### 3a. Project Dossier builder (new idea, high value)
Before you can *explain* a project well, you need the facts organized. For each project, Claude interviews
you in a relaxed, non-graded mode to fill gaps, then writes a **project dossier** you can review and edit:

- **The problem:** what it solves and who it's for
- **Architecture:** components and how data flows between them
- **Key technical decisions:** what you chose, what the alternatives were, and why you picked yours
- **Hardest problem / bug:** what happened, how you found it, how you fixed it
- **Impact / numbers:** users, speed, accuracy, scale, time saved
- **Your contribution:** what *you* did vs. the team
- **What you'd do differently / next steps**
- **Concepts you must know cold:** the underlying tech (for example "how does JWT auth work" if you used it)

The dossier becomes the context for every later question about that project, and it doubles as your study sheet.

---

## 4. Question types (diverse but useful)

Each question is tagged with a type so sessions can mix them and history can track them.

**Project-focused (the priority):**
1. **Elevator pitch:** "Tell me about X in 30 seconds." Then 2 minutes. Then 5 minutes.
2. **Drill-down ladder:** begins high-level and goes one level deeper with each follow-up, based on what you
   *just said*: overview → architecture → specific component → implementation detail → edge case.
3. **Why this and not that:** "Why Postgres and not MongoDB?" "Why React instead of plain HTML?"
4. **Debugging story:** "What was the hardest bug? How did you track it down?"
5. **Scaling / what-if:** "What breaks at 100x users?" "How would you add feature Y?"
6. **Explain to a non-engineer:** the same project, pitched to a recruiter or PM.
7. **Concept check:** "You listed Redis. How does it store data? Why is it fast?"
8. **Ownership:** "Which parts did you personally write?"
9. **Retrospective:** "What would you change if you rebuilt it?"

**General:**
10. **Tell me about yourself / walk me through your resume**
11. **Behavioral (STAR):** conflict, failure, leadership, learning something fast, disagreement
12. **Motivation:** why this role, why this company, where you see yourself going
13. **Curveballs:** "What's a weakness?", "What's something you're proud of that isn't on your resume?"
14. **Your questions for them:** practice asking good questions at the end

**Follow-ups:** after each answer, the interviewer can ask 0–3 follow-ups that dig into anything vague,
hand-wavy, or interesting. This is where real interviews expose gaps, so it's central, not optional.

**Variety control:** the question generator is given recent question history so it avoids repeats and keeps
rotating across projects, question types, and depth levels.

---

## 5. Session modes

| Mode | Length | What it does |
|---|---|---|
| **Quick drill** | ~5 min | 2–3 questions, one type or one project |
| **Project deep-dive** | ~15 min | One project, full drill-down ladder with follow-ups |
| **Full mock interview** | ~30 min | Realistic mix: intro → projects → behavioral → your questions |
| **JD-targeted** | ~20 min | Questions chosen to fit a pasted job description |
| **Pitch practice** | ~5 min | Repeat 30s / 90s / 3min versions of one project until they're smooth |
| **Weak-spot review** | varies | Re-asks questions you scored low on before (spaced repetition) |

**Interviewer persona** (optional setting): friendly, neutral, skeptical/pushy, rushed. The skeptical one is good
for practicing when someone keeps pressing.

---

## 6. Feedback

After each answer (and a summary at the end of the session):

**Content** (Claude, returned as structured JSON so the UI can display it consistently):
- Score 1–5 for: **structure**, **clarity**, **technical depth/accuracy**, **specificity** (numbers, concrete
  details), **ownership** ("I" vs. vague "we"), **conciseness**
- What was good (so you keep doing it)
- What was missing or unclear
- Technical errors or shaky claims, if any
- **Stronger version:** your answer rewritten *in your own voice with your own facts*, not a generic script
- **What to review:** specific concepts to study (these feed the review list)

**Delivery** (computed locally from the transcript + timestamps, no API call needed):
- words per minute (target range roughly 130–160)
- filler words per minute, and which ones
- long pauses (> 3s) and where they happened
- total length (flag answers that ramble past ~2–3 min)

**Retry button:** answer the same question again right away and see both attempts side by side.
This is probably the fastest way to improve.

---

## 7. Progress tracking

- **History page:** every session, question, transcript, audio recording, and score
- **Replay audio:** listen to yourself. Uncomfortable, but it works.
- **Trends:** scores and filler rate over time, per question type and per project
- **Weak spots:** questions and concepts that scored low are queued for review
- **Review list / flashcards:** "what to review" items collect into a list you can check off

---

## 8. Other ideas that help (beyond the original plan)

- **Project dossier builder** (section 3a): organizing your knowledge fixes a lot of the stuttering by itself.
- **Pitch ladder:** having practiced 30s / 2min / 5min versions means you never start from nothing.
- **Answer frameworks cheat sheet:** STAR for behavioral answers; for projects, *Problem → Approach → Tech → Challenge → Result → Learned*.
  Feedback points out which part of the framework was missing.
- **"Explain it back" check:** Claude explains a concept from your project wrong on purpose, and you have to
  catch the mistake. This tests real understanding.
- **Thinking-time practice:** practice saying "Good question, let me think about that for a second" instead of
  filling the silence. Delivery feedback counts a deliberate pause as fine.
- **Best-answer bank:** save your best version of each common answer and review it before real interviews.
- **Pre-interview cram sheet:** paste a JD and get a one-page summary: your most relevant projects, the stories
  to use, and the concepts to brush up on.

---

## 9. Project structure

```
interviewer/
├── app.py                  # Streamlit entry point
├── pages/
│   ├── 1_Profile.py        # resume upload, projects, background, dossiers
│   ├── 2_Interview.py      # run a session
│   ├── 3_History.py        # past sessions, replay, trends
│   └── 4_Review.py         # weak spots, review list, best answers
├── interviewer/
│   ├── llm.py              # Claude client, prompt caching, structured output
│   ├── prompts.py          # system prompts for interviewer, evaluator, dossier builder
│   ├── questions.py        # question types, generation, variety control
│   ├── session.py          # session state machine (ask → answer → follow-up → feedback)
│   ├── feedback.py         # content rubric + local delivery metrics
│   ├── speech.py           # faster-whisper STT, optional TTS
│   ├── profile.py          # load/save profile, resume parsing, repo ingestion
│   └── storage.py          # SQLite history
├── data/                   # gitignored: profile, recordings, db
├── .env.example
├── requirements.txt
└── README.md
```

---

## 10. Build phases

1. **MVP (text only):** profile page (paste resume text + projects) → Claude asks a question → you *type* an
   answer → structured feedback. Proves the prompts work.
2. **Voice:** mic input via `st.audio_input` → faster-whisper → transcript → feedback, plus delivery metrics.
3. **Follow-ups and session modes:** drill-down ladder, quick drill, deep-dive, full mock.
4. **Profile depth:** PDF resume upload, repo ingestion, project dossier builder.
5. **History and tracking:** SQLite, history page, audio replay, retry comparison, trends.
6. **Review system:** weak-spot queue, review list, best-answer bank.
7. **Polish:** TTS questions, interviewer personas, JD mode, cram sheet, README for the public repo.

---

## 11. Notes

- **Privacy:** because the repo will be public, `data/`, `.env`, and recordings must be in `.gitignore` from the first commit.
- **Cost:** mark the profile and dossiers as cached in each prompt (prompt caching) so the same large context
  isn't billed at full price every turn. Use Sonnet for question generation and Opus for evaluation.
- **Grounding:** the evaluator should only criticize technical claims it can judge from the profile, dossier,
  repo files, or general knowledge. It should not invent facts about your project.
