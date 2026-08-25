"""Spin STS Controller.

Coordinates the two modules over HTTP. Input (audio or text) and output
(audio or text) are independent choices, so all four combinations work
through the same endpoint, POST /converse:

    speech-to-speech -- file in,  output=audio -> Core_LLM/chat_audio -> TTS
    speech-to-text   -- file in,  output=text  -> Core_LLM/chat_audio only
    text-to-speech   -- text in,  output=audio -> Core_LLM/chat      -> TTS
    text-to-text     -- text in,  output=text  -> Core_LLM/chat only

TTS is only ever called when output=audio -- the text-to-text and
speech-to-text modes work today even though TTS/ doesn't exist yet.

An optional "model" field on /converse picks which of Core_LLM's registered
Gemma checkpoints answers the request (see GET /models, proxied straight
from Core_LLM) -- omitted, Core_LLM falls back to its own DEFAULT_MODEL.

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


def llm_models() -> dict:
    with _client() as c:
        r = c.get(f"{config.LLM_URL}/models")
    r.raise_for_status()
    return r.json()


def llm_chat_audio(audio: bytes, filename: str, system_prompt: str, text: str | None,
                    model: str | None = None) -> tuple[str, str]:
    """Send audio to Core_LLM's /chat_audio, get back (model actually used, reply text)."""
    data = {"system_prompt": system_prompt, "text": text or ""}
    if model:
        data["model"] = model
    with _client() as c:
        r = c.post(f"{config.LLM_URL}/chat_audio", files={"file": (filename, audio)}, data=data)
    if r.status_code != 200:
        raise RuntimeError(f"Core_LLM call failed ({r.status_code}): {r.text}")
    body = r.json()
    return body.get("model", model or ""), body["reply"]


def llm_chat_text(text: str, system_prompt: str, model: str | None = None) -> tuple[str, str]:
    """Send text to Core_LLM's plain /chat, get back (model actually used, reply text)."""
    payload = {"messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": text}]}
    if model:
        payload["model"] = model
    with _client() as c:
        r = c.post(f"{config.LLM_URL}/chat", json=payload)
    if r.status_code != 200:
        raise RuntimeError(f"Core_LLM call failed ({r.status_code}): {r.text}")
    body = r.json()
    return body.get("model", model or ""), body["reply"]


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


@app.get("/models")
def models():
    """Proxy Core_LLM's registered model keys (for building a model picker)."""
    try:
        return llm_models()
    except Exception as exc:
        raise HTTPException(502, f"Could not fetch models from Core_LLM: {exc}")


@app.post("/converse")
def converse(
    file: UploadFile | None = File(default=None),
    text: str | None = Form(default=None),
    system_prompt: str | None = Form(default=None),
    model: str | None = Form(default=None),
    output: str = Form(default="audio"),  # "audio" or "text"
):
    """The one entry point for all four modes -- speech-to-speech,
    speech-to-text, text-to-speech, text-to-text. Provide EXACTLY ONE of
    `file` (audio) or `text` as input; `output` picks the reply's shape.
    `model` is a Core_LLM registry key from GET /models; omitted, Core_LLM
    uses its own DEFAULT_MODEL.
    """
    if output not in ("audio", "text"):
        raise HTTPException(400, "output must be 'audio' or 'text'")
    if file is None and not text:
        raise HTTPException(400, "provide either an audio 'file' or 'text'")
    if file is not None and text:
        raise HTTPException(400, "provide only one of 'file' or 'text', not both")

    prompt = system_prompt or config.DEFAULT_SYSTEM_PROMPT

    try:
        if file is not None:
            audio = file.file.read()
            model_used, reply_text = llm_chat_audio(audio, file.filename or "audio.wav", prompt, None, model)
        else:
            model_used, reply_text = llm_chat_text(text, prompt, model)
    except Exception as exc:
        raise HTTPException(502, f"LLM step failed: {exc}")

    if output == "text":
        return {"reply": reply_text, "model": model_used}

    try:
        reply_audio = tts_synthesize(reply_text)
    except Exception as exc:
        raise HTTPException(502, f"TTS step failed: {exc}")

    # Reply text isn't also returned alongside the audio (HTTP headers can't
    # safely carry arbitrary UTF-8, e.g. Persian replies) -- use output=text
    # if you need the text itself instead of guessing from the audio. The
    # model key IS safe in a header (plain ASCII), so that comes back either way.
    return Response(content=reply_audio, media_type="audio/wav", headers={"X-Model": model_used})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("controller:app", host=config.HOST, port=config.PORT)
