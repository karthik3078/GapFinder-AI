from concurrent.futures import ThreadPoolExecutor

from sqlalchemy import select

from backend.database import Course, LoginSession, Quiz, User


def url(course, path):
    return f'/api/courses/{course}/{path}'


def private_answers(app, quiz_id, correct=True):
    with app.state.sessions() as db:
        quiz = db.get(Quiz, quiz_id)
        return {q['id']: (str(q['answer_index']) if q['kind'] == 'mcq' else q['reference_answer']) if correct else '' for q in quiz.questions}


def test_demo_complete_loop(student, course, app):
    topics = student.get(url(course, 'topics')).json()
    leaves = [t for t in topics if t['is_leaf']]
    assert len(topics) == 9 and len(leaves) == 6
    assert abs(sum(t['weight'] for t in leaves) - 1) < 0.0001
    gaps = student.get(url(course, 'gaps')).json()
    assert all(t['status'] == 'not_assessed' and t['accuracy'] is None for t in gaps)
    assert student.get(url(course, 'progress')).json()['attempts'] == 0
    papers = student.get(url(course, 'papers')).json()
    assert len(papers) == 8
    assert all(0 <= p['confidence'] <= 1 and p['citation']['chunk_id'] for p in papers)
    plan = student.post(url(course, 'plan'), json={'days': 3, 'minutes_per_day': 41}).json()
    assert plan['version'] == 1
    assert all(d['minutes'] <= 41 and sum(t['minutes'] for t in d['tasks']) == d['minutes'] for d in plan['schedule'])
    created = student.post(url(course, 'quizzes'), json={})
    assert created.status_code == 201, created.text
    quiz = created.json()
    assert len(quiz['questions']) == 12 and not quiz['skipped']
    assert {q['kind'] for q in quiz['questions']} == {'mcq', 'short'}
    serialized = created.text
    for key in ('answer_index', 'reference_answer', 'rubric', 'explanation', 'quote', 'context_ids'):
        assert f'"{key}"' not in serialized
    assert student.post(url(course, 'tutor'), json={'topic_id': leaves[0]['id'], 'message': 'Explain this topic'}).status_code == 409
    result = student.post(url(course, f'quizzes/{quiz["id"]}/submit'), json={'answers': private_answers(app, quiz['id'], False)})
    assert result.status_code == 200, result.text
    assert result.json()['score'] == 0
    assert all(g['status'] == 'weak' for g in student.get(url(course, 'gaps')).json())
    assert student.get(url(course, 'plan')).json()['version'] == 2
    for r in result.json()['results']:
        assert r['citations'] and r['reference_answer']
    # A real retest of the same topics updates latest-topic accuracy and the plan.
    retest = student.post(url(course, 'quizzes'), json={}).json()
    result2 = student.post(url(course, f'quizzes/{retest["id"]}/submit'), json={'answers': private_answers(app, retest['id'])})
    assert result2.status_code == 200, result2.text
    assert result2.json()['score'] >= 0.8
    current = student.get(url(course, 'gaps')).json()
    assert all(g['status'] == 'strong' for g in current), current
    plan2 = student.get(url(course, 'plan')).json()
    assert plan2['version'] == 3
    assert all(t['topic_id'] is None for d in plan2['schedule'] for t in d['tasks'])
    dashboard = student.get(url(course, 'progress')).json()
    assert dashboard['attempts'] == 2 and dashboard['history'][0]['score'] == 0
    tutor = student.post(url(course, 'tutor'), json={'topic_id': leaves[0]['id'], 'message': 'Explain ' + leaves[0]['name']})
    assert tutor.status_code == 200 and tutor.json()['citations'], tutor.text


def test_demo_seed_idempotent(student, course):
    again = student.post('/api/demo/load').json()
    assert again['id'] == course
    assert len(student.get(url(course, 'documents')).json()) == 3
    assert len(student.get(url(course, 'topics')).json()) == 9


def test_submit_idempotent(student, course, app):
    quiz = student.post(url(course, 'quizzes'), json={}).json()
    first = student.post(url(course, f'quizzes/{quiz["id"]}/submit'), json={'answers': {}}).json()
    second = student.post(url(course, f'quizzes/{quiz["id"]}/submit'), json={'answers': private_answers(app, quiz['id'])}).json()
    assert first == second
    assert student.get(url(course, 'progress')).json()['attempts'] == 1


def test_partial_assessment_keeps_unknowns(student, course):
    leaf = next(t for t in student.get(url(course, 'topics')).json() if t['is_leaf'])
    quiz = student.post(url(course, 'quizzes'), json={'topic_ids': [leaf['id']]}).json()
    student.post(url(course, f'quizzes/{quiz["id"]}/submit'), json={'answers': {}})
    gaps = student.get(url(course, 'gaps')).json()
    assert sum(g['status'] == 'not_assessed' for g in gaps) == 5
    assert sum(g['status'] == 'weak' for g in gaps) == 1


def test_course_and_user_isolation(student, course, app):
    quiz = student.post(url(course, 'quizzes'), json={}).json()
    topic_id = quiz['questions'][0]['topic_id']
    source = quiz['questions'][0]['citations'][0]['chunk_id']
    other = student.post('/api/courses', json={'name': 'Unrelated course'}).json()['id']
    assert student.get(url(other, f'sources/{source}')).status_code == 404
    assert student.get(url(other, f'quizzes/{quiz["id"]}')).status_code == 404
    assert student.post(url(other, 'quizzes'), json={'topic_ids': [topic_id]}).status_code == 422
    assert student.post(url(other, 'tutor'), json={'topic_id': topic_id, 'message': 'Explain'}).status_code == 404
    with app.state.sessions() as db:
        owner = db.get(Course, course).user_id
        assert app.state.vectors.retrieve(db, owner, other, 'photosynthesis') == []
        assert app.state.vectors.retrieve(db, 'other-user', course, 'photosynthesis') == []
    student.post('/api/auth/logout')
    reg = student.post('/api/auth/register', json={'email': 'other@example.com', 'password': 'otherpassword', 'name': 'Other'})
    assert reg.status_code == 201
    for path in ('documents', 'topics', 'gaps', 'papers', 'plan', 'progress', 'quizzes', 'tutor', f'sources/{source}', f'quizzes/{quiz["id"]}'):
        assert student.get(url(course, path)).status_code == 404, path
    assert student.post(url(course, 'quizzes'), json={}).status_code == 404
    assert student.post(url(course, f'quizzes/{quiz["id"]}/submit'), json={'answers': {}}).status_code == 404


def test_password_hash_session_logout(client, app):
    response = client.post('/api/auth/login', json={'email': 'student@demo.com', 'password': 'demo123'})
    assert response.status_code == 200
    assert 'HttpOnly' in response.headers['set-cookie']
    assert 'SameSite=lax' in response.headers['set-cookie']
    token = client.cookies.get('gapfinder_session')
    with app.state.sessions() as db:
        user = db.scalar(select(User))
        assert 'demo123' not in user.password_hash
        assert user.password_hash.startswith('pbkdf2_sha256$600000$')
        assert db.scalar(select(LoginSession)).token_hash != token
    client.post('/api/auth/logout')
    client.cookies.set('gapfinder_session', token)
    assert client.get('/api/auth/me').status_code == 401


def test_origin_protection(student):
    r = student.post('/api/courses', json={'name': 'Injected'}, headers={'Origin': 'https://attacker.example'})
    assert r.status_code == 403


def test_invalid_answers_no_mutation(student, course):
    q = student.post(url(course, 'quizzes'), json={}).json()
    r = student.post(url(course, f'quizzes/{q["id"]}/submit'), json={'answers': {'foreign-question': '0'}})
    assert r.status_code == 422
    assert student.get(url(course, f'quizzes/{q["id"]}')).json()['status'] == 'ready'
    assert student.get(url(course, 'progress')).json()['attempts'] == 0


def test_plan_completion_and_stale_version(student, course):
    plan = student.post(url(course, 'plan'), json={'days': 2, 'minutes_per_day': 10}).json()
    task = plan['schedule'][0]['tasks'][0]
    marked = student.patch(url(course, f'plan/{plan["id"]}'), json={'task_id': task['id'], 'completed': True}).json()
    assert task['id'] in marked['completed']
    student.post(url(course, 'plan'), json={'days': 1, 'minutes_per_day': 20})
    assert student.patch(url(course, f'plan/{plan["id"]}'), json={'task_id': task['id'], 'completed': False}).status_code == 409
    assert student.post(url(course, 'plan'), json={'days': 0, 'minutes_per_day': 600}).status_code == 422


def test_mapping_correction_changes_weight(student, course):
    leaf = next(t for t in student.get(url(course, 'topics')).json() if t['is_leaf'])
    paper = student.get(url(course, 'papers')).json()[0]
    r = student.patch(url(course, f'papers/{paper["id"]}'), json={'topic_id': leaf['id']})
    assert r.status_code == 200
    updated = next(p for p in student.get(url(course, 'papers')).json() if p['id'] == paper['id'])
    assert not updated['review_needed'] and updated['topic_id'] == leaf['id']
    leaves = [t for t in student.get(url(course, 'topics')).json() if t['is_leaf']]
    assert abs(sum(t['weight'] for t in leaves) - 1) < 0.0001
