"""File parsing, OCR via vision, cleaning, chunking."""
import io, re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Chunk:
    ref: str
    text: str


_HEAD = re.compile(r"^(\d+(\.\d+)*[.)]?\s+\S.{0,80}|[A-Z][A-Z \-]{3,60})$")


def looks_like_heading(line: str) -> bool:
    s = line.strip()
    return bool(s) and len(s) <= 80 and not s.endswith((".", ":", "،", "۔")) and bool(_HEAD.match(s))


def clean_text(text: str) -> str:
    """Drop page numbers, repeated running headers and zero-width junk."""
    text = re.sub(r"[\u200b\u200c\ufeff]", "", text)
    lines = [l.strip() for l in text.splitlines()]
    freq = Counter(l for l in lines if 0 < len(l) < 60)
    out = []
    for l in lines:
        if re.fullmatch(r"(page\s*)?\d{1,4}", l, re.I) or (l and freq[l] >= 4 and not looks_like_heading(l)):
            continue
        out.append(l)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip()


def chunk_text(text: str, max_chars: int = 1500) -> list[Chunk]:
    """Split by detected headings, further splitting long sections."""
    chunks: list[Chunk] = []
    head, buf, part = "Introduction", [], 0

    def flush() -> None:
        nonlocal buf, part
        if buf:
            chunks.append(Chunk(head if part == 0 else f"{head} (cont.)", "\n".join(buf)))
            buf, part = [], part + 1

    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        if looks_like_heading(s):
            flush(); head, part = s, 0
            continue
        buf.append(s)
        if sum(len(b) for b in buf) > max_chars:
            flush()
    flush()
    return chunks


def quality_warning(text: str) -> str | None:
    t = re.sub(r"\s", "", text)
    if len(t) < 400:
        return "Very little text was read. Try a clearer photo or a text-based PDF."
    if (sum(c.isalpha() for c in t) / len(t) < 0.6) or t.count("\ufffd") > 5:
        return "The text looks garbled. Try a clearer, well-lit photo or a text-based PDF."
    return None


def guess_title(text: str) -> str:
    for l in text.splitlines():
        if looks_like_heading(l):
            return l.strip()
    return text.strip().splitlines()[0][:60] if text.strip() else ""


def shrink(data: bytes, max_side: int = 1600) -> bytes:
    """Downscale phone photos to save bandwidth and tokens."""
    from PIL import Image
    im = Image.open(io.BytesIO(data)).convert("RGB")
    im.thumbnail((max_side, max_side))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=80)
    return buf.getvalue()


def extract(name: str, data: bytes) -> str:
    """Return raw text from PDF / DOCX / TXT / image bytes."""
    ext = Path(name).suffix.lower()
    if ext == ".pdf":
        from pypdf import PdfReader
        txt = "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(data)).pages)
        if len(txt.strip()) < 100:
            raise ValueError("This PDF looks scanned. Upload photos of the pages instead.")
        return txt
    if ext == ".docx":
        from docx import Document
        return "\n".join(p.text for p in Document(io.BytesIO(data)).paragraphs)
    if ext == ".txt":
        return data.decode("utf-8", errors="replace")
    if ext in (".jpg", ".jpeg", ".png"):
        from core import llm
        return llm.ocr_image(shrink(data))
    raise ValueError(f"Unsupported file type: {ext}")
