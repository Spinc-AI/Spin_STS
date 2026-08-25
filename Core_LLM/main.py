"""HTTP layer for Core_LLM — a thin FastAPI wrapper around model.MANAGER.

The Controller calls this service over HTTP instead of importing Core_LLM
directly. Two routes that matter: /chat_audio -- give an audio-capable
Gemma model the caller's audio directly, no separate STT step -- and /chat,
the plain text-only path. Both take an optional "model" registry key (see
GET /models) so the caller picks which Gemma checkpoint runs the request;
only one is ever held in memory at a time, swapped as needed.

Run:
    python main.py            # or: uvicorn main:app --host 0.0.0.0 --port 8001
Interactive docs at http://<host>:8001/docs
"""
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware

import config
from model import MANAGER
from schemas import (
    ChatAudioResponse, ChatRequest, ChatResponse, HealthResponse, ModelsResponse,
)

app = FastAPI(title="Core LLM Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_model=HealthResponse)
async def health():
    """Liveness check, and which model (if any) is currently loaded."""
    return HealthResponse(status="ok", model=MANAGER.loaded)


@app.get("/models", response_model=ModelsResponse)
def list_models():
    """List registered model keys, and which one (if any) is loaded -- call
    this before /chat or /chat_audio to see what's valid for "model"."""
    return ModelsResponse(available=MANAGER.available(), loaded=MANAGER.loaded)


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """Text-only chat (no audio) -- same registry/model choice as /chat_audio."""
    key = req.model or config.DEFAULT_MODEL
    messages = [m.model_dump() for m in req.messages]
    try:
        reply = await run_in_threadpool(MANAGER.chat, key, messages, temperature=req.temperature)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"LLM error: {exc}")
    return ChatResponse(model=key, reply=reply)


@app.post("/chat_audio", response_model=ChatAudioResponse)
async def chat_audio(
    file: UploadFile = File(...),
    system_prompt: str = Form(...),
    text: str | None = Form(default=None),
    model: str | None = Form(default=None),
    temperature: float = Form(default=0.3),
):
    """Multimodal chat: give Gemma the audio directly, no STT step.

    `system_prompt` sets the model's role/instructions. `text` is optional
    extra instructions attached alongside the audio in the same user turn.
    `model` is a registry key from GET /models; omitted, falls back to
    config.DEFAULT_MODEL.
    """
    key = model or config.DEFAULT_MODEL
    audio_bytes = await file.read()
    audio_format = (file.filename or "").rsplit(".", 1)[-1].lower() or "wav"
    messages = [{"role": "system", "content": system_prompt},
                {"role": "user", "content": text or ""}]
    try:
        reply = await run_in_threadpool(
            MANAGER.chat, key, messages, audio=audio_bytes, audio_format=audio_format,
            temperature=temperature,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"LLM error: {exc}")
    return ChatAudioResponse(model=key, reply=reply)


@app.post("/unload")
async def unload():
    """Unload the currently-loaded model, freeing its VRAM."""
    loaded = MANAGER.loaded
    await run_in_threadpool(MANAGER.unload)
    return {"status": "unloaded", "model": loaded}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host=config.HOST, port=config.PORT)
