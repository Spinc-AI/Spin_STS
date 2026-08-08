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

# --- Local model — served directly via transformers, NOT Ollama. ---
# Ollama can't accept audio input at all, so this is served the same way
# Core_LLM's audio role is served in the bigger sibling project: via
# AutoModelForMultimodalLM, straight from Hugging Face weights.
# gemma-4-e4b-it is Gemma 4's *lightest* audio-capable ("Unified",
# encoder-free) variant -- text AND audio in, text out.
GEMMA_MODEL_ID = os.getenv("GEMMA_MODEL_ID", "google/gemma-4-E4B-it")

MAX_NEW_TOKENS = int(os.getenv("MAX_NEW_TOKENS", "2048"))

# transformers' device_map passed to from_pretrained(). "cuda" pins the model
# to a single GPU (no automatic CPU offload); switch to "auto" if the model
# doesn't fit in one GPU's VRAM and offload is actually needed.
DEVICE_MAP = os.getenv("DEVICE_MAP", "cuda")
