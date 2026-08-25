# Controller

Coordinates Core_LLM and TTS over HTTP. Talks to the user and to both
modules over their own HTTP APIs; no shared imports, so any module can be
rewritten internally without touching this file, as long as its API holds.

```
user  <->  Controller  <->  Core_LLM (audio-capable Gemma)
                        <->  TTS (OmniVoice)
```

Input (audio or text) and output (audio or text) are independent choices,
all served by one endpoint, `POST /converse`:

| Mode | Input | `output` | Path |
|---|---|---|---|
| Speech-to-speech | `file` | `audio` | Core_LLM `/chat_audio` -> TTS `/synthesize` |
| Speech-to-text | `file` | `text` | Core_LLM `/chat_audio` only |
| Text-to-speech | `text` | `audio` | Core_LLM `/chat` -> TTS `/synthesize` |
| Text-to-text | `text` | `text` | Core_LLM `/chat` only |

TTS is only ever called when `output=audio` — the text-to-text and
speech-to-text modes work even if TTS happens to be down.

An optional `model` field picks which of Core_LLM's registered Gemma
checkpoints answers the request (see `GET /models`, proxied straight from
Core_LLM) — omitted, Core_LLM falls back to its own `DEFAULT_MODEL`.

## Run
```bash
pip install -r requirements.txt
./run.sh          # Linux/macOS;  run.bat on Windows
```
Serves on `0.0.0.0:9000` (docs at `/docs`). Set `LLM_URL`/`TTS_URL` in `.env`
if the modules aren't on their default ports. `POST /converse` needs
Core_LLM reachable always, and TTS reachable only when `output=audio` —
it'll fail with a 502 pointing at whichever module isn't up.

## API
| Method & path | Purpose |
|---|---|
| `GET /health` | controller + Core_LLM + TTS reachability |
| `GET /models` | proxies Core_LLM's registered model keys + which is loaded |
| `POST /converse` | multipart: exactly one of `file` (audio) or `text`, plus optional `system_prompt`, `model`, and `output` (`audio` default, or `text`) -> audio (`audio/wav`, with an `X-Model` header) or JSON `{reply, model}` |

## Examples
```bash
curl http://localhost:9000/models

# speech-to-speech
curl -X POST http://localhost:9000/converse -F "file=@question.wav" -o reply.wav

# speech-to-text (works even if TTS is down)
curl -X POST http://localhost:9000/converse -F "file=@question.wav" -F "output=text"

# text-to-speech, explicit model choice
curl -X POST http://localhost:9000/converse \
  -F "text=What's the weather like?" -F "model=gemma-4-e4b" -o reply.wav

# text-to-text (works even if TTS is down)
curl -X POST http://localhost:9000/converse -F "text=What's the weather like?" -F "output=text"
```

## Status

Core_LLM and TTS are both implemented and merged. `demo_app/` is the
easiest way to exercise all four modes without writing curl commands by
hand.
