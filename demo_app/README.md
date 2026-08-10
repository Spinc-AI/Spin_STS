# Demo App

A Tkinter desktop client for the Controller's speech-to-speech pipeline —
one chat window, not a form. Type a message or send audio, pick how you
want the reply, hit send.

## Run
```bash
pip install -r requirements.txt
python app.py          # or: run.bat (Windows) / ./run.sh (Linux)
```
Linux only: tkinter and mic recording need system packages —
`sudo apt install python3-tk libportaudio2`.

If `tkinterdnd2` isn't installed, the app still runs — drag-and-drop is
silently unavailable, but the mic button and 📎 browse button still work.
Same for `sounddevice`/`soundfile` (mic recording and audio playback) — the
app stays usable, you just get an error dialog if you try the mic or play
button specifically.

## Using it

**Sending:**
- Type text and press Enter or ➤
- 🎤 — click to start recording, click again (now ⏹) to stop; the recording
  attaches as a pending voice message (shown in a chip above the input bar)
- 📎 — browse for an audio file instead
- Drag an audio file onto the window from anywhere in the OS

Only one of "typed text" or "attached audio" is sent per message — attaching
audio disables the text box until you clear the attachment (✕ on the chip)
or send it. This matches the Controller's `/converse`, which takes audio OR
text, never both in the same call.

**Reply mode**, top-right: **🔊 Voice** or **💬 Text** — sets `output` on the
`/converse` call. Voice replies autoplay as soon as they arrive; every
audio bubble (yours or the assistant's) also has a ▶ button to replay it.

**All four modes** are reachable from this one chat box, just by choosing
what you send and how you want the reply back:

| You send | Reply mode | = |
|---|---|---|
| audio | 🔊 Voice | speech-to-speech |
| audio | 💬 Text | speech-to-text |
| text | 🔊 Voice | text-to-speech |
| text | 💬 Text | text-to-text |

**Top-left**: Controller URL (defaults to `http://localhost:9000`) + a
connection dot (green/red) + a small `LLM ✓/✗ · TTS ✓/✗` readout, so you can
tell at a glance which backend piece is down if a message fails. Click ⟳ to
recheck after starting the Controller.

**⚙ Settings** (top-right): optional system prompt override, sent as
`system_prompt` on every call. Leave blank to use the Controller's own
default.

## Notes

- Mic recordings are mono 16kHz PCM `.wav`, written to a temp file.
- A voice reply is saved to a temp `.wav` too, for the ▶ replay button —
  temp files aren't cleaned up automatically (fine for a demo tool, not
  meant to run unattended for days).
- Requests use a long timeout (300s) since a cold Core_LLM/TTS call can be
  slow the first time — see `Core_LLM/README.md` / `TTS/README.md`.
