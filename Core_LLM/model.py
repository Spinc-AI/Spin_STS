"""Core_LLM's model layer -- served directly via `transformers`, NOT Ollama.

Ollama can't accept audio input at all, so the one model this service
serves -- Gemma 4's lightest audio-capable ("Unified", encoder-free) variant
-- is loaded straight from Hugging Face weights instead.

Just one model, lazy-loaded on first request and kept warm after that (see
LLMManager). No registry/multi-model swapping here -- this project only ever
needs the one audio-capable model, unlike the bigger sibling project this is
based on.
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
        self._model = AutoModelForMultimodalLM.from_pretrained(
            self.model_id, device_map=config.DEVICE_MAP, attn_implementation="sdpa"
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


class LLMManager:
    """Lazy-loads the model on first use and keeps it warm; a lock guards
    loading and generation so concurrent requests can't collide."""

    def __init__(self):
        self._model: GemmaAudioModel | None = None
        self._lock = threading.Lock()

    @property
    def loaded(self) -> bool:
        return self._model is not None

    def _ensure_loaded(self):
        if self._model is None:
            model = GemmaAudioModel(config.GEMMA_MODEL_ID)
            model.load()
            self._model = model

    def chat(self, messages: list[dict], audio: bytes | None = None,
             audio_format: str | None = None, temperature: float = 0.3) -> str:
        with self._lock:
            self._ensure_loaded()
            if audio is None:
                return self._model.chat(messages, temperature=temperature)
            with tempfile.NamedTemporaryFile(suffix=f".{audio_format}") as f:
                f.write(audio)
                f.flush()
                return self._model.chat(messages, audio_path=f.name, temperature=temperature)

    def unload(self):
        with self._lock:
            if self._model is not None:
                self._model.unload()
                self._model = None


MANAGER = LLMManager()
