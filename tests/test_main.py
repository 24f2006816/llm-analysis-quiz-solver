from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_invalid_secret():
    response = client.post("/solve", json={
        "email": "x@y.com",
        "secret": "wrong",
        "url": "https://example.com"
    })
    assert response.status_code == 403
