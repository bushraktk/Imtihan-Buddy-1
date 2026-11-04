"""Multilingual explanations, doubt chat and summary."""
import prompts
from core import llm
from core.models import ChatAnswer, Explanation, Question, Summary


def explain(q: Question, context: str, lang: str, subject: str) -> str:
    user = (f"<chapter>\n{context}\n</chapter>\n<question>{q.question}</question>\nOptions: {q.options}\n"
            f"Correct answer: {q.answer}\nSubject: {subject}")
    return llm.call_json(prompts.explanation(lang), user, Explanation, 1500).text


def ask(question: str, context: str, lang: str) -> ChatAnswer:
    user = f"<chapter>\n{context}\n</chapter>\n<question>{question}</question>"
    return llm.call_json(prompts.chat(lang), user, ChatAnswer, 1500)


def summarize(context: str, lang: str) -> Summary:
    return llm.call_json(prompts.summary(lang), f"<chapter>\n{context}\n</chapter>", Summary, 2500)
