"""Question generation."""
import re, uuid
import prompts
from core import llm, retrieval
from core.ingest import Chunk
from core.models import Question, QuestionSet

DEFAULT_MARKS = {"mcq": 1, "tf": 1, "fill": 1, "short": 2, "numerical": 3, "long": 5}


def _norm(s: str) -> str:
    return re.sub(r"\W+", " ", s.casefold()).strip()


def generate_questions(chunks: list[Chunk], *, cls: int, subject: str, board: str, types: list[str], n: int,
                       difficulty: str, focus: str, qlang: str, existing: list[str],
                       weak: list[str] | None = None) -> list[Question]:
    """Generate up to n new, deduplicated questions grounded in the chapter (batches of 10)."""
    query = focus if focus and focus != "Whole chapter" else " ".join(weak or [])
    context = retrieval.select_context(chunks, query)
    seen = {_norm(q) for q in existing}
    out: list[Question] = []
    for _ in range(4):
        need = min(10, n - len(out))
        if need <= 0:
            break
        user = (f"<chapter>\n{context}\n</chapter>\n\nClass {cls}, subject {subject}, board {board or 'any'}. "
                f"Difficulty: {difficulty}. Focus: {query or 'whole chapter'}.\n"
                f"Write {need} questions, spread across these types: {', '.join(types)}.\n"
                f"Question language: {qlang}.\nAlready asked (do not repeat):\n"
                + "\n".join(f"- {q[:100]}" for q in (existing + [q.question for q in out])[-40:]))
        for q in llm.call_json(prompts.GENERATION, user, QuestionSet, max_tokens=6000).questions:
            if q.qtype in types and _norm(q.question) not in seen:
                q.id = uuid.uuid4().hex[:8]
                seen.add(_norm(q.question)); out.append(q)
    return out[:n]
