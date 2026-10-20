# Mojiokoshi

Transcribe local audio in a browser with faster-whisper, live progress, and downloadable text.

## Run

The Compose setup requires Docker, an NVIDIA GPU, its driver, and the NVIDIA Container Toolkit.

```sh
git clone https://github.com/P4suta/mojiokoshi.git
cd mojiokoshi
docker compose -f compose.yaml up --build
```

Open <http://localhost:8000>, upload an audio file, choose a language, and start transcription.
The app downloads the selected Whisper model on first use.

## Documentation

See the [usage and development guide](docs/usage.md) for configuration, model choices, local checks, and troubleshooting.

## License

[MIT](LICENSE).
