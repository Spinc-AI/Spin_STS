# config.py - تنظیمات TTS Server (بک‌اند: OmniVoice)
import os
import torch

# مسیر پایه‌ی پروژه (همون پوشه‌ای که این فایل توشه) - برای مسیرهای پیش‌فرض پرتابل
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ============== تنظیمات مدل OmniVoice ==============
MODEL_NAME = os.environ.get("OMNIVOICE_MODEL", "k2-fsa/OmniVoice")

# اگه CUDA در دسترس باشه به‌صورت خودکار از GPU استفاده می‌شه، در غیر این صورت CPU
DEVICE = os.environ.get("OMNIVOICE_DEVICE", "cuda:0" if torch.cuda.is_available() else "cpu")

# روی GPU از float16 استفاده می‌شه (سریع‌تر و کم‌حجم‌تر)، روی CPU از float32
DTYPE = os.environ.get("OMNIVOICE_DTYPE", "float16" if DEVICE.startswith("cuda") else "float32")

# تعداد استپ‌های تولید صدا - روی GPU نیازی به کم کردن برای سرعت نیست
NUM_STEP = int(os.environ.get("OMNIVOICE_NUM_STEP", 32 if DEVICE.startswith("cuda") else 16))

# ============== صدای پیش‌فرض (voice cloning) ==============
# پیش‌فرض دیگه هاردکد به مسیر یک سیستم خاص نیست - نسبت به پوشه‌ی پروژه‌ست
# فایل ref.wav رو باید خودت توی پوشه‌ی assets/ بذاری (این فایل توی PR/ریپو نیست)
DEFAULT_REF_AUDIO = os.environ.get("OMNIVOICE_REF_AUDIO", os.path.join(BASE_DIR, "assets", "ref.wav"))
DEFAULT_REF_TEXT = os.environ.get("OMNIVOICE_REF_TEXT", "")

# ============== تنظیمات سرور ==============
HOST = "0.0.0.0"
# پیش‌فرض با پورتی که Controller انتظار داره (TTS_URL) هماهنگ شده: 8002
PORT = int(os.environ.get("TTS_PORT", 8002))

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
# پیش‌فرض هم نسبی شد - داخل پوشه‌ی پروژه، نه مسیر هاردکد یک سیستم خاص
TEMP_AUDIO_DIR = os.environ.get("TTS_AUDIO_DIR", os.path.join(BASE_DIR, "tts_audio"))
os.makedirs(TEMP_AUDIO_DIR, exist_ok=True)

# ============== تنظیمات لاگ ==============
LOG_LEVEL = "info"
LOG_FILE = "api.log"


def check_files():
    print("\nChecking configuration...")
    print(f"   Model: {MODEL_NAME}")
    print(f"   Device: {DEVICE} (dtype={DTYPE})")

    if DEVICE.startswith("cuda"):
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            total_vram = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
            print(f"   OK GPU detected: {gpu_name} ({total_vram:.1f} GB VRAM)")
        else:
            print("   WARNING DEVICE is set to cuda but no GPU was detected! Falling back may fail.")

    if os.path.exists(DEFAULT_REF_AUDIO):
        print(f"   OK Reference voice: {DEFAULT_REF_AUDIO}")
    else:
        print(f"   WARNING Reference voice not found at: {DEFAULT_REF_AUDIO}")
        print("      -> server will use auto-voice mode (random voice).")
        print("      -> place a 3-10s wav there (e.g. ./assets/ref.wav), or set OMNIVOICE_REF_AUDIO.")

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