from fastapi.testclient import TestClient

from backend.config import Settings
from backend.main import create_app


def test_sql_and_vectors_survive_restart(tmp_path):
    settings = Settings(_env_file=None, storage_dir=tmp_path, ai_mode='demo', embedding_provider='local', gemini_api_key='')
    with TestClient(create_app(settings)) as client:
        client.post('/api/auth/login', json={'email': 'student@demo.com', 'password': 'demo123'})
        course = client.post('/api/demo/load').json()['id']
        quiz = client.post(f'/api/courses/{course}/quizzes', json={}).json()
        client.post(f'/api/courses/{course}/quizzes/{quiz["id"]}/submit', json={'answers': {}})
        client.post(f'/api/courses/{course}/plan', json={'days': 2, 'minutes_per_day': 25})
    with TestClient(create_app(settings)) as client:
        client.post('/api/auth/login', json={'email': 'student@demo.com', 'password': 'demo123'})
        assert client.get(f'/api/courses/{course}/progress').json()['attempts'] == 1
        assert client.get(f'/api/courses/{course}/plan').json()['days'] == 2
        leaf = next(t for t in client.get(f'/api/courses/{course}/topics').json() if t['is_leaf'])
        response = client.post(f'/api/courses/{course}/tutor', json={'topic_id': leaf['id'], 'message': 'Explain ' + leaf['name']})
        assert response.json()['citations']
