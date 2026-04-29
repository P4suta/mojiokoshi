# Mojiokoshi

Local audio transcription tool with real-time progress display, powered by [faster-whisper](https://github.com/SYSTRAN/faster-whisper) and NVIDIA CUDA.

## Features

- **High-accuracy transcription** using Whisper large-v3 model by default
- **GPU-accelerated** with automatic CUDA detection and CPU fallback
- **Real-time progress** showing elapsed time, percentage, and ETA during transcription
- **Live segment display** as each part of the audio is transcribed
- **Multi-language support** with Japanese, English, Chinese, Korean, and auto-detection
- **Modern web UI** with dark/light theme, drag-and-drop upload, copy and download results
- **Structured logs and RFC 7807 error responses** for easier debugging and monitoring
- **Docker-first workflow** with GPU passthrough for zero-config deployment

## Quick Start

Requires [Docker](https://docs.docker.com/get-docker/) and, for GPU acceleration, the [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html).

```bash
git clone https://github.com/P4suta/mojiokoshi.git
cd mojiokoshi
docker compose up
```

Then open <http://localhost:8000> in your browser.

The first run downloads the Whisper model (~3 GB for `large-v3`) into a persistent Docker volume, so subsequent starts are fast.

> No host-side Python or Node install is needed — everything runs inside containers.

## How It Works

1. **Upload** an audio file (drag-and-drop or click to browse)
2. **Select language** (defaults to Japanese, or choose auto-detect)
3. **Click Transcribe** and watch results appear in real-time
4. **Copy or download** the transcription as a text file

During transcription, you'll see:
- A progress bar with percentage
- Elapsed time and estimated time remaining
- Each segment as it's transcribed with timestamps

## Supported Audio Formats

| Format | Extension |
|--------|-----------|
| MP3 | `.mp3` |
| WAV | `.wav` |
| M4A | `.m4a` |
| OGG | `.ogg` |
| FLAC | `.flac` |
| WebM | `.webm` |
| WMA | `.wma` |
| AAC | `.aac` |

Maximum file size: **500 MB**

## Models

| Model | Parameters | VRAM (float16) | Speed | Accuracy | Best For |
|-------|-----------|----------------|-------|----------|----------|
| `tiny` | 39M | ~1 GB | Fastest | Lower | Quick drafts, testing |
| `base` | 74M | ~1 GB | Fast | Fair | Short clips |
| `small` | 244M | ~2 GB | Moderate | Good | General use |
| `medium` | 769M | ~5 GB | Slower | High | Important content |
| `large-v3` | 1.5B | ~6 GB | Slowest | Highest | Production (default) |

If your GPU doesn't have enough VRAM, either switch to a smaller model or let the app fall back to CPU (slower, but no VRAM limit).

## Languages

| Language | Code |
|----------|------|
| Japanese | `ja` (default) |
| English | `en` |
| Chinese | `zh` |
| Korean | `ko` |
| Auto-detect | `auto` |

Auto-detect works well for most audio, but specifying the language usually yields better results.

## Configuration

All runtime behavior is controlled via `MOJIOKOSHI_*` environment variables (or a local `.env` file). Commonly-tweaked values:

| Variable | Default | Description |
|----------|---------|-------------|
| `MOJIOKOSHI_LOG_FORMAT` | `console` | `json` for structured/prod-style logs, `console` for dev |
| `MOJIOKOSHI_LOG_LEVEL` | `INFO` | `DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL` |
| `MOJIOKOSHI_PORT` | `8000` | Web UI / API port |
| `MOJIOKOSHI_DEFAULT_MODEL` | `large-v3` | Any Whisper model name |
| `MOJIOKOSHI_OPEN_BROWSER` | `true` | Whether to auto-open a browser tab on startup |
| `MOJIOKOSHI_SENTRY_DSN` | *(unset)* | Enables Sentry error reporting when set (requires the `observability` extra) |

Larger fixed values (supported formats, upload size cap, transcription timeout) live in `src/mojiokoshi/config.py`.

## Development

The project is Docker-first: all tooling (Python, uv, ruff, pytest, pyrefly) runs inside the container, so you don't need to install anything on the host besides Docker.

### Option A — VS Code Dev Containers

1. Install the [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers).
2. Open the repo and run **"Dev Containers: Reopen in Container"**.
3. VS Code drops you into `/app` with the venv already synced and pre-commit hooks installed.

### Option B — Taskfile on the host

With [Task](https://taskfile.dev/installation/) installed, all common dev commands are one-liners:

```bash
task up             # Start the dev stack (GPU + hot reload)
task shell          # Shell into the app container
task lint           # ruff + pyrefly (read-only)
task fix            # ruff --fix + ruff format (writes)
task test           # Fast test suite
task test:all       # Full suite including integration/slow marks
task precommit      # Run all pre-commit hooks
task down           # Stop the dev stack
```

### Running Tests

Tests are enforced at 100% branch coverage.

```bash
task test           # Fast suite
task test:all       # Include integration + slow tests
```

### Linting and Formatting

Ruff (strict ruleset) and pyrefly run on every PR. Locally:

```bash
task lint           # Check only
task fix            # Auto-fix + format
```

Pre-commit hooks (ruff, gitleaks, hadolint, zizmor, standard hygiene) are installed automatically in the Dev Container; outside of it, run `pre-commit install` once.

## Troubleshooting

### "Model is still loading, please wait"

The model loads in the background after server startup. For `large-v3`, the first download is ~3 GB and may take several minutes. Subsequent starts use the cached model and load in seconds. Watch the startup status on the web UI.

### CUDA not detected (falling back to CPU)

- Ensure NVIDIA drivers are installed: `nvidia-smi`
- Check that CUDA 12+ is available
- For Docker, install the [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html)
- CPU mode works but is significantly slower (5–10×)

### Out of memory (OOM) error

Your GPU doesn't have enough VRAM for the selected model. Options:
- Switch to a smaller model by setting `MOJIOKOSHI_DEFAULT_MODEL=small`
- Close other GPU-intensive applications
- Use CPU mode (slower but no VRAM limit)

### Transcription is slow

- **GPU recommended**: CPU transcription is 5–10× slower than GPU
- **Model size matters**: `tiny` is ~20× faster than `large-v3`
- **Long audio files**: A 1-hour file with `large-v3` on GPU takes ~2–5 minutes

### "Processing is taking longer than expected"

This warning appears if no new segments arrive for 30 seconds. It usually means the model is working on a difficult section (background noise, multiple speakers, etc.). Wait a bit longer, or cancel and retry with a smaller model.

### File upload fails

- Check file size (max 500 MB)
- Ensure the file format is supported (see table above)
- Try converting to MP3 or WAV first

### Docker build fails

- Ensure Docker has network access for pulling dependencies
- The build requires ~10 GB of disk space (CUDA base image + model)
- On Windows, ensure WSL2 is configured for Docker

## Tech Stack

- **Backend**: Python 3.12, FastAPI, faster-whisper, uvicorn, structlog, pydantic-settings
- **Frontend**: Svelte 5, SvelteKit, Tailwind CSS 4, Vite 8
- **Transcription**: faster-whisper (CTranslate2-based Whisper implementation)
- **Package managers**: uv (Python), Bun (JavaScript)
- **Container**: Docker multi-stage build on NVIDIA CUDA 12.9.1

## License

MIT License. See [LICENSE](LICENSE) for details.
