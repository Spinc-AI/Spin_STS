# Core_LLM Service

Wraps one local multimodal model — Gemma 4's lightest audio-capable
("Unified", encoder-free) variant — behind a small HTTP API. Served directly
via `transformers`, **not Ollama** (Ollama can't accept audio input at all).
`model.py` holds the model wrapper and `LLMManager` (lazy-loaded on first
request, kept warm after); `main.py` exposes it over HTTP.

## Run
```bash
pip install -r requirements.txt
./run.sh          # Linux/macOS;  run.bat on Windows
```
Serves on `0.0.0.0:8001` (docs at `/docs`). The model doesn't load at
startup — the first request downloads it from Hugging Face and loads it into
VRAM (slow the first time, fast after). See `.env.example` to override the
model ID.

## Model

| Model | Role |
|---|---|
| `google/gemma-4-E4B-it` (default) | Text **and audio** in, text out — Gemma 4's lightest audio-capable variant |

Apache 2.0. Override via `GEMMA_MODEL_ID` in `.env` if a different
audio-capable checkpoint is needed later.

## API
| Method & path | Purpose |
|---|---|
| `GET /` | health + whether the model is currently loaded |
| `POST /chat_audio` | multipart: `file` (audio) + `system_prompt` + `text?` + `temperature?` -> `{reply}` |
| `POST /unload` | unload the model, freeing its VRAM |

## Example
```bash
curl -X POST http://localhost:8001/chat_audio \
  -F "file=@question.wav" \
  -F "system_prompt=You are a helpful voice assistant. Answer concisely." \
  -F "text=Optional extra instructions"
```
