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
    """
    نکته: این مدل دیگه توسط /synthesize استفاده نمی‌شه (اون اندپوینت الان
    بایت‌های خام audio/wav برمی‌گردونه، نه JSON). این مدل رو نگه داشتیم
    برای مصرف‌کننده‌های احتمالی دیگه که به فرمت JSON نیاز دارن (مثلاً
    یک اندپوینت جایگزین در آینده)، و برای مستندسازی shape داده‌ی history.
    """
    success: bool
    message: str
    audio_url: Optional[str] = None
    duration: Optional[float] = None
    latency: Optional[float] = None
    text: Optional[str] = None