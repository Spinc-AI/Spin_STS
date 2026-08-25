# Core_LLM Service

Wraps a small set of local multimodal models — all Gemma 4's "Unified"
(encoder-free) audio-capable family, different checkpoints trading size for
quality — behind a small HTTP API. Served directly via `transformers`,
**not Ollama** (Ollama can't accept audio input at all). `model.py` holds
the model wrapper and `LLMManager` (one model loaded at a time, swapped when
a request asks for a different registry key); `main.py` exposes it over
HTTP.

## Run
```bash
pip install -r requirements.txt
./run.sh          # Linux/macOS;  run.bat on Windows
```
Serves on `0.0.0.0:8001` (docs at `/docs`). No model loads at startup — the
first request for a given key downloads it from Hugging Face and loads it
into VRAM (slow the first time, fast after). See `.env.example` to override
any model ID or the default registry key.

## Models

| `model` key | Model | Size | Notes |
|---|---|---|---|
| `gemma-4-e4b` | `google/gemma-4-E4B-it` | ~16GB (BF16) | Best quality of the three |
| `gemma-4-e2b` | `google/gemma-4-E2B-it` | ~10GB (BF16) | Smaller, some quality loss |
| `gemma-4-e2b-qat-mobile` (default) | `google/gemma-4-E2B-it-qat-mobile-transformers` | ~2.5GB (pre-quantized) | Smallest by far — fits alongside `TTS/` on a single 12GB GPU with room to spare; expect a further quality step down from plain E2B |

All three: text **and** audio in, text out. Apache 2.0. Override any model
ID, or the default key (`DEFAULT_MODEL`), via `.env`.

## API
| Method & path | Purpose |
|---|---|
| `GET /` | health + which model (if any) is currently loaded |
| `GET /models` | registered model keys + which one is loaded |
| `POST /chat` | body `{messages, model?, temperature?}` (OpenAI message format) -> `{model, reply}` -- text only, no audio |
| `POST /chat_audio` | multipart: `file` (audio) + `system_prompt` + `text?` + `model?` + `temperature?` -> `{model, reply}` |
| `POST /unload` | unload the currently-loaded model, freeing its VRAM |

`model` is a registry key from `GET /models`; omitted on either endpoint, it
falls back to `DEFAULT_MODEL`. Requesting a different key than what's
currently loaded swaps it — the old one is unloaded first, so only one model
occupies VRAM at a time. An unknown key returns a `404` with the valid list.

## Examples
```bash
curl http://localhost:8001/models

curl -X POST http://localhost:8001/chat -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"system","content":"You are a helpful voice assistant."},{"role":"user","content":"hello"}], "model":"gemma-4-e2b-qat-mobile"}'

curl -X POST http://localhost:8001/chat_audio \
  -F "file=@question.wav" \
  -F "system_prompt=You are a helpful voice assistant. Answer concisely." \
  -F "model=gemma-4-e4b"
```
