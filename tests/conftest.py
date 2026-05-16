import os

# Env-Vars VOR dem Laden der Django-Settings setzen
os.environ.setdefault("SECRET_KEY", "test-secret-key-do-not-use-in-prod")
os.environ.setdefault("DATABASE_URL", "sqlite://:memory:")
os.environ.setdefault("OTEL_ENABLED", "false")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
os.environ.setdefault("ALLOWED_HOSTS", "localhost,127.0.0.1")

import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def configure_test_settings(settings):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True


@pytest.fixture
def provider(db):
    from apps.costs.models import Provider

    return Provider.objects.create(name="anthropic", display_name="Anthropic")
