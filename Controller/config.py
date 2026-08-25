"""Central configuration, loaded from environment / .env file."""
import os

from dotenv import load_dotenv

load_dotenv()

# Where the module APIs are reachable.
LLM_URL = os.getenv("LLM_URL", "http://localhost:8001").rstrip("/")
TTS_URL = os.getenv("TTS_URL", "http://localhost:8002").rstrip("/")

# This Controller's own address.
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "9000"))

# How long (seconds) to wait on each call to Core_LLM / TTS.
HTTP_TIMEOUT = float(os.getenv("HTTP_TIMEOUT", "120"))

# Default system prompt for Core_LLM, used when a request doesn't supply one.
# The Persian-diacritics instruction below is deliberate and non-standard --
# normal Persian writing omits most short vowels/sukun/tashdid, but this
# reply text feeds straight into TTS, and fully-marked text pronounces
# unambiguously where undiacritized text can be read multiple ways.
DEFAULT_SYSTEM_PROMPT = os.getenv(
    "DEFAULT_SYSTEM_PROMPT",
    "You are a helpful voice assistant. Answer clearly and concisely, in the "
    "same language the user spoke in. If your reply is in Persian/Farsi, "
    "write it with full diacritical marks (اعراب‌گذاری کامل) on every single "
    "word -- include every short vowel (زبر/fatha for \"ah\", زیر/kasra for "
    "\"eh\", پیش/damma for \"oh\"), سکون (sukun), and تشدید (tashdid) "
    "throughout the whole reply, not just where a word would otherwise be "
    "ambiguous.",
)
