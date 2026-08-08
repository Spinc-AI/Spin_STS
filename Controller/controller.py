"""Spin STS Controller.

Coordinates the two modules over HTTP -- audio in, audio out:

    user  <->  [this FastAPI service]  <->  Core_LLM (audio-capable Gemma)
                                        <->  TTS (pending -- see TTS/README.md)

Flow for POST /speak:
  1. audio -> Core_LLM's /chat_audio (multimodal: no separate STT step)
  2. Core_LLM's text reply -> TTS's /synthesize
  3. TTS's audio -> returned to the caller

Everything talks over HTTP, so either module can be swapped out or rewritten
without touching this file, as long as its API holds.
"""
import httpx
from fastapi import FastAPI, File, Form, HTTPException, Response, UploadFile

import config

app = FastAPI(title="Spin STS Controller")


def _client() -> httpx.Client:
    return httpx.Client(timeout=config.HTTP_TIMEOUT)


# ---------------------------------------------------------------------------
# Module clients -- thin wrappers over each module's HTTP API
# ---------------------------------------------------------------------------
def llm_health() -> bool:
    try:
        with _client() as c:
            return c.get(f"{config.LLM_URL}/").status_code == 200
    except httpx.HTTPError:
        return False


def tts_health() -> bool:
    try:
        with _client() as c:
            return c.get(f"{config.TTS_URL}/").status_code == 200
    except httpx.HTTPError:
        return False


def llm_chat_audio(audio: bytes, filename: str, system_prompt: str, text: str | None) -> str:
    """Send audio to Core_LLM, get back the model's text reply."""
    with _client() as c:
        r = c.post(
            f"{config.LLM_URL}/chat_audio",
            files={"file": (filename, audio)},
            data={"system_prompt": system_prompt, "text": text or ""},
        )
    if r.status_code != 200:
        raise RuntimeError(f"Core_LLM call failed ({r.status_code}): {r.text}")
    return r.json()["reply"]


def tts_synthesize(text: str) -> bytes:
    """Send text to the TTS service, get back audio bytes.

    Matches the contract documented in TTS/README.md (POST /synthesize,
    JSON body {"text": ...} -> audio bytes). Update this if the real TTS
    service, once built, ends up shaped differently.
    """
    with _client() as c:
        r = c.post(f"{config.TTS_URL}/synthesize", json={"text": text})
    if r.status_code != 200:
        raise RuntimeError(f"TTS call failed ({r.status_code}): {r.text}")
    return r.content


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------
@app.get("/health")
def health():
    return {"controller": "ok", "llm": llm_health(), "tts": tts_health()}


@app.post("/speak")
def speak(
    file: UploadFile = File(...),
    system_prompt: str | None = Form(default=None),
    text: str | None = Form(default=None),
):
    """Audio in, audio out: Core_LLM transcribes+responds, TTS speaks the reply."""
    audio = file.file.read()
    prompt = system_prompt or config.DEFAULT_SYSTEM_PROMPT

    try:
        reply_text = llm_chat_audio(audio, file.filename or "audio.wav", prompt, text)
    except Exception as exc:
        raise HTTPException(502, f"LLM step failed: {exc}")

    try:
        reply_audio = tts_synthesize(reply_text)
    except Exception as exc:
        raise HTTPException(502, f"TTS step failed: {exc}")

    # Reply text isn't returned alongside the audio (HTTP headers can't safely
    # carry arbitrary UTF-8, e.g. Persian replies) -- log it if you need it
    # for debugging.
    return Response(content=reply_audio, media_type="audio/wav")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("controller:app", host=config.HOST, port=config.PORT)
