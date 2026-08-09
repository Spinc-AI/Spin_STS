# main.py - سرور TTS (بک‌اند: OmniVoice)
import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from typing import Optional

from config import ALLOWED_ORIGINS, HOST, PORT, API_KEY, TEMP_AUDIO_DIR, check_files
from model import TTSManager
from schemas import TTSRequest, ModelInfo

manager = TTSManager()


@asynccontextmanager
async def lifespan(app):
    print("=" * 70)
    print("🎙️  TTS Server (OmniVoice backend)")
    print("=" * 70)
    check_files()

    models = manager.available()
    if models:
        try:
            manager.load(models[0])
            print(f"✅ Auto-loaded model: {models[0]}")
        except Exception as e:
            print(f"❌ Failed to load model: {e}")
    else:
        print("❌ No model configured!")

    print("=" * 70)
    yield


app = FastAPI(
    title="TTS API",
    description="Text-to-Speech API with OmniVoice (Persian voice cloning)",
    version="1.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


def verify_api_key(x_api_key: Optional[str] = Header(default=None)):
    if not API_KEY:
        return
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="کلید API نامعتبر یا وجود ندارد (هدر x-api-key)")


@app.get("/")
async def root():
    return {
        "message": "TTS API Server (OmniVoice)",
        "version": "1.1.0",
        "endpoints": {
            "/": "GET - This info",
            "/health": "GET - Check API health",
            "/synthesize": "POST - Convert text to speech, returns raw audio/wav bytes "
                            "(metadata in X-Duration / X-Latency headers)",
            "/download/{filename}": "GET - Re-download a previously generated audio file",
            "/history": "GET - Get conversion history",
            "/clear_history": "POST - Clear history",
        },
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "model_loaded": manager.loaded is not None,
        "model": manager.loaded,
        "history_count": len(manager.history),
    }


@app.get("/models", response_model=ModelInfo)
async def list_models():
    return ModelInfo(available=manager.available(), loaded=manager.loaded)


@app.post("/synthesize")
async def synthesize(request: TTSRequest, x_api_key: Optional[str] = Header(default=None)):
    """
    تبدیل متن به گفتار.

    برخلاف نسخه‌ی قبلی، این اندپوینت دیگه JSON با آدرس دانلود برنمی‌گردونه؛
    مستقیماً بایت‌های فایل صوتی (audio/wav) رو در بدنه‌ی پاسخ برمی‌گردونه،
    چون Controller دقیقاً همینو انتظار داره (fetch یک‌مرحله‌ای).

    متادیتا (duration/latency) توی هدرهای HTTP برگردونده می‌شه:
      X-Duration: طول صدا به ثانیه
      X-Latency:  زمان تولید به ثانیه

    خطاها هم دیگه با status code واقعی برمی‌گردن (نه 200 + success:false)،
    که یعنی شکست دیگه silent نیست.
    """
    verify_api_key(x_api_key)

    if not request.text or not request.text.strip():
        raise HTTPException(status_code=400, detail="Text is required")

    if manager.loaded is None:
        models = manager.available()
        if models:
            try:
                manager.load(models[0])
            except Exception as e:
                raise HTTPException(status_code=503, detail=f"Model failed to load: {e}")
        else:
            raise HTTPException(status_code=503, detail="No model available.")

    start = time.time()
    try:
        output_path, message = manager.synthesize_text(request.text, speed=request.speed or 1.0)

        if not output_path:
            # خطای منطقی synthesis (مثلاً متن خیلی کوتاه) -> 422، نه 200 با success:false
            raise HTTPException(status_code=422, detail=message)

        duration = manager.get_duration(output_path)
        latency = round(time.time() - start, 2)

        return FileResponse(
            output_path,
            media_type="audio/wav",
            filename=os.path.basename(output_path),
            headers={
                "X-Duration": str(duration),
                "X-Latency": str(latency),
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/download/{filename}")
async def download_file(filename: str):
    """
    دانلود مجدد یک فایل صوتی که قبلاً تولید شده (بر اساس تاریخچه).
    توجه: پاسخ اصلی /synthesize دیگه به این اندپوینت وابسته نیست؛
    این فقط برای دسترسی مجدد به فایل‌های قبلی نگه داشته شده.
    """
    safe_name = os.path.basename(filename)
    file_path = os.path.join(TEMP_AUDIO_DIR, safe_name)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path, media_type="audio/wav", filename=safe_name)


@app.get("/history")
async def get_history(limit: int = 20):
    return {"history": manager.get_history(limit), "total": len(manager.history)}


@app.post("/clear_history")
async def clear_history():
    return manager.clear_history()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host=HOST, port=PORT)