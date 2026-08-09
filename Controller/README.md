# Controller

Coordinates Core_LLM and TTS over HTTP. Talks to the user and to both
modules over their own HTTP APIs; no shared imports, so any module can be
rewritten internally without touching this file, as long as its API holds.

```
user  <->  Controller  <->  Core_LLM (audio-capable Gemma)
                        <->  TTS (pending -- see TTS/README.md)
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
speech-to-text modes already work today even though `TTS/` has no
implementation yet.

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
| `POST /converse` | multipart: exactly one of `file` (audio) or `text`, plus optional `system_prompt` and `output` (`audio` default, or `text`) -> audio (`audio/wav`) or JSON `{reply}` |

## Examples
```bash
# speech-to-speech
curl -X POST http://localhost:9000/converse -F "file=@question.wav" -o reply.wav

# speech-to-text (no TTS needed -- works today)
curl -X POST http://localhost:9000/converse -F "file=@question.wav" -F "output=text"

# text-to-speech
curl -X POST http://localhost:9000/converse -F "text=What's the weather like?" -o reply.wav

# text-to-text (no TTS needed -- works today)
curl -X POST http://localhost:9000/converse -F "text=What's the weather like?" -F "output=text"
```

## Status

Core_LLM is implemented. TTS is **not** — it's owned by another team member
and will be dropped into `../TTS/` once ready; `controller.py`'s
`tts_synthesize()` already calls the contract documented in
`TTS/README.md`, so no changes should be needed here once that lands (unless
the real API ends up shaped differently). Until then, `output=text` modes
are the only ones you can fully test end-to-end.
