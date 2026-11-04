# Imtihan Buddy 📘

![CI](../../actions/workflows/ci.yml/badge.svg)

Exam prep for Pakistani Matric and Intermediate students, built on the student's **own textbook chapter**.
Upload a chapter (PDF, DOCX, TXT or a phone photo), then get board-style questions, answers checked against the
chapter, and explanations in English, اردو or Roman Urdu. Powered by the Claude API.

## Features
- Upload PDF / DOCX / TXT / phone photos (read with Claude vision); preview and fix the extracted text
- MCQs, short, long, fill-in-the-blank, true/false and numericals, with a source reference on every question
- Practice mode (instant feedback) and timed Mock Test mode
- Rubric-based grading of written or handwritten answers, grounded only in the chapter
- Trilingual explanations with proper RTL Urdu (Noto Nastaliq Urdu)
- Weak-topic breakdown, "Revise weak areas", bookmarks, optional saved history
- Chapter Q&A and summary, DOCX export of quiz + answer key

## Quick start
```bash
git clone https://github.com/<your-username>/imtihan-buddy.git
cd imtihan-buddy
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # then add your ANTHROPIC_API_KEY
streamlit run app.py
pytest -q
```

## Configuration
- Model: `MODEL` in `core/llm.py`
- Per-session request cap: `MAX_CALLS` in `core/llm.py`
- **Never commit `.streamlit/secrets.toml`** (it is git-ignored)

## Deploy on Streamlit Community Cloud
1. Push this repo to GitHub.
2. On share.streamlit.io choose the repo, branch `main`, main file `app.py`.
3. In *Advanced settings > Secrets* paste: `ANTHROPIC_API_KEY = "sk-ant-..."`

## Project layout
```
app.py            UI and routing (tabs)
prompts.py        all system prompts
styles.py         CSS
core/             ingest, retrieval, llm, generate, grade, explain, models, db, export
tests/            unit tests (chunking, JSON validation, MCQ checking)
```

## Cost notes
A 10-question batch sends up to ~12k characters of chapter text; grading and explanations send only the most
relevant chunks. Photos cost one vision call each. The per-session cap limits spend.

## Privacy and copyright
Chapters stay in the session and are not stored. History is opt-in and keyed by a nickname (no login); on Community
Cloud the SQLite file is ephemeral. Use only material you have the right to study from.

## Roadmap
PDF export with Urdu font, per-user history, scanned-PDF support, page-level references, spaced repetition.

## License
MIT
