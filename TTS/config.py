# config.py - تنظیمات TTS Server (بک‌اند: OmniVoice)
import os

# ============== تنظیمات مدل OmniVoice ==============
MODEL_NAME = os.environ.get("OMNIVOICE_MODEL", "k2-fsa/OmniVoice")
DEVICE = "cpu"          # روی سیستم بدون GPU همیشه cpu
DTYPE = "float32"        # float16 روی خیلی از عملگرهای CPU پشتیبانی نمی‌شه/کنده است
NUM_STEP = int(os.environ.get("OMNIVOICE_NUM_STEP", 16))  # کمتر از پیش‌فرض (۳۲) = سریع‌تر روی CPU

# ============== صدای پیش‌فرض (voice cloning) ==============
DEFAULT_REF_AUDIO = os.environ.get("OMNIVOICE_REF_AUDIO", r"C:\Users\lotus\Desktop\omnivoice2\ref.wav")
DEFAULT_REF_TEXT = os.environ.get("OMNIVOICE_REF_TEXT", "")

# ============== تنظیمات سرور ==============
HOST = "0.0.0.0"
PORT = int(os.environ.get("TTS_PORT", 8000))

# ============== تنظیمات CORS ==============
ALLOWED_ORIGINS = ["*"]

# ============== احراز هویت ساده (اختیاری) ==============
API_KEY = os.environ.get("TTS_API_KEY", "")

# ============== تنظیمات TTS ==============
MAX_TEXT_LENGTH = 500
TIMEOUT = 300
SAMPLE_RATE = 24000
MIN_SPEED = 0.5
MAX_SPEED = 2.0

# ============== تنظیمات فایل‌ها ==============
TEMP_AUDIO_DIR = os.environ.get("TTS_AUDIO_DIR", r"C:\temp\tts_audio")
os.makedirs(TEMP_AUDIO_DIR, exist_ok=True)

# ============== تنظیمات لاگ ==============
LOG_LEVEL = "info"
LOG_FILE = "api.log"


def check_files():
    print("\nChecking configuration...")
    print(f"   Model: {MODEL_NAME}")
    print(f"   Device: {DEVICE} (dtype={DTYPE})")

    if os.path.exists(DEFAULT_REF_AUDIO):
        print(f"   OK Reference voice: {DEFAULT_REF_AUDIO}")
    else:
        print(f"   WARNING Reference voice not found at: {DEFAULT_REF_AUDIO}")
        print("      -> server will use auto-voice mode (random voice).")
        print("      -> place a 3-10s wav there, or set OMNIVOICE_REF_AUDIO.")

    if API_KEY:
        print("API key auth: ENABLED")
    else:
        print("API key auth: disabled (open on the network)")

    return True


def get_server_config():
    return {"host": HOST, "port": PORT, "title": "TTS API", "version": "1.0.0"}


def get_tts_config():
    return {
        "max_text_length": MAX_TEXT_LENGTH,
        "timeout": TIMEOUT,
        "sample_rate": SAMPLE_RATE,
    }


def get_cors_origins():
    return ALLOWED_ORIGINS


if __name__ == "__main__":
    print("=" * 70)
    print("Configuration")
    print("=" * 70)
    check_files()
    print("\nConfig loaded successfully!")