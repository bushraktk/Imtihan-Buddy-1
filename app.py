"""Imtihan Buddy - Streamlit entry point (tabs: Upload / Practice / Mock / Progress / Ask)."""
import html, time
import pandas as pd
import streamlit as st
import styles
from core import db, explain, export, generate, grade, ingest, llm
from core.llm import LLMError

st.set_page_config(page_title="Imtihan Buddy", page_icon="📘", layout="centered")
S = st.session_state
LANGS = ["English", "اردو", "Roman Urdu"]
LC = {"English": "en", "اردو": "ur", "Roman Urdu": "rur"}
TYPES = {"MCQs": "mcq", "Short (2-3 marks)": "short", "Long (5-8 marks)": "long", "Fill in the blanks": "fill",
         "True/False": "tf", "Numericals": "numerical"}
SUBJECTS = ["Physics", "Chemistry", "Biology", "Mathematics", "Computer Science", "English", "Other"]
MSG = {
    "busy": {"en": "Server is busy or internet is slow. Please try again in a moment.",
             "ur": "سرور مصروف ہے یا انٹرنیٹ سست ہے۔ براہِ کرم تھوڑی دیر بعد دوبارہ کوشش کریں۔",
             "rur": "Server busy hai ya internet slow hai. Thori der baad dobara koshish karein."},
    "format": {"en": "The AI reply was malformed. Please tap again.",
               "ur": "جواب درست شکل میں نہیں آیا۔ دوبارہ ٹیپ کریں۔",
               "rur": "Jawab sahi format mein nahi aaya. Dobara tap karein."},
    "cap": {"en": "Session limit reached. Reload the page to start a new session.",
            "ur": "اس سیشن کی حد پوری ہو گئی۔ نیا سیشن شروع کرنے کے لیے صفحہ ری لوڈ کریں۔",
            "rur": "Is session ki limit poori ho gayi. Naya session shuru karne ke liye page reload karein."},
    "key": {"en": "API key missing or invalid. Add ANTHROPIC_API_KEY to secrets.",
            "ur": "API کلید موجود نہیں یا غلط ہے۔ secrets میں ANTHROPIC_API_KEY شامل کریں۔",
            "rur": "API key maujood nahi ya ghalat hai. Secrets mein ANTHROPIC_API_KEY add karein."}}
MICRO = {"en": ("Well done!", "Not quite. Keep going!"), "ur": ("شاباش!", "کوئی بات نہیں، دوبارہ کوشش کریں"),
         "rur": ("Shabash!", "Koi baat nahi, dobara koshish karein")}

for k, v in dict(lang="English", quizzes={"practice": None, "mock": None}, bookmarks={}, chat=[], expl={},
                 seen=[], summary=None, text_edit="", title="").items():
    S.setdefault(k, v)


def card(text: str, lang: str = "English", cls: str = "") -> None:
    """Render escaped text in a card; Urdu gets RTL + Nastaliq."""
    ur = lang == "اردو"
    body = html.escape(str(text)).replace("$", "&#36;").replace("\n", "<br>")
    st.markdown(f'<div class="card {cls} {"ur" if ur else ""}" dir="{"rtl" if ur else "ltr"}">{body}</div>',
                unsafe_allow_html=True)


def safe(fn, *a, **k):
    """Run an LLM-backed call; show a friendly localized error and return None on failure."""
    try:
        return fn(*a, **k)
    except LLMError as e:
        st.error(MSG[e.kind][LC[S.lang]])
    return None


@st.cache_data(show_spinner=False)
def build_chunks(text: str):
    return ingest.chunk_text(text)


def chunks():
    return build_chunks(S.get("text_edit", ""))


def ctx(query: str = "") -> str:
    from core import retrieval
    return retrieval.select_context(chunks(), query)


# ---------------------------------------------------------------- sidebar
size = st.sidebar.slider("Text size", 14, 24, 16)
styles.inject(size)
st.sidebar.toggle("Save my history (optional)", key="save_opt")
if S.get("save_opt"):
    st.sidebar.text_input("Nickname (no real name needed)", key="profile")
st.sidebar.caption(f"Requests this session: {S.get('_calls', 0)}/{llm.MAX_CALLS}")
st.sidebar.info("🔒 Your chapter stays in this session and is not stored. No personal data is collected.\n\n"
                "📚 Use only material you have the right to study from.")

st.markdown("### 📘 Imtihan Buddy")
st.radio("Language / زبان", LANGS, horizontal=True, key="lang", label_visibility="collapsed")
t_up, t_pr, t_mk, t_pg, t_ask = st.tabs(["Upload", "Practice", "Mock Test", "Progress", "Ask"])


# ---------------------------------------------------------------- upload
with t_up:
    files = st.file_uploader("Chapter: PDF, photo, DOCX or TXT", type=["pdf", "jpg", "jpeg", "png", "docx", "txt"],
                             accept_multiple_files=True)
    pasted = st.text_area("...or paste text", height=100)
    st.selectbox("Class", [9, 10, 11, 12], key="cls")
    st.selectbox("Subject", SUBJECTS, key="subject")
    st.selectbox("Board (optional)", ["", "Punjab", "Sindh", "KPK", "Federal", "Balochistan", "AJK"], key="board")
    st.selectbox("Question language", LANGS, key="qlang_sel")
    if st.button("📖 Read my chapter", type="primary"):
        parts = []
        with st.spinner("Reading your chapter..."):
            for f in files or []:
                try:
                    parts.append(ingest.extract(f.name, f.getvalue()))
                except LLMError as e:
                    st.error(MSG[e.kind][LC[S.lang]])
                except Exception as e:
                    st.warning(f"{f.name}: {e}")
            if pasted.strip():
                parts.append(pasted)
        if parts:
            S["text_edit"] = ingest.clean_text("\n\n".join(parts))
            S["title"] = ingest.guess_title(S["text_edit"])
            S.summary, S.expl, S.seen = None, {}, []
    if S.get("text_edit"):
        w = ingest.quality_warning(S["text_edit"])
        if w:
            st.warning(w)
        st.text_input("Chapter title", key="title")
        st.text_area("Here's what we read from your chapter. Fix errors or delete junk:", key="text_edit", height=300)
        st.caption(f"{len(chunks())} sections detected.")


# ---------------------------------------------------------------- quiz helpers
def start_quiz(mode: str, cfg: dict, weak: list[str] | None = None) -> None:
    with st.spinner("Writing questions from your chapter..."):
        qs = safe(generate.generate_questions, chunks(), cls=S.cls, subject=S.subject, board=S.board,
                  types=cfg["types"], n=cfg["n"], difficulty=cfg["diff"], focus=cfg["focus"],
                  qlang=cfg["qlang"], existing=S.seen[-40:], weak=weak)
    if not qs:
        if qs is not None:
            st.warning("No questions came back. Try again or change the settings.")
        return
    S.seen += [q.question for q in qs]
    S.quizzes[mode] = dict(qs=qs, i=0, res={}, ans={}, t0=time.time(), limit=cfg.get("mins", 0), done=False,
                           saved=False, cfg=cfg, qlang=cfg["qlang"], title=S.title, secs=0)
    st.rerun()


def evaluate(q, resp, img) -> dict:
    mx = float(q.marks)
    if q.qtype in grade.OBJECTIVE:
        ok = grade.check_objective(q, resp)
        return dict(score=mx if ok else 0.0, max=mx, ok=ok, grade=None)
    text = (resp or "").strip()
    if img:
        text = (text + "\n" + llm.ocr_image(ingest.shrink(img))).strip()
    if not text:
        return dict(score=0.0, max=mx, ok=False, grade=None)
    g = grade.grade_written(q, text, ctx(q.question + " " + q.source_ref), LC[S.lang], S.subject)
    return dict(score=g.score, max=mx, ok=g.score >= 0.7 * mx, grade=g)


def answer_widget(q, key: str, disabled: bool):
    if q.qtype == "mcq":
        return st.radio("Choose one", range(4), index=None, key=key, disabled=disabled,
                        format_func=lambda k: f"{'ABCD'[k]}. {q.options[k]}"), None
    if q.qtype == "tf":
        return st.radio("True or false?", ["True", "False"], index=None, key=key, disabled=disabled,
                        horizontal=True), None
    if q.qtype == "fill":
        return st.text_input("Your answer", key=key, disabled=disabled), None
    txt = st.text_area("Your answer (English, اردو or Roman Urdu)", key=key, height=160, disabled=disabled)
    up = st.file_uploader("...or a photo of your handwritten answer", type=["jpg", "jpeg", "png"],
                          key=key + "_img", disabled=disabled)
    return txt, (up.getvalue() if up else None)


def correct_text(q) -> str:
    return f"{q.answer}. {q.options['ABCD'.index(q.answer)]}" if q.qtype == "mcq" else q.answer


def explain_ui(q) -> None:
    k = (q.id, LC[S.lang])
    if k not in S.expl and st.button("💡 Explain", key=f"ex_{q.id}_{k[1]}"):
        with st.spinner("Preparing explanation..."):
            t = safe(explain.explain, q, ctx(q.question + " " + q.source_ref), k[1], S.subject)
        if t:
            S.expl[k] = t
    if k in S.expl:
        card(S.expl[k], S.lang)


def show_feedback(q, r: dict) -> None:
    good, bad = MICRO[LC[S.lang]]
    card(f"{'✅' if r['ok'] else '❌'} {good if r['ok'] else bad}  ({r['score']:g}/{r['max']:g})",
         S.lang, "ok" if r["ok"] else "bad")
    g = r["grade"]
    if g:
        if g.feedback:
            card(g.feedback, S.lang)
        for title, items, icon in (("Covered", g.covered, "✔️"), ("Missed", g.missed, "➖"),
                                   ("Incorrect", g.incorrect, "⚠️")):
            if items:
                st.markdown(f"**{title}**\n" + "\n".join(f"- {icon} {i}" for i in items))
        if g.outside_chapter:
            st.info("Correct, but outside this chapter.")
        card(g.model_answer, S.lang)
    else:
        st.markdown(f"**Correct answer:** {correct_text(q)}")
    st.caption(f"📍 {q.source_ref}")
    explain_ui(q)


def finish(mode: str, Q: dict) -> bool:
    with st.spinner("Marking your answers..."):
        for q in Q["qs"]:
            if q.id not in Q["res"]:
                resp, img = Q["ans"].get(q.id, (None, None))
                r = safe(evaluate, q, resp, img)
                if r is None:
                    return False
                Q["res"][q.id] = r
    Q["secs"] = int(time.time() - Q["t0"])
    Q["done"] = True
    return True


def quiz_setup(mode: str) -> None:
    if not S.get("text_edit"):
        st.info("Upload a chapter first (Upload tab).")
        return
    types = st.multiselect("Question types", list(TYPES), default=["MCQs"], key=f"{mode}_t")
    n = st.slider("How many questions?", 3, 20, 8, key=f"{mode}_n")
    diff = st.select_slider("Difficulty", ["Easy", "Medium", "Exam-level"], "Medium", key=f"{mode}_d")
    heads = list(dict.fromkeys(c.ref for c in chunks()))
    focus = st.selectbox("Focus on", ["Whole chapter"] + heads, key=f"{mode}_f")
    mins = st.number_input("Time limit (minutes)", 5, 180, 20, key=f"{mode}_m") if mode == "mock" else 0
    if st.button("🚀 Start", key=f"{mode}_go", type="primary") and types:
        start_quiz(mode, dict(types=[TYPES[t] for t in types], n=n, diff=diff, focus=focus, mins=mins,
                              qlang=S.qlang_sel))


def show_results(mode: str, Q: dict) -> None:
    qs, res = Q["qs"], Q["res"]
    tot, mx = sum(r["score"] for r in res.values()), sum(q.marks for q in qs)
    st.metric("Score", f"{tot:g} / {mx}", f"{100 * tot / mx:.0f}%  ·  {Q['secs'] // 60}m {Q['secs'] % 60}s")
    topics: dict[str, list[float]] = {}
    for q in qs:
        a = topics.setdefault(q.topic or q.source_ref or "General", [0.0, 0.0])
        a[0] += res[q.id]["score"]; a[1] += q.marks
    pct = {t: 100 * a / b for t, (a, b) in topics.items()}
    st.bar_chart(pd.Series(pct, name="% by topic"))
    weak = [t for t, p in pct.items() if p < 60]
    st.markdown("**Weak topics:** " + (", ".join(weak) if weak else "none 🎉"))
    if S.get("save_opt") and S.get("profile") and not Q["saved"]:
        db.save_attempt(S.profile, Q["title"], S.subject, mode, tot, mx, Q["secs"], pct)
        Q["saved"] = True
    for q in qs:
        with st.expander(f"{'✅' if res[q.id]['ok'] else '❌'} {q.question[:70]}"):
            show_feedback(q, res[q.id])
    if weak and st.button("🎯 Revise weak areas", key=f"{mode}_rev"):
        start_quiz(mode, Q["cfg"] | dict(focus="Whole chapter"), weak)
    if st.button("➕ More new questions", key=f"{mode}_more"):
        start_quiz(mode, Q["cfg"])
    st.download_button("⬇️ Quiz + answer key (DOCX)", export.build_docx(Q["title"], qs, S.summary),
                       f"{Q['title'] or 'quiz'}.docx", key=f"{mode}_dl")
    if st.button("New setup", key=f"{mode}_new"):
        S.quizzes[mode] = None
        st.rerun()


def run_quiz(mode: str) -> None:
    Q = S.quizzes[mode]
    if Q is None:
        return quiz_setup(mode)
    if Q["done"]:
        return show_results(mode, Q)
    qs, i = Q["qs"], Q["i"]
    q = qs[i]
    checked = q.id in Q["res"]
    st.progress(i / len(qs))
    st.caption(f"Q {i + 1} of {len(qs)} · {q.marks} marks · {q.length_guide or q.source_ref}")
    if mode == "mock":
        left = int(Q["limit"] * 60 - (time.time() - Q["t0"]))
        st.caption(f"⏱ {left // 60}:{left % 60:02d} left (updates when you tap)" if left > 0
                   else "⏱ Time is up. Please submit.")
    card(q.question, Q["qlang"])
    resp, img = answer_widget(q, f"{mode}_{q.id}", checked)
    if st.toggle("🔖 Bookmark", value=q.id in S.bookmarks, key=f"bm_{mode}_{q.id}"):
        S.bookmarks[q.id] = q
    else:
        S.bookmarks.pop(q.id, None)
    last = i + 1 == len(qs)
    if mode == "practice" and not checked:
        if st.button("Check answer", key=f"chk_{q.id}", type="primary"):
            if resp in (None, "") and not img:
                st.warning("Please write or choose an answer first.")
            else:
                r = safe(evaluate, q, resp, img)
                if r:
                    Q["res"][q.id] = r
                    st.rerun()
    elif mode == "practice":
        show_feedback(q, Q["res"][q.id])
        if st.button("Finish" if last else "Next ➡️", key=f"nx_{q.id}", type="primary"):
            if last:
                Q["secs"] = int(time.time() - Q["t0"]); Q["done"] = True
            else:
                Q["i"] += 1
            st.rerun()
    else:
        if st.button("Submit paper" if last else "Next ➡️", key=f"nx_{q.id}", type="primary"):
            Q["ans"][q.id] = (resp, img)
            if last:
                finish(mode, Q)
            else:
                Q["i"] += 1
            st.rerun()


with t_pr:
    run_quiz("practice")
with t_mk:
    run_quiz("mock")


# ---------------------------------------------------------------- progress
with t_pg:
    rows = db.history(S.get("profile", "")) if S.get("save_opt") and S.get("profile") else []
    if not rows:
        st.info("Turn on 'Save my history' in the sidebar and finish a quiz to see progress.")
    else:
        df = pd.DataFrame(rows)
        df["pct"] = 100 * df["score"] / df["max"]
        st.line_chart(df.set_index("ts")["pct"])
        agg: dict[str, list[float]] = {}
        for r in rows:
            for t, p in r["topics"].items():
                agg.setdefault(t, []).append(p)
        weakest = sorted(((sum(v) / len(v), t) for t, v in agg.items()))[:5]
        st.markdown("**Weakest topics:** " + ", ".join(f"{t} ({p:.0f}%)" for p, t in weakest))
    st.subheader("🔖 Bookmarked")
    for q in S.bookmarks.values():
        with st.expander(q.question[:70]):
            card(q.question, S.get("qlang_sel", "English"))
            st.markdown(f"**Answer:** {correct_text(q)}")


# ---------------------------------------------------------------- ask
with t_ask:
    if not S.get("text_edit"):
        st.info("Upload a chapter first.")
    else:
        if st.button("📝 Chapter summary"):
            with st.spinner("Summarising..."):
                S.summary = safe(explain.summarize, ctx(), LC[S.lang])
        if S.summary:
            for title, items in (("Key points", S.summary.bullets), ("Definitions", S.summary.definitions),
                                 ("Formulas", S.summary.formulas)):
                if items:
                    st.markdown(f"**{title}**")
                    for x in items:
                        card(x, S.lang)
        for role, text in S.chat:
            with st.chat_message(role):
                card(text, S.lang if role == "assistant" else "English")
        if prompt := st.chat_input("Ask a doubt about this chapter..."):
            S.chat.append(("user", prompt))
            with st.spinner("Looking in your chapter..."):
                a = safe(explain.ask, prompt, ctx(prompt), LC[S.lang])
            if a:
                S.chat.append(("assistant", a.answer + (f"\n📍 {', '.join(a.source_refs)}" if a.source_refs else "")))
            st.rerun()
