"""Central configuration, loaded from environment / .env file.

Keeping this in one place means the rest of the code never hard-codes the
server address or model name.
"""
import os

from dotenv import load_dotenv

load_dotenv()  # reads a .env file if present; no-op otherwise

# --- HTTP server (the FastAPI wrapper in main.py) ---
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8001"))
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

# --- Local models — served directly via transformers, NOT Ollama. ---
# Ollama can't accept audio input at all, so these are served the same way
# Core_LLM's audio role is served in the bigger sibling project: via
# AutoModelForMultimodalLM, straight from Hugging Face weights. All three are
# Gemma 4's "Unified" (encoder-free) family -- text AND audio in, text out --
# just different checkpoints trading size for quality; see model.py's
# MODEL_REGISTRY for how these map to the /models API's short keys.
GEMMA_E4B_MODEL_ID = os.getenv("GEMMA_E4B_MODEL_ID", "google/gemma-4-E4B-it")
GEMMA_E2B_MODEL_ID = os.getenv("GEMMA_E2B_MODEL_ID", "google/gemma-4-E2B-it")
# Pre-quantized on disk (mixed 2-bit/int8, QAT-trained) -- ~2.5GB vs ~10GB for
# plain E2B. Loads through the exact same AutoModelForMultimodalLM path, no
# special quantization_config needed; just don't force an explicit dtype that
# would upcast it back to full precision (see GemmaAudioModel.load()).
GEMMA_E2B_QAT_MOBILE_MODEL_ID = os.getenv(
    "GEMMA_E2B_QAT_MOBILE_MODEL_ID", "google/gemma-4-E2B-it-qat-mobile-transformers"
)

# Which registry key /chat and /chat_audio fall back to when a request
# doesn't specify "model" explicitly.
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gemma-4-e2b-qat-mobile")

MAX_NEW_TOKENS = int(os.getenv("MAX_NEW_TOKENS", "2048"))

# transformers' device_map passed to from_pretrained(). "cuda" pins the model
# to a single GPU (no automatic CPU offload); switch to "auto" if the model
# doesn't fit in one GPU's VRAM and offload is actually needed.
DEVICE_MAP = os.getenv("DEVICE_MAP", "cuda")
