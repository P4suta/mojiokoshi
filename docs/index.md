---
title: Mojiokoshi
---

**Mojiokoshi** is a self-hosted audio transcription tool with a real-time
progress UI, powered by [faster-whisper](https://github.com/SYSTRAN/faster-whisper)
and NVIDIA CUDA. It runs entirely on your own machine — your audio never leaves it.

[View on GitHub](https://github.com/P4suta/mojiokoshi){: .btn }

## Highlights

- **High-accuracy transcription** with the Whisper `large-v3` model by default
- **GPU-accelerated** with automatic CUDA detection and CPU fallback
- **Real-time progress** — elapsed time, percentage, ETA, and live segments as they decode
- **Multi-language** — Japanese, English, Chinese, Korean, and auto-detect
- **Modern web UI** — dark/light theme, drag-and-drop upload, copy & download
- **Docker-first** with GPU passthrough for zero-config deployment

## Quick Start

Requires [Docker](https://docs.docker.com/get-docker/) and, for GPU acceleration,
the [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html).

```bash
git clone https://github.com/P4suta/mojiokoshi.git
cd mojiokoshi
docker compose up
```

Then open <http://localhost:8000> in your browser. The first run downloads the
Whisper model (~3 GB for `large-v3`) into a persistent volume, so later starts
are fast. No host-side Python or Node is needed — everything runs in containers.

## At a glance

| | |
|---|---|
| **Models** | `tiny` · `base` · `small` · `medium` · `large-v3` (default) |
| **Languages** | Japanese (default) · English · Chinese · Korean · auto-detect |
| **Audio formats** | MP3 · WAV · M4A · OGG · FLAC · WebM · WMA · AAC (≤ 500 MB) |
| **Backend** | Python 3.12 · FastAPI · faster-whisper · uvicorn |
| **Frontend** | Svelte 5 · SvelteKit · Tailwind CSS 4 · Vite 8 |
| **Container** | Docker multi-stage build on NVIDIA CUDA 12.9.1 |

## Learn more

- [Full README](https://github.com/P4suta/mojiokoshi#readme) — configuration, development, troubleshooting
- [Report an issue](https://github.com/P4suta/mojiokoshi/issues)
- [License](https://github.com/P4suta/mojiokoshi/blob/main/LICENSE) — MIT
