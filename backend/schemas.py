from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Citation(Strict):
    chunk_id: str
    quote: str = Field(min_length=8, max_length=800)


class GeneratedQuestion(Strict):
    kind: Literal['mcq', 'short']
    prompt: str = Field(min_length=10, max_length=1000)
    options: list[str] = Field(default_factory=list, max_length=4)
    answer_index: int | None = Field(default=None, ge=0, le=3)
    reference_answer: str = Field(min_length=1, max_length=1500)
    explanation: str = Field(min_length=10, max_length=1500)
    rubric: list[str] = Field(min_length=1, max_length=8)
    citations: list[Citation] = Field(min_length=1, max_length=4)

    @model_validator(mode='after')
    def check_kind(self):
        if self.kind == 'mcq' and (len(self.options) != 4 or self.answer_index is None or len(set(self.options)) != 4):
            raise ValueError('MCQs require four distinct options and one answer index.')
        if self.kind == 'short' and (self.options or self.answer_index is not None):
            raise ValueError('Short answers must not contain MCQ fields.')
        return self


class QuestionBatch(Strict):
    questions: list[GeneratedQuestion] = Field(max_length=3)
    insufficient_evidence: bool = False


class Grade(Strict):
    score: float = Field(ge=0, le=1)
    feedback: str = Field(min_length=5, max_length=1800)
    citations: list[Citation] = Field(min_length=1, max_length=4)


class TutorAnswer(Strict):
    answer: str = Field(max_length=4000)
    insufficient_evidence: bool
    citations: list[Citation] = Field(max_length=5)


class TopicNode(Strict):
    name: str = Field(min_length=1, max_length=160)
    parent: str | None = Field(default=None, max_length=160)
    citations: list[Citation] = Field(min_length=1, max_length=3)


class TopicBatch(Strict):
    topics: list[TopicNode] = Field(min_length=1, max_length=60)


class PaperItem(Strict):
    text: str = Field(min_length=5, max_length=2000)
    marks: float = Field(default=1, ge=0.5, le=100)
    citation: Citation


class PaperBatch(Strict):
    questions: list[PaperItem] = Field(max_length=100)


class LoginInput(Strict):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)


class RegisterInput(LoginInput):
    name: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=8, max_length=128)


class CourseInput(Strict):
    name: str = Field(min_length=1, max_length=120)


class QuizInput(Strict):
    topic_ids: list[str] = Field(default_factory=list, max_length=8)
    per_topic: int = Field(default=2, ge=2, le=3)


class Submission(Strict):
    answers: dict[str, str] = Field(max_length=24)

    @model_validator(mode='after')
    def bounded(self):
        if any(len(x) > 3000 for x in self.answers.values()):
            raise ValueError('Answers must be at most 3000 characters.')
        return self


class PlanInput(Strict):
    days: int = Field(default=5, ge=1, le=30)
    minutes_per_day: int = Field(default=60, ge=10, le=480)


class TutorInput(Strict):
    topic_id: str
    message: str = Field(min_length=3, max_length=2000)


class MappingInput(Strict):
    topic_id: str


class CompletionInput(Strict):
    task_id: str
    completed: bool
