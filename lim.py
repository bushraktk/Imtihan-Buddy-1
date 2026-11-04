"""Anthropic wrapper: retries, session cap, strict-JSON validation (one retry)."""
import base64, json, os, re
from functools import lru_cache
from typing import TypeVar
import anthropic
from pydantic import BaseModel

MODEL = "claude-sonnet-5-5"   # single config constant
MAX_CALLS = 80                 # per-session request cap
T = TypeVar("T", bound=BaseModel)


class LLMError(Exception):
    """kind: busy | format | cap | key"""
    def __init__(self, kind: str):
        super().__init__(kind)
        self.kind = kind


def _api_key() -> str | None:
    try:
        import streamlit as st
        k = st.secrets.get("ANTHROPIC_API_KEY")
    except Exception:
        k = None
    return k or os.environ.get("ANTHROPIC_API_KEY")


@lru_cache(maxsize=2)
def _client(key: str) -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=key, timeout=60, max_retries=2)


def _count() -> None:
    try:
        import streamlit as st
        n = st.session_state.get("_calls", 0) + 1
        if n > MAX_CALLS:
            raise LLMError("cap")
        st.session_state["_calls"] = n
    except LLMError:
        raise
    except Exception:
        pass


def _send(system: str, messages: list, max_tokens: int) -> str:
    key = _api_key()
    if not key:
        raise LLMError("key")
    _count()
    try:
        r = _client(key).messages.create(model=MODEL, max_tokens=max_tokens, system=system, messages=messages)
    except anthropic.AuthenticationError:
        raise LLMError("key")
    except (anthropic.RateLimitError, anthropic.APITimeoutError, anthropic.APIConnectionError, anthropic.APIStatusError):
        raise LLMError("busy")
    return "".join(b.text for b in r.content if b.type == "text")


def extract_json(text: str) -> str:
    """Strip code fences/preamble and return the outermost JSON object."""
    t = re.sub(r"```(?:json)?", "", text).strip()
    a, b = t.find("{"), t.rfind("}")
    if a < 0 or b <= a:
        raise ValueError("no JSON object found")
    return t[a:b + 1]


def call_json(system: str, user: str, schema: type[T], max_tokens: int = 4000) -> T:
    """Call the model, validate against `schema`, retry once on bad JSON."""
    sys = (system + "\n\nReturn ONLY one JSON object matching this JSON Schema, no markdown fences, no commentary:\n"
           + json.dumps(schema.model_json_schema()))
    msgs = [{"role": "user", "content": user}]
    for _ in range(2):
        raw = _send(sys, msgs, max_tokens)
        try:
            return schema.model_validate_json(extract_json(raw))
        except ValueError as e:  # includes pydantic ValidationError
            msgs += [{"role": "assistant", "content": raw or "{}"},
                     {"role": "user", "content": f"Invalid ({str(e)[:300]}). Return ONLY the corrected JSON object."}]
    raise LLMError("format")


def ocr_image(data: bytes, media_type: str = "image/jpeg") -> str:
    """Read text from a photo with Claude vision."""
    import prompts
    content = [{"type": "image", "source": {"type": "base64", "media_type": media_type,
                                            "data": base64.b64encode(data).decode()}},
               {"type": "text", "text": "Transcribe this image."}]
    return _send(prompts.OCR, [{"role": "user", "content": content}], 3000)
