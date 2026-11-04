"""Pydantic schemas for all structured LLM output."""
from typing import Literal
from pydantic import BaseModel, Field, model_validator

QType = Literal["mcq", "short", "long", "fill", "tf", "numerical"]


class Question(BaseModel):
    id: str = ""
    qtype: QType
    question: str
    options: list[str] = []
    answer: str
    marks: int = Field(1, ge=1, le=10)
    length_guide: str = ""
    rubric: list[str] = []
    explanation: str = ""
    topic: str = ""
    source_ref: str = ""

    @model_validator(mode="after")
    def _check(self) -> "Question":
        if self.qtype == "mcq":
            if len(self.options) != 4:
                raise ValueError("MCQ needs exactly 4 options")
            self.answer = self.answer.strip().upper()[:1]
            if self.answer not in list("ABCD"):
                raise ValueError("MCQ answer must be A-D")
        if self.qtype == "tf":
            self.answer = "True" if self.answer.strip().lower().startswith("t") else "False"
        return self


class QuestionSet(BaseModel):
    questions: list[Question]


class GradeResult(BaseModel):
    score: float = Field(ge=0)
    covered: list[str] = []
    missed: list[str] = []
    incorrect: list[str] = []
    model_answer: str = ""
    feedback: str = ""
    outside_chapter: bool = False


class Explanation(BaseModel):
    text: str


class ChatAnswer(BaseModel):
    answer: str
    source_refs: list[str] = []
    in_chapter: bool = True


class Summary(BaseModel):
    bullets: list[str]
    definitions: list[str] = []
    formulas: list[str] = []
