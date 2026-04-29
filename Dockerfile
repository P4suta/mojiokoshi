# syntax=docker/dockerfile:1.9
#
# Multi-stage build:
#   1. frontend-build  — SvelteKit static build via Bun
#   2. uv              — pin the Astral uv binary for reproducibility
#   3. runtime         — CUDA + Python + venv, non-root, healthcheck.
#                        DOES NOT ship the uv binary — uv is a build tool
#                        used to populate /opt/venv, never executed at
#                        runtime. Removing it shrinks the trust surface
#                        (one fewer statically-linked rust binary for Trivy
#                        to scan against bundled-crate CVEs).
#   4. dev             — `runtime` + uv re-installed, for devcontainer /
#                        compose.override.yaml hot-reload workflows where
#                        `uv sync`, `uv run`, etc. are part of the loop.

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

# `apt-get upgrade` is intentional here: NVIDIA's CUDA images are rebuilt
# infrequently, so the Ubuntu 24.04 archive nearly always ships patched
# versions of glibc/openssl/gnupg/pam/etc. that the base image hasn't picked
# up yet. Pulling those patches at build time is what closes the bulk of the
# Trivy CVE backlog. DL3005 (no apt-get upgrade) is suppressed for that reason.
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

# uv is mounted into /usr/local/bin only for the build steps below; it is
# removed before the runtime stage finalizes (see the rm at the end of this
# stage). The `dev` stage re-adds it for interactive workflows.
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

# Drop the build-only uv binary so Trivy doesn't keep flagging the rust
# crates statically linked into it (rand / rustls-webpki / etc.) when those
# advisories don't actually affect production code paths — uv is never
# invoked at runtime. The `dev` stage below copies it back for interactive
# use in the devcontainer.
RUN rm -f /usr/local/bin/uv /usr/local/bin/uvx

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD curl --fail --silent --show-error http://localhost:8000/health || exit 1

# venv is on PATH, so the console_script runs directly without `uv run`.
CMD ["mojiokoshi"]

# ===== Stage 4: dev (runtime + uv) =====
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
