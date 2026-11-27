from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import JSON, Boolean, Float, ForeignKey, Integer, String, Text, UniqueConstraint, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


def uid():
    return uuid4().hex


def now():
    return datetime.now(timezone.utc).isoformat()


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = 'users'
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    email: Mapped[str] = mapped_column(String, unique=True)
    password_hash: Mapped[str] = mapped_column(String)
    name: Mapped[str] = mapped_column(String, default='Student')


class LoginSession(Base):
    __tablename__ = 'sessions'
    token_hash: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    expires: Mapped[float] = mapped_column(Float)


class Course(Base):
    __tablename__ = 'courses'
    __table_args__ = (UniqueConstraint('user_id', 'name'),)
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    name: Mapped[str] = mapped_column(String)
    created_at: Mapped[str] = mapped_column(String, default=now)


class Document(Base):
    __tablename__ = 'documents'
    __table_args__ = (UniqueConstraint('course_id', 'kind', 'sha256'),)
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    course_id: Mapped[str] = mapped_column(ForeignKey('courses.id'), index=True)
    filename: Mapped[str] = mapped_column(String)
    kind: Mapped[str] = mapped_column(String)
    sha256: Mapped[str] = mapped_column(String)
    pages: Mapped[int] = mapped_column(Integer)
    warnings: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[str] = mapped_column(String, default=now)


class Chunk(Base):
    __tablename__ = 'chunks'
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    document_id: Mapped[str] = mapped_column(ForeignKey('documents.id'), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    course_id: Mapped[str] = mapped_column(ForeignKey('courses.id'), index=True)
    kind: Mapped[str] = mapped_column(String)
    filename: Mapped[str] = mapped_column(String)
    page: Mapped[int] = mapped_column(Integer)
    ordinal: Mapped[int] = mapped_column(Integer, default=0)
    section: Mapped[str] = mapped_column(String)
    text: Mapped[str] = mapped_column(Text)
    quarantined: Mapped[bool] = mapped_column(Boolean, default=False)


class Topic(Base):
    __tablename__ = 'topics'
    __table_args__ = (UniqueConstraint('course_id', 'path'),)
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    course_id: Mapped[str] = mapped_column(ForeignKey('courses.id'), index=True)
    parent_id: Mapped[str | None] = mapped_column(ForeignKey('topics.id'), nullable=True)
    name: Mapped[str] = mapped_column(String)
    path: Mapped[str] = mapped_column(String)
    citations: Mapped[list] = mapped_column(JSON, default=list)
    frequency: Mapped[int] = mapped_column(Integer, default=0)
    marks: Mapped[float] = mapped_column(Float, default=0)
    weight: Mapped[float] = mapped_column(Float, default=0)


class PaperQuestion(Base):
    __tablename__ = 'paper_questions'
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    course_id: Mapped[str] = mapped_column(ForeignKey('courses.id'), index=True)
    text: Mapped[str] = mapped_column(Text)
    marks: Mapped[float] = mapped_column(Float, default=1)
    topic_id: Mapped[str | None] = mapped_column(ForeignKey('topics.id'), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0)
    review_needed: Mapped[bool] = mapped_column(Boolean, default=True)
    citation: Mapped[dict] = mapped_column(JSON)


class Quiz(Base):
    __tablename__ = 'quizzes'
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    course_id: Mapped[str] = mapped_column(ForeignKey('courses.id'), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    status: Mapped[str] = mapped_column(String, default='ready')
    mode: Mapped[str] = mapped_column(String)
    questions: Mapped[list] = mapped_column(JSON)
    skipped: Mapped[list] = mapped_column(JSON, default=list)
    answers: Mapped[dict] = mapped_column(JSON, default=dict)
    results: Mapped[list] = mapped_column(JSON, default=list)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[str] = mapped_column(String, default=now)
    submitted_at: Mapped[str | None] = mapped_column(String, nullable=True)


class RevisionPlan(Base):
    __tablename__ = 'revision_plans'
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    course_id: Mapped[str] = mapped_column(ForeignKey('courses.id'), index=True)
    version: Mapped[int] = mapped_column(Integer)
    days: Mapped[int] = mapped_column(Integer)
    minutes_per_day: Mapped[int] = mapped_column(Integer)
    schedule: Mapped[list] = mapped_column(JSON)
    completed: Mapped[list] = mapped_column(JSON, default=list)
    reason: Mapped[str] = mapped_column(String)
    created_at: Mapped[str] = mapped_column(String, default=now)


class TutorMessage(Base):
    __tablename__ = 'tutor_messages'
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    course_id: Mapped[str] = mapped_column(ForeignKey('courses.id'), index=True)
    topic_id: Mapped[str] = mapped_column(ForeignKey('topics.id'))
    question: Mapped[str] = mapped_column(Text)
    response: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[str] = mapped_column(String, default=now)


def open_database(path):
    engine = create_engine(f'sqlite:///{path.as_posix()}', connect_args={'check_same_thread': False, 'timeout': 30})

    @event.listens_for(engine, 'connect')
    def pragmas(connection, _):
        connection.execute('PRAGMA foreign_keys=ON')
        connection.execute('PRAGMA journal_mode=WAL')

    Base.metadata.create_all(engine)
    return engine, sessionmaker(bind=engine, expire_on_commit=False)
