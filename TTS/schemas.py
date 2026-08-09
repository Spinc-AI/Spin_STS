# schemas.py - مدل‌های داده TTS (تنها منبع واحد - main.py از همین‌ها استفاده می‌کند)
from pydantic import BaseModel, Field
from typing import List, Optional


class ModelInfo(BaseModel):
    available: List[str]
    loaded: Optional[str] = None


class LoadResponse(BaseModel):
    status: str
    model: str


class TTSRequest(BaseModel):
    text: str
    speed: Optional[float] = Field(default=1.0, description="۱٫۰=عادی، >۱ سریع‌تر، <۱ کندتر")
    language: Optional[str] = "fa"


class TTSResponse(BaseModel):
    success: bool
    message: str
    audio_url: Optional[str] = None
    duration: Optional[float] = None
    latency: Optional[float] = None
    text: Optional[str] = None