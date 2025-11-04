"""
Tests for main.py API endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_root_endpoint():
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()
    assert "endpoints" in response.json()


def test_health_endpoint():
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_solve_endpoint_invalid_secret():
    """Test solve endpoint with invalid secret."""
    response = client.post(
        "/solve",
        json={
            "email": "test@example.com",
            "secret": "wrong-secret",
            "url": "https://example.com/quiz"
        }
    )
    assert response.status_code == 403
    assert "invalid secret" in response.json()["detail"].lower()


def test_solve_endpoint_missing_url():
    """Test solve endpoint with missing URL."""
    from app.config import SECRET
    
    response = client.post(
        "/solve",
        json={
            "email": "test@example.com",
            "secret": SECRET,
            "url": ""
        }
    )
    assert response.status_code == 422  # Validation error


def test_solve_endpoint_invalid_email():
    """Test solve endpoint with invalid email."""
    from app.config import SECRET
    
    response = client.post(
        "/solve",
        json={
            "email": "invalid-email",
            "secret": SECRET,
            "url": "https://example.com/quiz"
        }
    )
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_solve_endpoint_valid_request():
    """Test solve endpoint with valid request (mocked)."""
    # This would require mocking Playwright and HTTP requests
    # Implementation depends on testing strategy
    pass

