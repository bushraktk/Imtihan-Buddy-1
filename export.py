"""DOCX export (Urdu paragraphs are marked RTL with an Urdu font)."""
import io, re
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from core.models import Question, Summary

_URDU = re.compile(r"[\u0600-\u06FF]")


def _para(doc, text: str, bold: bool = False) -> None:
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.bold = bold
    if _URDU.search(text):
        p._p.get_or_add_pPr().append(OxmlElement("w:bidi"))
        r.font.name = "Noto Nastaliq Urdu"
        rpr = r._r.get_or_add_rPr()
        rpr.rFonts.set(qn("w:cs"), "Noto Nastaliq Urdu")
        rpr.append(OxmlElement("w:rtl"))


def build_docx(title: str, qs: list[Question], summary: Summary | None = None) -> bytes:
    """Quiz paper + answer key (+ optional key-points summary)."""
    d = Document()
    d.add_heading(f"{title or 'Chapter'} - Practice Paper", 1)
    for i, q in enumerate(qs, 1):
        _para(d, f"Q{i}. ({q.marks} marks) {q.question}", True)
        for k, o in enumerate(q.options):
            _para(d, f"   {'ABCD'[k]}. {o}")
    d.add_page_break()
    d.add_heading("Answer key", 1)
    for i, q in enumerate(qs, 1):
        _para(d, f"Q{i}. {q.answer}   [{q.source_ref}]", True)
        for pt in q.rubric:
            _para(d, f"   - {pt}")
    if summary:
        d.add_page_break(); d.add_heading("Key points summary", 1)
        for x in summary.bullets + summary.definitions + summary.formulas:
            _para(d, f"- {x}")
    buf = io.BytesIO(); d.save(buf)
    return buf.getvalue()
