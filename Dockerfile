# syntax=docker/dockerfile:1
#
# Multi-stage build for the ACEest Fitness & Gym Flask application.
#   docker build --target test -t aceest-fitness:test .   -> image that runs the Pytest suite
#   docker build -t aceest-fitness:latest .                -> slim, non-root production image

ARG PYTHON_VERSION=3.13

# ---------- base: shared Python settings ----------
FROM python:${PYTHON_VERSION}-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app

# ---------- builder: runtime dependencies in an isolated virtualenv ----------
FROM base AS builder
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt .
RUN pip install -r requirements.txt

# ---------- test: adds dev dependencies and tests; runs Pytest by default ----------
FROM builder AS test
COPY requirements-dev.txt .
RUN pip install -r requirements-dev.txt
COPY . .
CMD ["pytest", "-v", "--cov", "--cov-report=term-missing"]

# ---------- runtime: only the virtualenv and application code ----------
FROM base AS runtime
LABEL org.opencontainers.image.title="aceest-fitness" \
      org.opencontainers.image.description="ACEest Fitness & Gym Flask application"

# Unprivileged user; /data holds the SQLite database (mount a volume to persist it).
RUN groupadd --system --gid 10001 aceest \
 && useradd --system --uid 10001 --gid aceest --no-create-home --shell /usr/sbin/nologin aceest \
 && mkdir /data \
 && chown aceest:aceest /data

COPY --from=builder /opt/venv /opt/venv
# Application files stay owned by root, so the app user cannot modify them.
COPY *.py schema.sql ./
COPY templates/ templates/

ENV PATH="/opt/venv/bin:$PATH" \
    ACEEST_DATABASE=/data/aceest_fitness.db

USER aceest
EXPOSE 5000
VOLUME ["/data"]

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/health', timeout=2)"]

# The control socket is not needed in a container (and the user has no home directory).
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--preload", \
     "--no-control-socket", "--access-logfile", "-", "app:create_app()"]
