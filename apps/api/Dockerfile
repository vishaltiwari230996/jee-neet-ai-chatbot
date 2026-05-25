# syntax=docker/dockerfile:1.7
# Multi-stage build:
#   1. base   — Python + uv installed
#   2. deps   — install workspace deps (cached when pyproject.toml unchanged)
#   3. final  — copy source, drop privileges, run uvicorn
ARG PYTHON_VERSION=3.12

FROM python:${PYTHON_VERSION}-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON=python3.12 \
    PATH="/opt/venv/bin:$PATH"

RUN apt-get update \
 && apt-get install -y --no-install-recommends curl ca-certificates \
 && rm -rf /var/lib/apt/lists/* \
 && pip install --no-cache-dir uv

WORKDIR /app

FROM base AS deps
COPY pyproject.toml uv.lock* ./
COPY apps/api/pyproject.toml apps/api/
COPY packages/ packages/
COPY adapters/ adapters/
RUN uv sync --frozen --no-dev --package neetai-api 2>/dev/null \
 || uv sync --no-dev --package neetai-api

FROM base AS final
RUN useradd --create-home --uid 10001 neetai
WORKDIR /app

COPY --from=deps /app/.venv /app/.venv
COPY --chown=neetai:neetai packages/ packages/
COPY --chown=neetai:neetai adapters/ adapters/
COPY --chown=neetai:neetai apps/api/ apps/api/

USER neetai
ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD curl -fsS "http://127.0.0.1:${PORT:-8000}/health/live" || exit 1

CMD ["sh", "-c", "uvicorn neetai_api.main:create_app --factory --host 0.0.0.0 --port ${PORT:-8000}"]
