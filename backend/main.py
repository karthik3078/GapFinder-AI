import logging
import secrets
import threading
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError

from .config import ROOT, Settings
from .database import Chunk, Course, Document, LoginSession, PaperQuestion, Quiz, RevisionPlan, Topic, TutorMessage, User, open_database
from .diagnostic import build_plan, create_quiz, gap_report, grade_quiz, latest_plan, progress, public_quiz
from .generation import EvidenceError, Generator, ProviderError
from .ingestion import citation, ingest
from .retrieval import VectorStore
from .schemas import CompletionInput, CourseInput, LoginInput, MappingInput, PlanInput, QuizInput, RegisterInput, Submission, TutorInput
from .security import hash_password, token_hash, verify_password
from .topics import build_topics, leaf_topics, map_papers, recalculate_weights

COOKIE = 'gapfinder_session'


class BodyTooLarge(Exception):
    pass


class BodyLimit:
    def __init__(self, app, maximum):
        self.app, self.maximum = app, maximum

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        total = 0

        async def bounded_receive():
            nonlocal total
            message = await receive()
            total += len(message.get('body', b''))
            if total > self.maximum:
                raise BodyTooLarge()
            return message

        headers = dict(scope.get('headers', []))
        try:
            length = int(headers.get(b'content-length', b'0'))
        except ValueError:
            length = self.maximum + 1
        if length > self.maximum:
            return await JSONResponse({'detail': 'Upload exceeds the request size limit.'}, status_code=413)(scope, receive, send)
        try:
            await self.app(scope, bounded_receive, send)
        except BodyTooLarge:
            await JSONResponse({'detail': 'Upload exceeds the request size limit.'}, status_code=413)(scope, receive, send)


def create_app(settings=None):
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app):
        settings.storage_dir.mkdir(parents=True, exist_ok=True)
        (settings.storage_dir / 'uploads').mkdir(exist_ok=True)
        engine, sessions = open_database(settings.storage_dir / 'gapfinder.db')
        app.state.engine, app.state.sessions = engine, sessions
        app.state.vectors = VectorStore(settings)
        app.state.generator = Generator(settings)
        app.state.course_locks = defaultdict(threading.Lock)
        app.state.login_attempts = defaultdict(deque)
        app.state.login_lock = threading.Lock()
        app.state.dummy_password = hash_password(secrets.token_urlsafe(24))
        if settings.seed_demo_user:
            with sessions() as db:
                if not db.scalar(select(User).where(User.email == 'student@demo.com')):
                    db.add(User(email='student@demo.com', name='Demo student', password_hash=hash_password('demo123')))
                    db.commit()
        yield
        app.state.generator.close()
        app.state.vectors.close()
        engine.dispose()

    app = FastAPI(title='GapFinder AI', version='1.0.0', lifespan=lifespan)
    app.state.settings = settings
    app.add_middleware(CORSMiddleware, allow_origins=settings.origins, allow_credentials=True,
                       allow_methods=['GET', 'POST', 'PATCH', 'DELETE'], allow_headers=['Content-Type'])
    app.add_middleware(BodyLimit, maximum=settings.max_upload_mb * 1024 * 1024 + 65536)

    @app.middleware('http')
    async def browser_security(request, call_next):
        if request.method not in ('GET', 'HEAD', 'OPTIONS'):
            origin = request.headers.get('origin')
            if (origin and origin.rstrip('/') not in settings.origins) or request.headers.get('sec-fetch-site') == 'cross-site':
                return JSONResponse({'detail': 'This request origin is not allowed.'}, status_code=403)
        response = await call_next(request)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'same-origin'
        response.headers['X-Frame-Options'] = 'DENY'
        if request.url.path.startswith('/api'):
            response.headers['Cache-Control'] = 'no-store'
        return response

    @app.exception_handler(EvidenceError)
    async def evidence_error(_, exc):
        return JSONResponse({'detail': str(exc)}, status_code=422)

    @app.exception_handler(ProviderError)
    async def provider_error(_, exc):
        return JSONResponse({'detail': str(exc)}, status_code=502)

    @app.exception_handler(ValueError)
    async def value_error(_, exc):
        return JSONResponse({'detail': str(exc)}, status_code=422)

    @app.exception_handler(IntegrityError)
    async def conflict_error(_, __):
        return JSONResponse({'detail': 'This record already exists. Refresh and try again.'}, status_code=409)

    def database():
        with app.state.sessions() as db:
            yield db

    def current_user(request: Request, db=Depends(database)):
        token = request.cookies.get(COOKIE)
        login = db.get(LoginSession, token_hash(token)) if token else None
        if not login or login.expires < time.time():
            raise HTTPException(401, 'Please sign in.')
        return db.get(User, login.user_id)

    def course_access(course_id: str, db=Depends(database), user=Depends(current_user)):
        course = db.scalar(select(Course).where(Course.id == course_id, Course.user_id == user.id))
        if not course:
            raise HTTPException(404, 'Course not found.')
        return course

    def login_throttle(request):
        key = request.client.host if request.client else 'local'
        with app.state.login_lock:
            attempts = app.state.login_attempts[key]
            while attempts and attempts[0] < time.time() - 60:
                attempts.popleft()
            if len(attempts) >= 15:
                raise HTTPException(429, 'Too many sign-in attempts. Wait one minute.')
            attempts.append(time.time())

    def session_cookie(db, user, response):
        token = secrets.token_urlsafe(32)
        db.execute(delete(LoginSession).where(LoginSession.expires < time.time()))
        db.add(LoginSession(token_hash=token_hash(token), user_id=user.id, expires=time.time() + 86400))
        db.commit()
        response.set_cookie(COOKIE, token, httponly=True, secure=settings.cookie_secure, samesite='lax', max_age=86400, path='/')
        return {'id': user.id, 'email': user.email, 'name': user.name}

    @app.get('/api/health')
    def health():
        return {'status': 'ok', 'mode': settings.ai_mode, 'embedding_provider': settings.embedding_provider,
                'generation_model': settings.gemini_model if settings.ai_mode == 'live' else None,
                'demo_user_available': settings.seed_demo_user,
                'notice': 'Offline demonstration: curated/extractive questions and lexical short-answer grading.' if settings.ai_mode == 'demo' else 'Live model outputs require review; citations verify provenance, not correctness.'}

    @app.post('/api/auth/login')
    def login(data: LoginInput, request: Request, response: Response, db=Depends(database)):
        login_throttle(request)
        user = db.scalar(select(User).where(User.email == data.email.strip().lower()))
        valid = verify_password(data.password, user.password_hash if user else app.state.dummy_password)
        if not user or not valid:
            raise HTTPException(401, 'Incorrect email or password.')
        return session_cookie(db, user, response)

    @app.post('/api/auth/register', status_code=201)
    def register(data: RegisterInput, request: Request, response: Response, db=Depends(database)):
        login_throttle(request)
        email = data.email.strip().lower()
        if '@' not in email or '.' not in email.split('@')[-1]:
            raise HTTPException(422, 'Enter a valid email address.')
        user = User(email=email, name=data.name.strip(), password_hash=hash_password(data.password))
        db.add(user)
        db.flush()
        return session_cookie(db, user, response)

    @app.get('/api/auth/me')
    def me(user=Depends(current_user)):
        return {'id': user.id, 'email': user.email, 'name': user.name}

    @app.post('/api/auth/logout')
    def logout(request: Request, response: Response, db=Depends(database)):
        token = request.cookies.get(COOKIE)
        if token:
            db.execute(delete(LoginSession).where(LoginSession.token_hash == token_hash(token)))
            db.commit()
        response.delete_cookie(COOKIE, path='/')
        return {'ok': True}

    @app.get('/api/courses')
    def courses(db=Depends(database), user=Depends(current_user)):
        return [{'id': c.id, 'name': c.name} for c in db.scalars(select(Course).where(Course.user_id == user.id).order_by(Course.created_at))]

    @app.post('/api/courses', status_code=201)
    def add_course(data: CourseInput, db=Depends(database), user=Depends(current_user)):
        if not data.name.strip():
            raise HTTPException(422, 'A course name is required.')
        course = Course(user_id=user.id, name=data.name.strip())
        db.add(course)
        db.commit()
        return {'id': course.id, 'name': course.name}

    @app.post('/api/demo/load')
    def load_demo(db=Depends(database), user=Depends(current_user)):
        with app.state.course_locks['seed-' + user.id]:
            course = db.scalar(select(Course).where(Course.user_id == user.id, Course.name == 'Biology foundations · Demo'))
            if not course:
                course = Course(user_id=user.id, name='Biology foundations · Demo')
                db.add(course)
                db.commit()
            with app.state.course_locks[course.id]:
                for name, kind in [('syllabus.txt', 'syllabus'), ('biology_notes.txt', 'material'), ('past_paper.txt', 'past_paper')]:
                    ingest(db, app.state.vectors, settings, user.id, course.id, name, kind, (ROOT / 'sample_materials' / name).read_bytes())
                if not leaf_topics(db, course.id):
                    build_topics(db, app.state.generator, app.state.vectors, user.id, course.id)
                if not db.scalar(select(PaperQuestion).where(PaperQuestion.course_id == course.id)):
                    map_papers(db, app.state.generator, app.state.vectors, user.id, course.id)
        return {'id': course.id, 'name': course.name, 'notice': 'Sample material loaded. No attempts or scores were seeded.'}

    @app.get('/api/courses/{course_id}/documents')
    def documents(course=Depends(course_access), db=Depends(database)):
        return [{'id': d.id, 'filename': d.filename, 'kind': d.kind, 'pages': d.pages, 'warnings': d.warnings, 'created_at': d.created_at}
                for d in db.scalars(select(Document).where(Document.course_id == course.id).order_by(Document.created_at))]

    @app.post('/api/courses/{course_id}/documents', status_code=201)
    def upload(file: UploadFile = File(...), kind: str = Form(...), course=Depends(course_access), db=Depends(database)):
        with app.state.course_locks[course.id]:
            data = file.file.read(settings.max_upload_mb * 1024 * 1024 + 1)
            doc, duplicate = ingest(db, app.state.vectors, settings, course.user_id, course.id, file.filename or 'upload.txt', kind, data)
        return {'id': doc.id, 'filename': doc.filename, 'warnings': doc.warnings, 'duplicate': duplicate}

    @app.get('/api/courses/{course_id}/sources/{chunk_id}')
    def source(chunk_id: str, course=Depends(course_access), db=Depends(database)):
        chunk = db.scalar(select(Chunk).where(Chunk.id == chunk_id, Chunk.course_id == course.id, Chunk.user_id == course.user_id))
        if not chunk:
            raise HTTPException(404, 'Source not found.')
        return {**citation(chunk), 'text': chunk.text, 'quarantined': chunk.quarantined}

    @app.post('/api/courses/{course_id}/topics/build')
    def topic_build(course=Depends(course_access), db=Depends(database)):
        with app.state.course_locks[course.id]:
            result = build_topics(db, app.state.generator, app.state.vectors, course.user_id, course.id)
        return {'count': len(result)}

    @app.get('/api/courses/{course_id}/topics')
    def topics(course=Depends(course_access), db=Depends(database)):
        leaves = {t.id for t in leaf_topics(db, course.id)}
        return [{'id': t.id, 'name': t.name, 'path': t.path, 'parent_id': t.parent_id, 'is_leaf': t.id in leaves,
                 'weight': t.weight, 'frequency': t.frequency, 'marks': t.marks, 'citations': t.citations}
                for t in db.scalars(select(Topic).where(Topic.course_id == course.id).order_by(Topic.path))]

    @app.post('/api/courses/{course_id}/papers/map')
    def paper_map(course=Depends(course_access), db=Depends(database)):
        with app.state.course_locks[course.id]:
            result = map_papers(db, app.state.generator, app.state.vectors, course.user_id, course.id)
        return {'count': len(result)}

    @app.get('/api/courses/{course_id}/papers')
    def papers(course=Depends(course_access), db=Depends(database)):
        return [{'id': p.id, 'text': p.text, 'marks': p.marks, 'topic_id': p.topic_id, 'confidence': p.confidence,
                 'review_needed': p.review_needed, 'citation': p.citation}
                for p in db.scalars(select(PaperQuestion).where(PaperQuestion.course_id == course.id))]

    @app.patch('/api/courses/{course_id}/papers/{paper_id}')
    def correct_mapping(paper_id: str, data: MappingInput, course=Depends(course_access), db=Depends(database)):
        with app.state.course_locks[course.id]:
            paper = db.scalar(select(PaperQuestion).where(PaperQuestion.id == paper_id, PaperQuestion.course_id == course.id))
            if not paper or data.topic_id not in {t.id for t in leaf_topics(db, course.id)}:
                raise HTTPException(404, 'Question or topic not found.')
            paper.topic_id, paper.review_needed = data.topic_id, False
            db.flush()
            recalculate_weights(db, course.id)
            plan = latest_plan(db, course.id)
            if plan:
                build_plan(db, course.id, plan.days, plan.minutes_per_day, 'Refreshed after exam mapping changed.')
            db.commit()
        return {'ok': True}

    @app.post('/api/courses/{course_id}/quizzes', status_code=201)
    def quiz_create(data: QuizInput, course=Depends(course_access), db=Depends(database)):
        with app.state.course_locks[course.id]:
            existing = db.scalar(select(Quiz).where(Quiz.course_id == course.id, Quiz.status == 'ready'))
            if existing:
                return public_quiz(existing)
            return public_quiz(create_quiz(db, app.state.vectors, app.state.generator, course.user_id, course.id, data.topic_ids, data.per_topic))

    def find_quiz(db, course, quiz_id):
        quiz = db.scalar(select(Quiz).where(Quiz.id == quiz_id, Quiz.course_id == course.id, Quiz.user_id == course.user_id))
        if not quiz:
            raise HTTPException(404, 'Quiz not found.')
        return quiz

    @app.get('/api/courses/{course_id}/quizzes')
    def quiz_list(course=Depends(course_access), db=Depends(database)):
        return [{'id': q.id, 'status': q.status, 'score': q.score if q.status == 'submitted' else None,
                 'created_at': q.created_at, 'mode': q.mode} for q in db.scalars(select(Quiz).where(Quiz.course_id == course.id).order_by(Quiz.created_at.desc()))]

    @app.get('/api/courses/{course_id}/quizzes/{quiz_id}')
    def quiz_get(quiz_id: str, course=Depends(course_access), db=Depends(database)):
        return public_quiz(find_quiz(db, course, quiz_id))

    @app.delete('/api/courses/{course_id}/quizzes/{quiz_id}')
    def abandon_quiz(quiz_id: str, course=Depends(course_access), db=Depends(database)):
        with app.state.course_locks[course.id]:
            quiz = find_quiz(db, course, quiz_id)
            if quiz.status != 'ready':
                raise HTTPException(409, 'Only an unsubmitted quiz can be discarded.')
            quiz.status = 'abandoned'
            db.commit()
        return {'ok': True}

    @app.post('/api/courses/{course_id}/quizzes/{quiz_id}/submit')
    def submit(quiz_id: str, data: Submission, course=Depends(course_access), db=Depends(database)):
        with app.state.course_locks[course.id]:
            quiz = find_quiz(db, course, quiz_id)
            if quiz.status == 'submitted':
                return public_quiz(quiz)
            if quiz.status != 'ready':
                raise HTTPException(409, 'This quiz cannot be submitted.')
            # Atomic claim is rolled back on model/citation failure; retry remains possible.
            changed = db.execute(update(Quiz).where(Quiz.id == quiz.id, Quiz.status == 'ready').values(status='grading'))
            if changed.rowcount != 1:
                raise HTTPException(409, 'This quiz is already being submitted.')
            try:
                return public_quiz(grade_quiz(db, app.state.generator, quiz, data.answers))
            except Exception:
                db.rollback()
                raise

    @app.get('/api/courses/{course_id}/gaps')
    def gaps(course=Depends(course_access), db=Depends(database)):
        return gap_report(db, course.id)

    @app.get('/api/courses/{course_id}/progress')
    def get_progress(course=Depends(course_access), db=Depends(database)):
        return progress(db, course.id)

    def plan_json(plan):
        return None if not plan else {k: getattr(plan, k) for k in ('id', 'version', 'days', 'minutes_per_day', 'schedule', 'completed', 'reason', 'created_at')}

    @app.post('/api/courses/{course_id}/plan')
    def plan_create(data: PlanInput, course=Depends(course_access), db=Depends(database)):
        with app.state.course_locks[course.id]:
            plan = build_plan(db, course.id, data.days, data.minutes_per_day)
            db.commit()
        return plan_json(plan)

    @app.get('/api/courses/{course_id}/plan')
    def plan_get(course=Depends(course_access), db=Depends(database)):
        return plan_json(latest_plan(db, course.id))

    @app.patch('/api/courses/{course_id}/plan/{plan_id}')
    def plan_complete(plan_id: str, data: CompletionInput, course=Depends(course_access), db=Depends(database)):
        with app.state.course_locks[course.id]:
            plan = latest_plan(db, course.id)
            if not plan or plan.id != plan_id or data.task_id not in {t['id'] for d in plan.schedule for t in d['tasks']}:
                raise HTTPException(409, 'The plan changed. Refresh before marking a task.')
            completed = set(plan.completed)
            completed.add(data.task_id) if data.completed else completed.discard(data.task_id)
            plan.completed = sorted(completed)
            db.commit()
        return plan_json(plan)

    @app.post('/api/courses/{course_id}/tutor')
    def tutor(data: TutorInput, course=Depends(course_access), db=Depends(database)):
        with app.state.course_locks[course.id]:
            if db.scalar(select(Quiz).where(Quiz.course_id == course.id, Quiz.status.in_(['ready', 'grading']))):
                raise HTTPException(409, 'Submit or discard the current quiz before using the tutor.')
            topic = db.scalar(select(Topic).where(Topic.id == data.topic_id, Topic.course_id == course.id))
            if not topic:
                raise HTTPException(404, 'Topic not found.')
            blocks = app.state.vectors.retrieve(db, course.user_id, course.id, topic.path + ' ' + data.message)
            result = app.state.generator.tutor(topic.path, data.message, blocks)
            db.add(TutorMessage(course_id=course.id, topic_id=topic.id, question=data.message, response=result))
            db.commit()
        return result

    @app.get('/api/courses/{course_id}/tutor')
    def tutor_history(course=Depends(course_access), db=Depends(database)):
        rows = db.scalars(select(TutorMessage).where(TutorMessage.course_id == course.id).order_by(TutorMessage.created_at.desc()).limit(30))
        return [{'id': m.id, 'topic_id': m.topic_id, 'question': m.question, 'response': m.response} for m in reversed(list(rows))]

    # A production build can be served by the same FastAPI origin.
    dist = ROOT / 'frontend' / 'dist'
    if dist.exists():
        app.mount('/', StaticFiles(directory=dist, html=True), name='frontend')
    return app


app = create_app()
