# TTS Service (pending)

Not implemented yet — owned by another team member. This folder is a
placeholder so the Controller has something concrete to call once it lands.

## Expected contract

The Controller (`Controller/controller.py`) calls this service the same way
it calls Core_LLM: a small HTTP API, same house style as the rest of this
project (FastAPI, runs standalone, no shared imports).

| Method & path | Purpose |
|---|---|
| `GET /` | health check |
| `POST /synthesize` | body `{"text": "..."}` -> audio bytes (`audio/wav`) |

Suggested port: `8002` (Core_LLM uses `8001`, Controller uses `9000`).

`Controller/config.py` already has a `TTS_URL` setting (default
`http://localhost:8002`) pointed at this contract — once this service exists
and matches it, the Controller needs no changes. If the real implementation
ends up shaped differently (different route, multipart instead of JSON,
extra required fields like a voice/speaker id), update
`Controller/controller.py`'s `tts_synthesize()` to match.
