"""Core_LLM's model layer -- served directly via `transformers`, NOT Ollama.

Ollama can't accept audio input at all, so these are loaded straight from
Hugging Face weights instead. All three registered models are Gemma 4's
"Unified" (encoder-free) family -- same architecture, same loading/chat code
(GemmaAudioModel), just different checkpoints trading size for quality --
unlike the bigger sibling project, which juggles genuinely different model
architectures and needs a class per shape.

At most one model is held in memory at a time (LLMManager), swapped when a
request asks for a different registry key than what's currently loaded.
"""
import gc
import tempfile
import threading

import torch
from transformers import AutoModelForMultimodalLM, AutoProcessor

import config


def _generation_kwargs(temperature: float) -> dict:
    """Low temperature (near 0) -> greedy decoding; otherwise sampled."""
    if temperature <= 0.01:
        return {"do_sample": False}
    return {"do_sample": True, "temperature": temperature}


def _last_user_index(messages: list[dict]) -> int:
    for i in range(len(messages) - 1, -1, -1):
        if messages[i]["role"] == "user":
            return i
    raise ValueError("messages must include at least one user turn")


class GemmaAudioModel:
    """Gemma 4's "Unified" (encoder-free) model, via AutoModelForMultimodalLM.
    Text AND audio in, text out."""

    def __init__(self, model_id: str):
        self.model_id = model_id
        self._model = None
        self._processor = None

    def load(self):
        self._processor = AutoProcessor.from_pretrained(self.model_id, padding_side="left")
        # dtype="auto" -- NOT a fixed dtype like torch.bfloat16 -- so a
        # pre-quantized checkpoint (e.g. the qat-mobile entry) loads at its
        # own on-disk precision instead of being upcast back to full size.
        self._model = AutoModelForMultimodalLM.from_pretrained(
            self.model_id, device_map=config.DEVICE_MAP, dtype="auto", attn_implementation="sdpa"
        )

    def chat(self, messages: list[dict], audio_path: str | None = None,
             temperature: float = 0.3) -> str:
        """Return the model's text reply.

        `messages` is the standard OpenAI shape: [{"role": ..., "content": <str>}, ...].
        `audio_path` attaches an audio file to the last user turn.
        """
        last_user = _last_user_index(messages) if audio_path else -1
        converted = []
        for i, m in enumerate(messages):
            if m["role"] == "system":
                converted.append({"role": "system", "content": m["content"]})
                continue
            content = [{"type": "text", "text": m["content"]}]
            if audio_path and i == last_user:
                content.append({"type": "audio", "url": audio_path})
            converted.append({"role": m["role"], "content": content})

        inputs = self._processor.apply_chat_template(
            converted, tokenize=True, add_generation_prompt=True,
            return_dict=True, return_tensors="pt",
        ).to(self._model.device, dtype=self._model.dtype)
        input_len = inputs["input_ids"].shape[-1]
        with torch.no_grad():
            outputs = self._model.generate(**inputs, max_new_tokens=config.MAX_NEW_TOKENS,
                                           **_generation_kwargs(temperature))
        # skip_special_tokens=True so a caller parsing this as plain text (or JSON)
        # doesn't have to strip stray special-token text itself.
        return self._processor.decode(outputs[0][input_len:], skip_special_tokens=True)

    def unload(self):
        self._model = None
        self._processor = None
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()


# ============================================================
# Registry -- short API key -> Hugging Face model id
# ============================================================
MODEL_REGISTRY = {
    "gemma-4-e4b": config.GEMMA_E4B_MODEL_ID,
    "gemma-4-e2b": config.GEMMA_E2B_MODEL_ID,
    "gemma-4-e2b-qat-mobile": config.GEMMA_E2B_QAT_MOBILE_MODEL_ID,
}


class LLMManager:
    """Holds at most one loaded model at a time, swapping when a request
    asks for a different registry key than what's currently loaded. A single
    lock guards both loading and generation so concurrent requests can't
    swap the model out from under an in-flight generation."""

    def __init__(self):
        self._current_key: str | None = None
        self._current_model: GemmaAudioModel | None = None
        self._lock = threading.Lock()

    def available(self) -> list[str]:
        return list(MODEL_REGISTRY.keys())

    @property
    def loaded(self) -> str | None:
        return self._current_key

    def _ensure_loaded(self, key: str):
        if key not in MODEL_REGISTRY:
            raise KeyError(f"unknown model '{key}' -- available: {self.available()}")
        if self._current_key != key:
            if self._current_model is not None:
                self._current_model.unload()
            model = GemmaAudioModel(MODEL_REGISTRY[key])
            model.load()
            self._current_model = model
            self._current_key = key

    def chat(self, key: str, messages: list[dict], audio: bytes | None = None,
             audio_format: str | None = None, temperature: float = 0.3) -> str:
        with self._lock:
            self._ensure_loaded(key)
            if audio is None:
                return self._current_model.chat(messages, temperature=temperature)
            with tempfile.NamedTemporaryFile(suffix=f".{audio_format}") as f:
                f.write(audio)
                f.flush()
                return self._current_model.chat(messages, audio_path=f.name, temperature=temperature)

    def unload(self):
        with self._lock:
            if self._current_model is not None:
                self._current_model.unload()
                self._current_model = None
                self._current_key = None


MANAGER = LLMManager()
