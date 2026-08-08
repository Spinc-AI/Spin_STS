# Controller

Coordinates Core_LLM and TTS over HTTP — audio in, audio out. Talks to the
user and to both modules over their own HTTP APIs; no shared imports, so any
module can be rewritten internally without touching this file, as long as
its API holds.

```
user  <->  Controller  <->  Core_LLM (audio-capable Gemma)
                        <->  TTS (pending -- see TTS/README.md)
```

## Run
```bash
pip install -r requirements.txt
./run.sh          # Linux/macOS;  run.bat on Windows
```
Serves on `0.0.0.0:9000` (docs at `/docs`). Set `LLM_URL`/`TTS_URL` in `.env`
if the modules aren't on their default ports. Both module servers must
already be running/reachable — `POST /speak` will fail with a 502 pointing
at whichever one isn't.

## API
| Method & path | Purpose |
|---|---|
| `GET /health` | controller + Core_LLM + TTS reachability |
| `POST /speak` | multipart: `file` (audio) + optional `system_prompt`/`text` -> audio (`audio/wav`) |

## Example
```bash
curl -X POST http://localhost:9000/speak -F "file=@question.wav" -o reply.wav
```

## Status

Core_LLM is implemented. TTS is **not** — it's owned by another team member
and will be dropped into `../TTS/` once ready; `controller.py`'s
`tts_synthesize()` already calls the contract documented in
`TTS/README.md`, so no changes should be needed here once that lands (unless
the real API ends up shaped differently).
