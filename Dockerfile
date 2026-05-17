# ---- Stage 1: Builder ----
FROM python:3.12-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
RUN pip install --upgrade pip && \
    pip install --no-cache-dir ".[dev]"

# ---- Stage 2: Runtime ----
FROM python:3.12-slim AS runtime

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy installed packages AND scripts from builder's system Python
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=appuser:appuser apps/ apps/
COPY --chown=appuser:appuser config/ config/
COPY --chown=appuser:appuser gunicorn.conf.py ./
COPY --chown=appuser:appuser manage.py ./
COPY --chown=appuser:appuser pyproject.toml ./

# OTel auto-instrumentation bootstrap
RUN opentelemetry-bootstrap -a install

RUN mkdir -p /app/staticfiles && chown appuser:appuser /app/staticfiles

USER appuser

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings

EXPOSE 8000

CMD ["gunicorn", "-c", "gunicorn.conf.py", "config.wsgi:application"]
