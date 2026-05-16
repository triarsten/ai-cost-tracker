import logging

from django.conf import settings
from django.db import connection
from django.http import JsonResponse

logger = logging.getLogger(__name__)


def health_check(request):
    status = {"status": "ok", "db": "ok", "redis": "ok"}
    http_status = 200

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception:
        logger.exception("Health check: DB connection failed")
        status["db"] = "error"
        status["status"] = "error"
        http_status = 503

    try:
        import redis

        r = redis.from_url(settings.REDIS_URL)
        r.ping()
    except Exception:
        logger.exception("Health check: Redis connection failed")
        status["redis"] = "error"
        status["status"] = "error"
        http_status = 503

    return JsonResponse(status, status=http_status)
