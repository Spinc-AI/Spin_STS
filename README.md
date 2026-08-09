# Spin STS

A speech-to-speech service — but input (audio/text) and output (audio/text)
are independent, so speech-to-text and text-to-text work too, through the
same endpoint. See [`Controller/README.md`](Controller/README.md) for all
four modes.

```
user  <->  Controller (:9000)  <->  Core_LLM (:8001) -- audio-capable Gemma, transcribes + responds
                                <->  TTS (:8002)      -- pending, speaks the reply (only for audio output)
```

Three independent HTTP services, each in its own folder. Reference/pattern
project: `Spin_Medical_Assistant_Project` (its `Core_LLM` and `Orchestrator`
folders) — this project is a deliberately smaller subset: one local model
(no multi-model registry, no external/cloud API routing, no instruction
JSON workflows), matching the simpler single-purpose scope here.

| Folder | Status | Purpose |
|---|---|---|
| [`Core_LLM/`](Core_LLM/README.md) | done | Multimodal LLM (Gemma 4, audio-capable) — `/chat` (text) and `/chat_audio` (audio), both text out |
| [`TTS/`](TTS/README.md) | pending (teammate) | Text in, audio out |
| [`Controller/`](Controller/README.md) | done | Coordinates the two above via `POST /converse` — audio-or-text in, audio-or-text out |

## Run

Each service is standalone — install and run independently (see each
folder's own README for details):
```bash
cd Core_LLM  && pip install -r requirements.txt && ./run.sh   # :8001
cd Controller && pip install -r requirements.txt && ./run.sh  # :9000
```
`TTS/` has no code yet — the Controller is already wired to call it at
`TTS_URL` (default `http://localhost:8002`) per the contract in
`TTS/README.md`. `POST /converse` only calls TTS when `output=audio`, so the
speech-to-text and text-to-text modes work end-to-end today; the two
audio-output modes will 502 on the TTS step until that service exists.
