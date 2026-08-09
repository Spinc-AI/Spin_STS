"""HTTP layer for Core_LLM — a thin FastAPI wrapper around model.MANAGER.

The Controller calls this service over HTTP instead of importing Core_LLM
directly. Two routes that matter: /chat_audio -- give the audio-capable
Gemma model the caller's audio directly, no separate STT step -- and /chat,
the plain text-only path (same underlying model, just no audio attached).

Run:
    python main.py            # or: uvicorn main:app --host 0.0.0.0 --port 8001
Interactive docs at http://<host>:8001/docs
"""
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware

import config
from model import MANAGER
from schemas import ChatAudioResponse, ChatRequest, ChatResponse, HealthResponse

app = FastAPI(title="Core LLM Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_model=HealthResponse)
async def health():
    """Liveness check, and whether the model is currently loaded."""
    return HealthResponse(status="ok", model=config.GEMMA_MODEL_ID, loaded=MANAGER.loaded)


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """Text-only chat (no audio) -- same model as /chat_audio."""
    messages = [m.model_dump() for m in req.messages]
    try:
        reply = await run_in_threadpool(MANAGER.chat, messages, temperature=req.temperature)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"LLM error: {exc}")
    return ChatResponse(reply=reply)


@app.post("/chat_audio", response_model=ChatAudioResponse)
async def chat_audio(
    file: UploadFile = File(...),
    system_prompt: str = Form(...),
    text: str | None = Form(default=None),
    temperature: float = Form(default=0.3),
):
    """Multimodal chat: give Gemma the audio directly, no STT step.

    `system_prompt` sets the model's role/instructions. `text` is optional
    extra instructions attached alongside the audio in the same user turn.
    """
    audio_bytes = await file.read()
    audio_format = (file.filename or "").rsplit(".", 1)[-1].lower() or "wav"
    messages = [{"role": "system", "content": system_prompt},
                {"role": "user", "content": text or ""}]
    try:
        reply = await run_in_threadpool(
            MANAGER.chat, messages, audio=audio_bytes, audio_format=audio_format,
            temperature=temperature,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"LLM error: {exc}")
    return ChatAudioResponse(reply=reply)


@app.post("/unload")
async def unload():
    """Unload the model, freeing its VRAM."""
    await run_in_threadpool(MANAGER.unload)
    return {"status": "unloaded", "model": config.GEMMA_MODEL_ID}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host=config.HOST, port=config.PORT)
