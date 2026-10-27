'''Тесты health-check backend (skeleton T-005).'''
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_health_status_ok(client):
    response = client.get('/api/v1/health')
    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'ok'
    assert data['service'] == 'ai-exam-checker-backend'
    assert data['version'] == '0.1.0'


def test_health_request_id_echoed(client):
    req_id = 'c3f1c0de-0000-4000-8000-000000000000'
    response = client.get('/api/v1/health', headers={'X-Request-ID': req_id})
    assert response.status_code == 200
    assert response.headers.get('x-request-id') == req_id
