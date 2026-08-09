# model.py - مدیریت مدل TTS (بک‌اند: OmniVoice، بدون دیتاست)
import os
import re
import time
import wave
import tempfile

import config


class TTSManager:
    def __init__(self):
        self.loaded = None
        self.model = None
        self.sample_rate = config.SAMPLE_RATE
        self.history = []
        self._ref_audio_ok = os.path.exists(config.DEFAULT_REF_AUDIO)

    def available(self):
        return [config.MODEL_NAME]

    def load(self, key):
        if self.model is not None and self.loaded == key:
            return self.loaded

        import torch
        from omnivoice import OmniVoice

        dtype = torch.float32 if config.DTYPE == "float32" else torch.float16
        print(f"Loading OmniVoice on {config.DEVICE} (dtype={config.DTYPE})... this may take a while.")
        self.model = OmniVoice.from_pretrained(key, device_map=config.DEVICE, dtype=dtype)
        self.loaded = key
        print(f"Model loaded: {key}")
        return self.loaded

    def synthesize_to_file(self, text, output_path, speed=1.0):
        text = self._remove_emojis(text)
        text = self._clean_text(text)[: config.MAX_TEXT_LENGTH]

        if not text or len(text) < 3:
            return False, "متن وارد شده خیلی کوتاه است"

        if self.model is None:
            return False, "مدل هنوز لود نشده است"

        speed = max(config.MIN_SPEED, min(config.MAX_SPEED, speed or 1.0))

        try:
            import soundfile as sf

            gen_kwargs = dict(text=text, num_step=config.NUM_STEP, speed=speed)
            if self._ref_audio_ok:
                gen_kwargs["ref_audio"] = config.DEFAULT_REF_AUDIO
                if config.DEFAULT_REF_TEXT:
                    gen_kwargs["ref_text"] = config.DEFAULT_REF_TEXT

            audio = self.model.generate(**gen_kwargs)
            sf.write(output_path, audio[0], config.SAMPLE_RATE)

            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                self.history.append(
                    {
                        "text": text,
                        "output": output_path,
                        "duration": self.get_duration(output_path),
                        "timestamp": time.time(),
                    }
                )
                return True, "Success"

            return False, "خروجی صوتی خالی بود"

        except Exception as e:
            return False, str(e)[:300]

    def synthesize_text(self, text, speed=1.0):
        fd, output_path = tempfile.mkstemp(suffix=".wav", dir=config.TEMP_AUDIO_DIR)
        os.close(fd)

        success, message = self.synthesize_to_file(text, output_path, speed=speed)

        if success:
            return output_path, message
        else:
            if os.path.exists(output_path):
                os.remove(output_path)
            return None, message

    def get_duration(self, audio_path):
        try:
            with wave.open(audio_path, "rb") as wav:
                frames = wav.getnframes()
                rate = wav.getframerate()
                return round(frames / rate, 2) if rate > 0 else 0
        except Exception:
            return 0

    def get_history(self, limit=20):
        return self.history[-limit:]

    def clear_history(self):
        self.history = []
        return {"status": "History cleared"}

    def _clean_text(self, text):
        text = re.sub(r"\s+", " ", text).strip()
        text = re.sub(r"[^\w\s\u0600-\u06FF\[\]]", "", text)
        return text

    def _remove_emojis(self, text):
        if not isinstance(text, str):
            return text

        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"
            "\U0001F300-\U0001F5FF"
            "\U0001F680-\U0001F6FF"
            "\U0001F1E0-\U0001F1FF"
            "\U00002500-\U00002BEF"
            "\U00002702-\U000027B0"
            "\U000024C2-\U0001F251"
            "\U0001f926-\U0001f937"
            "\U00010000-\U0010FFFF"
            "\u2640-\u2642"
            "\u2600-\u2B55"
            "\u200d"
            "\u23cf"
            "\u23e9"
            "\u231a"
            "\ufe0f"
            "\u3030"
            "]+",
            flags=re.UNICODE,
        )

        text = emoji_pattern.sub(r"", text)
        text = re.sub(r"[\x00-\x1f\x7f]", "", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text