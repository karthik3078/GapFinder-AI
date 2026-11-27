import pytest
from fastapi.testclient import TestClient
from backend.config import Settings
from backend.main import create_app


@pytest.fixture
def app(tmp_path):
    return create_app(Settings(_env_file=None, storage_dir=tmp_path, ai_mode='demo', embedding_provider='local', gemini_api_key='', seed_demo_user=True))


@pytest.fixture
def client(app):
    with TestClient(app) as client:
        yield client


@pytest.fixture
def student(client):
    assert client.post('/api/auth/login', json={'email': 'student@demo.com', 'password': 'demo123'}).status_code == 200
    return client


@pytest.fixture
def course(student):
    response = student.post('/api/demo/load')
    assert response.status_code == 200, response.text
    return response.json()['id']
