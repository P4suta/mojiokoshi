# Mojiokoshi

Local audio transcription tool with real-time progress display, powered by [faster-whisper](https://github.com/SYSTRAN/faster-whisper) and NVIDIA CUDA.

## Features

- **High-accuracy transcription** using Whisper large-v3 model by default
- **GPU-accelerated** with automatic CUDA detection and CPU fallback
- **Real-time progress** showing elapsed time, percentage, and ETA during transcription
- **Live segment display** as each part of the audio is transcribed
- **Multi-language support** with Japanese, English, Chinese, Korean, and auto-detection
- **Modern web UI** with dark/light theme, drag-and-drop upload, copy and download results
- **One-command startup** with background model loading and status display
- **Docker support** with GPU passthrough for zero-config deployment

## Quick Start

### Option 1: Docker (Recommended)

Requires [Docker](https://docs.docker.com/get-docker/) and [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html).

```bash
docker build -t mojiokoshi .
docker run --gpus all -p 8000:8000 mojiokoshi
```

Open http://localhost:8000 in your browser.

### Option 2: Local Installation

Requires [Python 3.12+](https://www.python.org/downloads/) and [uv](https://docs.astral.sh/uv/getting-started/installation/).

```bash
git clone https://github.com/your-username/mojiokoshi.git
cd mojiokoshi
uv sync
uv run mojiokoshi
```

The server starts immediately and opens your browser. The model downloads in the background on first run (~3 GB for large-v3).

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

The model is selected at server startup via `DEFAULT_MODEL` in `src/mojiokoshi/config.py`. Default: `large-v3`.

| Model | Parameters | VRAM (float16) | Speed | Accuracy | Best For |
|-------|-----------|----------------|-------|----------|----------|
| `tiny` | 39M | ~1 GB | Fastest | Lower | Quick drafts, testing |
| `base` | 74M | ~1 GB | Fast | Fair | Short clips |
| `small` | 244M | ~2 GB | Moderate | Good | General use |
| `medium` | 769M | ~5 GB | Slower | High | Important content |
| `large-v3` | 1.5B | ~6 GB | Slowest | Highest | Production (default) |

If your GPU doesn't have enough VRAM, the app will show an error. Switch to a smaller model or use CPU mode.

## Languages

| Language | Code |
|----------|------|
| Japanese | `ja` (default) |
| English | `en` |
| Chinese | `zh` |
| Korean | `ko` |
| Auto-detect | `auto` |

Auto-detect works well for most audio but specifying the language gives better results.

## Development Setup

### Prerequisites

- [Python 3.12+](https://www.python.org/downloads/)
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- [Bun](https://bun.sh/) (frontend package manager)
- NVIDIA GPU with CUDA 12+ (optional, falls back to CPU)

### Running in Development Mode

```bash
# Terminal 1: Backend (auto-reloads on changes)
uv sync --dev
uv run uvicorn mojiokoshi.main:app --reload --port 8000

# Terminal 2: Frontend (hot module replacement)
cd frontend
bun install
bun run dev
```

Open http://localhost:5173 (frontend dev server proxies API calls to the backend).

### Running Tests

```bash
# All tests with coverage
uv run pytest

# Quick test run without coverage
uv run pytest --no-cov

# Only unit tests
uv run pytest tests/unit/

# Property-based tests
uv run pytest tests/property/
```

Tests require 100% branch coverage to pass.

## Configuration

| Setting | Default | Location |
|---------|---------|----------|
| Default model | `large-v3` | `src/mojiokoshi/config.py` |
| Default language | `ja` | `src/mojiokoshi/config.py` |
| Max upload size | 500 MB | `src/mojiokoshi/config.py` |
| Transcription timeout | 30 minutes | `src/mojiokoshi/config.py` |
| Server port | 8000 | `src/mojiokoshi/main.py` |

To change defaults, edit `src/mojiokoshi/config.py` and restart the server.

## Troubleshooting

### "Model is still loading, please wait"

The model loads in the background after server startup. For `large-v3`, the first download is ~3 GB and may take several minutes. Subsequent starts use the cached model and load in seconds. Watch the startup status on the web UI.

### CUDA not detected (falling back to CPU)

- Ensure NVIDIA drivers are installed: `nvidia-smi`
- Check that CUDA 12+ is available
- For Docker, install [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html) and use `--gpus all`
- CPU mode works but is significantly slower (5-10x)

### Out of memory (OOM) error

Your GPU doesn't have enough VRAM for the selected model. Options:
- Switch to a smaller model (e.g., `small` or `medium`) in `config.py`
- Close other GPU-intensive applications
- Use CPU mode (slower but no VRAM limit)

### Transcription is slow

- **GPU recommended**: CPU transcription is 5-10x slower than GPU
- **Model size matters**: `tiny` is ~20x faster than `large-v3`
- **Long audio files**: A 1-hour file with `large-v3` on GPU takes ~2-5 minutes

### "Processing is taking longer than expected"

This warning appears if no new segments arrive for 30 seconds. It usually means the model is working on a difficult section (background noise, multiple speakers, etc.). Wait a bit longer or cancel and try with a smaller model.

### File upload fails

- Check file size (max 500 MB)
- Ensure the file format is supported (see table above)
- Try converting to MP3 or WAV first

### Docker build fails

- Ensure Docker has access to the internet for downloading dependencies
- The build requires ~10 GB of disk space (CUDA base image + model)
- On Windows, ensure WSL2 is configured for Docker

## Tech Stack

- **Backend**: Python 3.12, FastAPI, faster-whisper, uvicorn
- **Frontend**: Svelte 5, SvelteKit, Tailwind CSS 4, Vite 8
- **Transcription**: faster-whisper (CTranslate2-based Whisper implementation)
- **Package Managers**: uv (Python), Bun (JavaScript)
- **Container**: Docker with NVIDIA CUDA 12.6.3

## License

MIT License. See [LICENSE](LICENSE) for details.
