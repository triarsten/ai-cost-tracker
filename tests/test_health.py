from unittest.mock import MagicMock, patch

import pytest
from django.test import Client


@pytest.fixture
def client():
    return Client()


@pytest.mark.django_db
def test_health_check_ok(client):
    with patch("apps.health.views.connection") as mock_conn, patch("apps.health.views.redis") as mock_redis:
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = lambda s: mock_cursor
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        mock_redis_instance = MagicMock()
        mock_redis.from_url.return_value = mock_redis_instance

        response = client.get("/health/")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["db"] == "ok"
    assert data["redis"] == "ok"


@pytest.mark.django_db
def test_health_check_db_failure(client):
    with patch("apps.health.views.connection") as mock_conn, patch("apps.health.views.redis") as mock_redis:
        mock_conn.cursor.side_effect = Exception("DB down")

        mock_redis_instance = MagicMock()
        mock_redis.from_url.return_value = mock_redis_instance

        response = client.get("/health/")

    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "error"
    assert data["db"] == "error"


@pytest.mark.django_db
def test_health_check_redis_failure(client):
    with patch("apps.health.views.connection") as mock_conn, patch("apps.health.views.redis") as mock_redis:
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = lambda s: mock_cursor
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        mock_redis.from_url.side_effect = Exception("Redis down")

        response = client.get("/health/")

    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "error"
    assert data["redis"] == "error"
