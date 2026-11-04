"""Answer checking."""
import re
import prompts
from core import llm
from core.models import GradeResult, Question

OBJECTIVE = {"mcq", "tf", "fill"}


def _norm(s: str) -> str:
    return re.sub(r"[\W_]+", " ", s.casefold()).strip()


def check_objective(q: Question, resp) -> bool:
    """MCQ: resp is option index 0-3; TF: 'True'/'False'; fill: free text (answer may use '|' alternatives)."""
    if resp is None or resp == "":
        return False
    if q.qtype == "mcq":
        return isinstance(resp, int) and 0 <= resp < 4 and "ABCD"[resp] == q.answer
    if q.qtype == "tf":
        return str(resp).strip().lower() == q.answer.strip().lower()
    return _norm(str(resp)) in {_norm(a) for a in q.answer.split("|")}


def grade_written(q: Question, answer: str, context: str, lang: str, subject: str) -> GradeResult:
    """Grade a written answer against the chapter-derived rubric."""
    user = (f"<chapter>\n{context}\n</chapter>\n<question marks=\"{q.marks}\">{q.question}</question>\n"
            f"Subject: {subject}. Rubric key points: {q.rubric}\nReference answer: {q.answer}\n"
            f"<student_answer>\n{answer}\n</student_answer>")
    g = llm.call_json(prompts.grading(lang), user, GradeResult)
    g.score = max(0.0, min(float(q.marks), g.score))
    return g
