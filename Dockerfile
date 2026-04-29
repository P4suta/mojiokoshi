# syntax=docker/dockerfile:1.9
#
# Multi-stage build:
#   1. frontend-build  — SvelteKit static build via Bun.
#   2. uv              — pin the Astral uv binary for reproducibility.
#   3. builder         — CUDA + Python + uv → populate /opt/venv. Has uv,
#                        is thrown away (only its /opt/venv survives).
#   4. runtime         — fresh CUDA + Python + the venv from `builder`.
#                        DOES NOT contain the uv binary in any layer (it
#                        was never COPY'd in here), so Trivy has nothing to
#                        flag against bundled rust crates. A `RUN rm` after
#                        a `COPY` is NOT enough — Docker layers are
#                        append-only and Trivy reads every layer, so the
#                        binary still leaks via layer history. The fix is
#                        a clean stage that never received it.
#   5. dev             — `runtime` + uv re-installed (in its own layer here
#                        is fine, dev images are not deployed). Used by the
#                        devcontainer / compose.override.yaml hot-reload
#                        workflow where `uv sync`, `uv run`, etc. are part
#                        of the inner loop.

# Pin uv (not `latest`) so a Trivy hit on a bundled rust crate ties to a
# specific upstream release we can bump deliberately. CUDA stays in the 12.x
# line because CTranslate2 / faster-whisper 1.2 don't yet support CUDA 13.
ARG UV_VERSION=0.11.8
ARG CUDA_IMAGE=nvidia/cuda:12.9.1-cudnn-runtime-ubuntu24.04
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

# ===== Stage 3: builder — populate /opt/venv with uv =====
# This stage is intentionally not the final image. Only /opt/venv (and the
# project source under /app) get COPY'd into the runtime stage below; the
# uv binary stays here and is discarded with the rest of this layer set.
FROM ${CUDA_IMAGE} AS builder

ARG PYTHON_VERSION

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_NO_DEV=1

# hadolint ignore=DL3008
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        python${PYTHON_VERSION} \
        python${PYTHON_VERSION}-venv \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=uv /uv /uvx /usr/local/bin/

WORKDIR /app

# --- Layer 1: deps only. Cache mount keeps uv's download cache warm across
#     builds without bloating the image.
RUN --mount=type=cache,target=/root/.cache/uv,sharing=locked \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev

# --- Layer 2: project source then install the project itself. Placing source
#     after the dep layer means code changes don't invalidate dep caches.
COPY pyproject.toml uv.lock ./
COPY src/ src/
RUN --mount=type=cache,target=/root/.cache/uv,sharing=locked \
    uv sync --locked --no-dev

# ===== Stage 4: runtime — uv-free production image =====
FROM ${CUDA_IMAGE} AS runtime

ARG PYTHON_VERSION

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    MOJIOKOSHI_LOG_FORMAT=json \
    MOJIOKOSHI_LOG_LEVEL=INFO \
    MOJIOKOSHI_OPEN_BROWSER=false \
    NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility

# `apt-get upgrade` is intentional here: NVIDIA's CUDA images are rebuilt
# infrequently, so the Ubuntu 24.04 archive nearly always ships patched
# versions of glibc/openssl/gnupg/pam/etc. that the base image hasn't picked
# up yet. Pulling those patches at build time is what closes the bulk of the
# Trivy CVE backlog. DL3005 (no apt-get upgrade) is suppressed for that reason.
# We need the same python${PYTHON_VERSION}-venv as the builder so the venv's
# python symlink resolves; ca-certificates and curl are needed at runtime
# (TLS for the API + curl for the HEALTHCHECK).
# hadolint ignore=DL3005,DL3008
RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends \
        python${PYTHON_VERSION} \
        python${PYTHON_VERSION}-venv \
        ca-certificates \
        curl \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

# Non-root runtime user.
RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --create-home --shell /bin/bash app \
    && mkdir -p /app \
    && chown -R app:app /app

WORKDIR /app

# Bring in only the populated venv and the project source from the builder
# stage. The uv binary lives in the builder layers and never crosses over.
COPY --from=builder --chown=app:app /opt/venv /opt/venv
COPY --from=builder --chown=app:app /app /app

# Frontend assets.
COPY --from=frontend-build --chown=app:app /app/frontend/build frontend/build/

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD curl --fail --silent --show-error http://localhost:8000/health || exit 1

# venv is on PATH, so the console_script runs directly without `uv run`.
CMD ["mojiokoshi"]

# ===== Stage 5: dev (runtime + uv) =====
# Selected by compose.override.yaml / .devcontainer; not used for prod.
# We re-add the uv binary here so that:
#   * `uv sync` works inside the devcontainer postCreateCommand
#   * compose.override.yaml's `UV_NO_DEV=0` actually has something to act on
#   * `task lint` / `task test` (which shell out to `uv run …`) work
# The Trivy alerts on this image are accepted: dev images are not deployed.
FROM runtime AS dev
USER root
COPY --from=uv /uv /uvx /usr/local/bin/
USER app
