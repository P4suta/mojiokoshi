# syntax=docker/dockerfile:1.9
#
# Multi-stage build:
#   1. frontend-build  — SvelteKit static build via Bun
#   2. uv              — pin the Astral uv binary for reproducibility
#   3. runtime         — CUDA + Python + venv, non-root, healthcheck

ARG UV_VERSION=latest
ARG CUDA_IMAGE=nvidia/cuda:12.6.3-cudnn-runtime-ubuntu24.04
ARG PYTHON_VERSION=3.12

# ===== Stage 1: frontend build =====
FROM oven/bun:1.3-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/bun.lock ./
RUN bun install --frozen-lockfile
COPY frontend/ .
RUN bun run build

# ===== Stage 2: pinned uv binary =====
FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv

# ===== Stage 3: CUDA runtime =====
FROM ${CUDA_IMAGE} AS runtime

ARG PYTHON_VERSION

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_NO_DEV=1 \
    PATH="/opt/venv/bin:$PATH" \
    MOJIOKOSHI_LOG_FORMAT=json \
    MOJIOKOSHI_LOG_LEVEL=INFO \
    MOJIOKOSHI_OPEN_BROWSER=false \
    NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility

# hadolint ignore=DL3008
RUN apt-get update && apt-get install -y --no-install-recommends \
        python${PYTHON_VERSION} \
        python${PYTHON_VERSION}-venv \
        ca-certificates \
        curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=uv /uv /uvx /usr/local/bin/

# Non-root runtime user.
RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --create-home --shell /bin/bash app \
    && mkdir -p /app /opt/venv \
    && chown -R app:app /app /opt/venv

WORKDIR /app

# --- Layer 1: deps only. Cache mount keeps uv's download cache warm across
#     builds without bloating the image.
RUN --mount=type=cache,target=/root/.cache/uv,sharing=locked \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev

# --- Layer 2: project source then install the project itself. Placing source
#     after the dep layer means code changes don't invalidate dep caches.
COPY --chown=app:app pyproject.toml uv.lock ./
COPY --chown=app:app src/ src/
RUN --mount=type=cache,target=/root/.cache/uv,sharing=locked \
    uv sync --locked --no-dev

# --- Frontend assets.
COPY --from=frontend-build --chown=app:app /app/frontend/build frontend/build/

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD curl --fail --silent --show-error http://localhost:8000/health || exit 1

# venv is on PATH, so the console_script runs directly without `uv run`.
CMD ["mojiokoshi"]
