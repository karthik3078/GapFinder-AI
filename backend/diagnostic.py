"""Assessment, explainable diagnosis, and deterministic budget enforcement."""
from sqlalchemy import select

from .database import Chunk, Quiz, RevisionPlan, now, uid
from .generation import EvidenceError
from .topics import leaf_topics


def public_quiz(quiz):
    # Explicit allowlist: never serialize private question dictionaries directly.
    questions = []
    for q in quiz.questions:
        citations = [{k: c[k] for k in ('chunk_id', 'document_id', 'filename', 'page', 'section')} for c in q['citations']]
        questions.append({k: q[k] for k in ('id', 'topic_id', 'topic_name', 'kind', 'prompt', 'options')} | {'citations': citations})
    data = {'id': quiz.id, 'mode': quiz.mode, 'status': quiz.status, 'created_at': quiz.created_at,
            'questions': questions, 'skipped': quiz.skipped}
    if quiz.status == 'submitted':
        data.update(score=quiz.score, results=quiz.results, answers=quiz.answers, submitted_at=quiz.submitted_at)
    return data


def create_quiz(db, vectors, generator, user_id, course_id, topic_ids, per_topic):
    leaves = leaf_topics(db, course_id)
    allowed = {t.id: t for t in leaves}
    if topic_ids and any(t not in allowed for t in topic_ids):
        raise EvidenceError('Choose assessable topics from this course.')
    report = gap_report(db, course_id)
    targets = list(dict.fromkeys(topic_ids)) if topic_ids else [g['id'] for g in sorted(report, key=lambda g: -g['priority'])[:6]]
    if not targets:
        raise EvidenceError('Build the syllabus topic map first.')
    questions, skipped = [], []
    for topic_id in targets:
        topic = allowed[topic_id]
        blocks = vectors.retrieve(db, user_id, course_id, topic.path)
        try:
            generated = generator.questions(topic.path, blocks, per_topic)
        except EvidenceError as exc:
            skipped.append({'topic': topic.name, 'reason': str(exc)})
            continue
        for question in generated:
            questions.append(question | {'id': uid(), 'topic_id': topic.id, 'topic_name': topic.name,
                'context_ids': [b['chunk_id'] for b in blocks]})
    if not questions:
        raise EvidenceError('No supported diagnostic questions could be created. Add clearer study material for the selected topics.')
    quiz = Quiz(user_id=user_id, course_id=course_id, mode=generator.settings.ai_mode,
                questions=questions, skipped=skipped)
    db.add(quiz)
    db.commit()
    return quiz


def grade_quiz(db, generator, quiz, answers):
    ids = {q['id'] for q in quiz.questions}
    if not set(answers).issubset(ids):
        raise EvidenceError('Submission contains an unknown question.')
    results = []
    for q in quiz.questions:
        answer = answers.get(q['id'], '').strip()
        if q['kind'] == 'mcq':
            if answer and answer not in ('0', '1', '2', '3'):
                raise EvidenceError('MCQ answers must be option indexes from 0 to 3.')
            score = float(answer == str(q['answer_index']))
            grade = {'score': score, 'feedback': ('Correct. ' if score else 'Incorrect or unanswered. ') + q['explanation'],
                     'citations': q['citations'], 'method': 'deterministic_mcq'}
        elif not answer:
            grade = {'score': 0, 'feedback': 'No answer submitted. ' + q['explanation'], 'citations': q['citations'], 'method': 'unanswered'}
        else:
            chunks = list(db.scalars(select(Chunk).where(Chunk.id.in_(q['context_ids']), Chunk.user_id == quiz.user_id,
                Chunk.course_id == quiz.course_id, Chunk.kind == 'material', Chunk.quarantined.is_(False))))
            from .ingestion import citation
            blocks = [{**citation(c), 'text': c.text} for c in chunks]
            if not blocks:
                raise EvidenceError('The question evidence is no longer available. No score was saved.')
            grade = generator.grade_short(q, answer, blocks)
        results.append({'question_id': q['id'], 'topic_id': q['topic_id'], 'topic_name': q['topic_name'],
                        'prompt': q['prompt'], 'answer': answer, 'reference_answer': q['reference_answer'],
                        'answer_index': q['answer_index'], 'rubric': q['rubric'], **grade})
    quiz.answers, quiz.results, quiz.status = answers, results, 'submitted'
    quiz.score = round(sum(r['score'] for r in results) / len(results), 4)
    quiz.submitted_at = now()
    db.flush()
    previous = latest_plan(db, quiz.course_id)
    if previous:
        build_plan(db, quiz.course_id, previous.days, previous.minutes_per_day, 'Automatically refreshed after a diagnostic submission.')
    db.commit()
    return quiz


def classify(accuracy):
    if accuracy is None:
        return 'not_assessed'
    return 'weak' if accuracy < 0.5 else 'medium' if accuracy < 0.8 else 'strong'


def gap_report(db, course_id):
    quizzes = list(db.scalars(select(Quiz).where(Quiz.course_id == course_id, Quiz.status == 'submitted').order_by(Quiz.submitted_at, Quiz.id)))
    report = []
    leaves = leaf_topics(db, course_id)
    for topic in leaves:
        histories = [[r for r in q.results if r['topic_id'] == topic.id] for q in quizzes]
        histories = [r for r in histories if r]
        recent = histories[-1] if histories else []
        accuracy = sum(r['score'] for r in recent) / len(recent) if recent else None
        status = classify(accuracy)
        priority = (1 - accuracy if accuracy is not None else 0.75) * topic.weight
        if status == 'not_assessed':
            reason = 'No answers assessed yet. This is an evidence gap, not a measured weakness.'
        else:
            full = sum(r['score'] == 1 for r in recent)
            reason = f'{round(accuracy * 100)}% earned credit; {full}/{len(recent)} fully correct in the latest topic assessment.'
        report.append({'id': topic.id, 'name': topic.name, 'path': topic.path, 'status': status,
            'accuracy': accuracy, 'weight': topic.weight, 'frequency': topic.frequency, 'marks': topic.marks,
            'priority': priority, 'reason': reason, 'assessed_questions': len(recent),
            'lifetime_questions': sum(map(len, histories)), 'assessment_count': len(histories),
            'limited_evidence': len(recent) < 3,
            'high_weight_unassessed': not recent and topic.weight > 1 / max(1, len(leaves)),
            'review_points': [r['feedback'] for r in recent if r['score'] < 1][:3],
            'citations': topic.citations})
    return sorted(report, key=lambda g: (-g['priority'], g['name']))


def latest_plan(db, course_id):
    return db.scalar(select(RevisionPlan).where(RevisionPlan.course_id == course_id).order_by(RevisionPlan.version.desc()).limit(1))


def build_plan(db, course_id, days, minutes, reason='Created from current topic evidence.'):
    report = gap_report(db, course_id)
    if not report:
        raise EvidenceError('Build a topic map before planning.')
    # Strong topics are reserved for self-check, never treated as unresolved gaps.
    targets = [g for g in report if g['status'] != 'strong']
    targets.sort(key=lambda g: (-g['priority'], g['name']))
    previous = latest_plan(db, course_id)
    schedule = []
    total_priority = sum(g['priority'] for g in targets) or 1
    for day in range(1, days + 1):
        tasks, left = [], minutes
        # Integer allocation obeys the budget exactly, using largest remainders.
        if targets:
            allocations = [int(minutes * g['priority'] / total_priority) for g in targets]
            remainder = minutes - sum(allocations)
            order = sorted(range(len(targets)), key=lambda i: -(minutes * targets[i]['priority'] / total_priority - allocations[i]))
            for i in order[:remainder]:
                allocations[i] += 1
            for g, allocated in zip(targets, allocations):
                if allocated <= 0:
                    continue
                action = 'Diagnose before revising' if g['status'] == 'not_assessed' else 'Review evidence, recall without notes, then retest'
                tasks.append({'id': uid(), 'topic_id': g['id'], 'topic': g['name'], 'minutes': allocated,
                    'action': action, 'reason': g['reason'], 'status': g['status'], 'priority': round(g['priority'], 4),
                    'source_citations': g['citations']})
                left -= allocated
        else:
            tasks.append({'id': uid(), 'topic_id': None, 'topic': 'Maintenance self-check', 'minutes': min(20, minutes),
                'action': 'Retest a topic to check retention', 'reason': 'All assessed topics are currently strong.', 'status': 'strong', 'priority': 0, 'source_citations': []})
            left -= min(20, minutes)
        schedule.append({'day': day, 'minutes': minutes - left, 'free_minutes': left, 'tasks': tasks})
    plan = RevisionPlan(course_id=course_id, version=previous.version + 1 if previous else 1,
                        days=days, minutes_per_day=minutes, schedule=schedule, reason=reason)
    db.add(plan)
    db.flush()
    return plan


def progress(db, course_id):
    quizzes = list(db.scalars(select(Quiz).where(Quiz.course_id == course_id, Quiz.status == 'submitted').order_by(Quiz.submitted_at, Quiz.id)))
    history = []
    for i, quiz in enumerate(quizzes, 1):
        topic_scores = {}
        for r in quiz.results:
            topic_scores.setdefault(r['topic_id'], {'name': r['topic_name'], 'scores': []})['scores'].append(r['score'])
        history.append({'id': quiz.id, 'attempt': i, 'score': quiz.score, 'mode': quiz.mode, 'date': quiz.submitted_at,
                        'topics': [{'id': tid, 'name': v['name'], 'score': sum(v['scores']) / len(v['scores'])} for tid, v in topic_scores.items()]})
    gaps = gap_report(db, course_id)
    return {'history': history, 'assessed_topics': sum(g['status'] != 'not_assessed' for g in gaps), 'total_topics': len(gaps),
            'strong_topics': sum(g['status'] == 'strong' for g in gaps), 'attempts': len(quizzes)}
