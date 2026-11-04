"""Lightweight retrieval: whole chapter if small, else BM25 top chunks."""
import re
from core.ingest import Chunk


def _tok(s: str) -> list[str]:
    return re.findall(r"\w+", s.casefold())


def _fmt(cs: list[Chunk]) -> str:
    return "\n\n".join(f"[{c.ref}]\n{c.text}" for c in cs)


def select_context(chunks: list[Chunk], query: str = "", budget: int = 12000) -> str:
    """Return chapter text (<= budget chars) most relevant to `query`."""
    if sum(len(c.text) for c in chunks) <= budget:
        return _fmt(chunks)
    if query.strip():
        try:
            from rank_bm25 import BM25Okapi
            scores = BM25Okapi([_tok(c.text) for c in chunks]).get_scores(_tok(query))
        except Exception:
            q = set(_tok(query)); scores = [len(q & set(_tok(c.text))) for c in chunks]
        order = sorted(range(len(chunks)), key=lambda i: -scores[i])
    else:
        order = list(range(len(chunks)))
    picked, used = [], 0
    for i in order:
        if used + len(chunks[i].text) > budget:
            continue
        picked.append(i); used += len(chunks[i].text)
    return _fmt([chunks[i] for i in sorted(picked)])
