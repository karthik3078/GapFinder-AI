"""Load the fictional sample course through the same production pipeline."""
from fastapi.testclient import TestClient
from .main import create_app


def main():
    with TestClient(create_app()) as client:
        response = client.post('/api/auth/login', json={'email': 'student@demo.com', 'password': 'demo123'})
        response.raise_for_status()
        result = client.post('/api/demo/load')
        result.raise_for_status()
        print(result.json()['notice'])


if __name__ == '__main__':
    main()
