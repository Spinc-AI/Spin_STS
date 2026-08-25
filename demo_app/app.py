"""Desktop demo client for the Controller's speech-to-speech pipeline.

A single chat-style window, not a form -- type a message or send audio (mic
button, drag-and-drop, or the attach button), pick whether you want the
reply spoken back or shown as text, and hit send. Every combination of
input/output the Controller's POST /converse supports (speech-to-speech,
speech-to-text, text-to-speech, text-to-text) is reachable from the same
chat box, just by choosing what you send and how you want the reply.

Run:  python app.py
(Needs: pip install -r requirements.txt. On Linux, tkinter and mic
recording need system packages: sudo apt install python3-tk libportaudio2)
"""
import os
import queue
import tempfile
import threading
import time
import wave
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

import requests

try:
    import sounddevice as sd
    import soundfile as sf
    AUDIO_ERROR = None
except Exception as exc:  # missing PortAudio / no audio device -- keep the app usable
    sd = None
    sf = None
    AUDIO_ERROR = exc

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    _AppBase = TkinterDnD.Tk
except Exception:
    DND_FILES = None
    _AppBase = tk.Tk

DEFAULT_CONTROLLER_URL = "http://localhost:9000"
TIMEOUT_SHORT = 10
TIMEOUT_LONG = 300  # a cold-start Core_LLM/TTS call can be slow -- see each service's own README
MIC_SAMPLE_RATE = 16000
AUDIO_EXTENSIONS = {".wav", ".mp3", ".flac", ".ogg", ".m4a", ".aac"}
AUDIO_FILETYPES = [("Audio files", "*.wav *.mp3 *.flac *.ogg *.m4a *.aac"), ("All files", "*.*")]
WELCOME_TEXT = ("Hi! Type a message, or send audio with \U0001F3A4 (mic), \U0001F4CE "
                "(browse), or by dropping an audio file onto this window. Choose \U0001F50A "
                "Voice or \U0001F4AC Text for how you want the reply.")


def run_bg(fn, *args, **kwargs):
    """Fire fn(*args, **kwargs) on a background thread so the GUI never freezes."""
    threading.Thread(target=fn, args=args, kwargs=kwargs, daemon=True).start()


def error_detail(exc):
    """Best-effort extraction of a JSON {"detail": ...} body from a requests error."""
    resp = getattr(exc, "response", None)
    if resp is not None:
        try:
            return resp.json().get("detail", str(exc))
        except ValueError:
            pass
    return str(exc)


class MicRecorder:
    """Records mono 16-bit PCM from the default microphone until stopped."""

    def __init__(self, samplerate=MIC_SAMPLE_RATE, channels=1):
        self.samplerate = samplerate
        self.channels = channels
        self._queue = queue.Queue()
        self._stream = None

    def _callback(self, indata, frames, time_info, status):
        self._queue.put(bytes(indata))

    def start(self):
        self._queue = queue.Queue()
        self._stream = sd.RawInputStream(
            samplerate=self.samplerate, channels=self.channels,
            dtype="int16", callback=self._callback,
        )
        self._stream.start()

    def stop_and_save(self):
        """Stop recording and write the captured audio to a temp .wav file. Returns its path."""
        self._stream.stop()
        self._stream.close()
        chunks = []
        while not self._queue.empty():
            chunks.append(self._queue.get())
        path = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
        with wave.open(path, "wb") as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(2)  # int16 -> 2 bytes
            wf.setframerate(self.samplerate)
            wf.writeframes(b"".join(chunks))
        return path


# ---------------------------------------------------------------------------
# Chat bubbles
# ---------------------------------------------------------------------------
class ChatBubble(tk.Frame):
    """One chat message. `style` picks side + color: user (right, blue),
    assistant (left, gray), error (left, red), pending (left, gray italic)."""

    SIDE = {"user": "e", "assistant": "w", "error": "w", "pending": "w"}
    COLORS = {
        "user": ("#DCEEFB", "#0B3D66"),
        "assistant": ("#F1F0F0", "#1C1C1C"),
        "error": ("#FDE2E1", "#7A1F1A"),
        "pending": ("#F1F0F0", "#8A8A8A"),
    }

    def __init__(self, parent, style, text=None, audio_path=None, on_play=None, caption=None):
        bg, fg = self.COLORS[style]
        super().__init__(parent, bg=bg)
        inner = tk.Frame(self, bg=bg, padx=10, pady=6)
        inner.pack()
        font = ("Segoe UI", 10, "italic" if style == "pending" else "normal")

        if audio_path is not None:
            row = tk.Frame(inner, bg=bg)
            row.pack(anchor="w")
            tk.Button(row, text="▶", command=lambda: on_play(audio_path), bg=bg, fg=fg,
                     relief="flat", cursor="hand2", padx=4, font=font).pack(side="left")
            tk.Label(row, text=text or "Voice message", bg=bg, fg=fg, font=font).pack(
                side="left", padx=(4, 0))
        else:
            tk.Label(inner, text=text or "", bg=bg, fg=fg, font=font,
                    wraplength=340, justify="left").pack(anchor="w")

        if caption:  # e.g. which model actually answered -- only set on assistant replies
            tk.Label(inner, text=caption, bg=bg, fg="#9A9A9A", font=("Segoe UI", 7)).pack(
                anchor="w", pady=(2, 0))


class ScrollableChat(ttk.Frame):
    """Vertically scrolling column of ChatBubble widgets, auto-scrolled to
    the bottom on every new message."""

    def __init__(self, parent):
        super().__init__(parent)
        self.canvas = tk.Canvas(self, highlightthickness=0, bg="#FFFFFF")
        vsb = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=vsb.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        self.body = tk.Frame(self.canvas, bg="#FFFFFF")
        self._window = self.canvas.create_window((0, 0), window=self.body, anchor="nw")

        self.body.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(self._window, width=e.width))
        # Only scroll this canvas while the mouse is actually over it -- a global
        # bind_all would hijack scrolling everywhere else in the window too.
        self.canvas.bind("<Enter>", lambda e: self.canvas.bind_all("<MouseWheel>", self._on_mousewheel))
        self.canvas.bind("<Leave>", lambda e: self.canvas.unbind_all("<MouseWheel>"))

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def add_bubble(self, style, text=None, audio_path=None, on_play=None, caption=None):
        bubble = ChatBubble(self.body, style, text=text, audio_path=audio_path, on_play=on_play,
                            caption=caption)
        bubble.pack(anchor=ChatBubble.SIDE[style], pady=4, padx=10)
        self.canvas.update_idletasks()
        self.canvas.yview_moveto(1.0)
        return bubble

    def remove_bubble(self, bubble):
        bubble.destroy()


# ---------------------------------------------------------------------------
# Top bar: connection status + reply mode + settings
# ---------------------------------------------------------------------------
class TopBar(tk.Frame):
    def __init__(self, parent, controller_url_var, on_check, output_mode_var, on_settings):
        super().__init__(parent, bg="#FFFFFF")

        left = tk.Frame(self, bg="#FFFFFF")
        left.pack(side="left", padx=8, pady=6)
        self.indicator = tk.Label(left, text="●", fg="gray", bg="#FFFFFF")
        self.indicator.pack(side="left")
        ttk.Entry(left, textvariable=controller_url_var, width=24).pack(side="left", padx=(4, 4))
        ttk.Button(left, text="⟳", width=3, command=on_check).pack(side="left")
        self.status_sub = tk.Label(left, text="", fg="gray", bg="#FFFFFF", font=("Segoe UI", 8))
        self.status_sub.pack(side="left", padx=(6, 0))

        right = tk.Frame(self, bg="#FFFFFF")
        right.pack(side="right", padx=8, pady=6)
        ttk.Radiobutton(right, text="\U0001F50A Voice", variable=output_mode_var, value="audio").pack(side="left")
        ttk.Radiobutton(right, text="\U0001F4AC Text", variable=output_mode_var, value="text").pack(
            side="left", padx=(4, 8))
        ttk.Button(right, text="⚙", width=3, command=on_settings).pack(side="left")

    def set_status(self, ok, llm_ok=None, tts_ok=None):
        self.indicator.config(fg="green" if ok else "red")
        if ok:
            self.status_sub.config(text=f"LLM {'✓' if llm_ok else '✗'} · "
                                        f"TTS {'✓' if tts_ok else '✗'}")
        else:
            self.status_sub.config(text="unreachable")


DEFAULT_MODEL_LABEL = "(Core_LLM default)"


class SettingsDialog(tk.Toplevel):
    """Model choice (a Core_LLM registry key, via GET /models) + optional
    system prompt override. Controller URL lives in the top bar, not
    duplicated here."""

    def __init__(self, parent, system_prompt_var, model_var, available_models, on_refresh_models):
        super().__init__(parent)
        self.title("Settings")
        self.geometry("420x300")
        self.resizable(False, False)
        self._model_var = model_var

        ttk.Label(self, text="Model:").pack(anchor="w", padx=10, pady=(10, 2))
        row = tk.Frame(self)
        row.pack(anchor="w", padx=10)
        self.model_box = ttk.Combobox(row, width=38, state="readonly",
                                      values=[DEFAULT_MODEL_LABEL] + available_models)
        self.model_box.set(model_var.get() or DEFAULT_MODEL_LABEL)
        self.model_box.pack(side="left")
        ttk.Button(row, text="⟳", width=3,
                  command=lambda: on_refresh_models(self._apply_models)).pack(side="left", padx=(4, 0))

        ttk.Label(self, text="System prompt override (optional):").pack(anchor="w", padx=10, pady=(14, 2))
        text = scrolledtext.ScrolledText(self, width=48, height=5, wrap="word")
        text.pack(padx=10)
        text.insert("1.0", system_prompt_var.get())

        def save():
            chosen = self.model_box.get()
            model_var.set("" if chosen == DEFAULT_MODEL_LABEL else chosen)
            system_prompt_var.set(text.get("1.0", tk.END).strip())
            self.destroy()

        ttk.Button(self, text="Save", command=save).pack(pady=10)

    def _apply_models(self, models):
        current = self.model_box.get()
        self.model_box["values"] = [DEFAULT_MODEL_LABEL] + models
        if current not in self.model_box["values"]:
            self.model_box.set(DEFAULT_MODEL_LABEL)


# ---------------------------------------------------------------------------
# Main app
# ---------------------------------------------------------------------------
class STSChatApp(_AppBase):
    def __init__(self):
        super().__init__()
        self.title("Spin STS — Demo")
        self.geometry("520x760")
        self.configure(bg="#FFFFFF")

        self.controller_url = tk.StringVar(value=DEFAULT_CONTROLLER_URL)
        self.output_mode = tk.StringVar(value="audio")
        self.system_prompt = tk.StringVar(value="")
        self.selected_model = tk.StringVar(value="")  # "" = Core_LLM's own DEFAULT_MODEL
        self._available_models = []
        self._pending_audio_path = None
        self._recorder = None
        self._record_start_time = None

        self.topbar = TopBar(self, self.controller_url, self._check_connection,
                             self.output_mode, self._open_settings)
        self.topbar.pack(fill="x")
        ttk.Separator(self).pack(fill="x")

        self.chat = ScrollableChat(self)
        self.chat.pack(fill="both", expand=True)

        # Attachment preview row -- hidden until a mic recording, browsed file,
        # or dropped file is pending; only ONE pending input at a time (the
        # Controller's /converse takes audio OR text, never both).
        self.attachment_frame = tk.Frame(self, bg="#FFF7E0")
        self.attachment_label = tk.Label(self.attachment_frame, bg="#FFF7E0", anchor="w",
                                         font=("Segoe UI", 9))
        self.attachment_label.pack(side="left", padx=8, pady=4)
        tk.Button(self.attachment_frame, text="✕", command=self._clear_pending_audio,
                 relief="flat", bg="#FFF7E0", cursor="hand2").pack(side="right", padx=8)

        input_row = tk.Frame(self, bg="#FFFFFF")
        input_row.pack(fill="x", padx=8, pady=8)
        btn_bg = "#EFEFEF"
        self.mic_btn = tk.Button(input_row, text="\U0001F3A4", width=3, command=self._toggle_mic,
                                 bg=btn_bg, relief="flat", cursor="hand2")
        self.mic_btn.pack(side="left")
        self.record_timer_label = tk.Label(input_row, text="", fg="#E74C3C", bg="#FFFFFF", width=5)
        self.record_timer_label.pack(side="left")
        tk.Button(input_row, text="\U0001F4CE", width=3, command=self._browse, relief="flat",
                 bg=btn_bg, cursor="hand2").pack(side="left", padx=(4, 4))

        self.entry_var = tk.StringVar()
        self.entry = ttk.Entry(input_row, textvariable=self.entry_var)
        self.entry.pack(side="left", fill="x", expand=True, padx=(0, 4))
        self.entry.bind("<Return>", lambda e: self._send())

        ttk.Button(input_row, text="➤", width=3, command=self._send).pack(side="left")

        if DND_FILES is not None:
            self.drop_target_register(DND_FILES)
            self.dnd_bind("<<Drop>>", self._on_drop)

        self.chat.add_bubble("assistant", text=WELCOME_TEXT)
        self._check_connection()
        self._refresh_models()

    # --- connection status ---
    def _check_connection(self):
        run_bg(self._check_connection_bg)

    def _check_connection_bg(self):
        try:
            r = requests.get(f"{self.controller_url.get().rstrip('/')}/health", timeout=TIMEOUT_SHORT)
            r.raise_for_status()
            data = r.json()
            self.after(0, self.topbar.set_status, True, data.get("llm"), data.get("tts"))
        except requests.RequestException:
            self.after(0, self.topbar.set_status, False)

    # --- model list (Core_LLM registry keys, proxied through Controller's GET /models) ---
    def _refresh_models(self, callback=None):
        run_bg(self._refresh_models_bg, callback)

    def _refresh_models_bg(self, callback):
        try:
            r = requests.get(f"{self.controller_url.get().rstrip('/')}/models", timeout=TIMEOUT_SHORT)
            r.raise_for_status()
            self._available_models = r.json().get("available", [])
        except requests.RequestException:
            self._available_models = []
        if callback:
            self.after(0, callback, self._available_models)

    def _open_settings(self):
        SettingsDialog(self, self.system_prompt, self.selected_model,
                       self._available_models, self._refresh_models)

    # --- pending audio attachment (mic / browse / drop, all share one slot) ---
    def _set_pending_audio(self, path):
        self._pending_audio_path = path
        self.entry_var.set("")
        self.entry.config(state="disabled")
        self.attachment_label.config(text=f"\U0001F3A4 {os.path.basename(path)}")
        self.attachment_frame.pack(fill="x", padx=8, pady=(4, 0), before=self.mic_btn.master)

    def _clear_pending_audio(self):
        self._pending_audio_path = None
        self.entry.config(state="normal")
        self.attachment_frame.pack_forget()

    def _browse(self):
        path = filedialog.askopenfilename(title="Choose an audio file", filetypes=AUDIO_FILETYPES)
        if path:
            self._set_pending_audio(path)

    def _on_drop(self, event):
        paths = self.tk.splitlist(event.data)
        if not paths:
            return
        path = paths[0]
        ext = os.path.splitext(path)[1].lower()
        if ext not in AUDIO_EXTENSIONS:
            messagebox.showwarning("Drop audio", f"Unsupported file type: {ext or 'unknown'}")
            return
        self._set_pending_audio(path)

    # --- mic recording ---
    def _toggle_mic(self):
        if self._recorder is None:
            if sd is None:
                messagebox.showerror("Microphone", f"Microphone unavailable: {AUDIO_ERROR}")
                return
            try:
                self._recorder = MicRecorder()
                self._recorder.start()
            except Exception as exc:
                messagebox.showerror("Microphone", f"Could not start recording: {exc}")
                self._recorder = None
                return
            self.mic_btn.config(text="⏹", bg="#E74C3C", fg="white")
            self._record_start_time = time.time()
            self._update_record_timer()
        else:
            try:
                path = self._recorder.stop_and_save()
                self._set_pending_audio(path)
            except Exception as exc:
                messagebox.showerror("Microphone", f"Could not save recording: {exc}")
            finally:
                self._recorder = None
                self.mic_btn.config(text="\U0001F3A4", bg="#EFEFEF", fg="black")
                self.record_timer_label.config(text="")

    def _update_record_timer(self):
        if self._recorder is None:
            return
        elapsed = int(time.time() - self._record_start_time)
        self.record_timer_label.config(text=f"● {elapsed}s")
        self.after(500, self._update_record_timer)

    # --- playback (assistant replies, and previewing what you're about to send) ---
    def _play(self, path):
        if sd is None or sf is None:
            messagebox.showerror("Playback", f"Audio playback unavailable: {AUDIO_ERROR}")
            return
        run_bg(self._play_bg, path)

    def _play_bg(self, path):
        try:
            data, samplerate = sf.read(path, dtype="float32")
            sd.play(data, samplerate)
            sd.wait()
        except Exception as exc:
            self.after(0, messagebox.showerror, "Playback", f"Could not play audio: {exc}")

    # --- send / receive ---
    def _send(self):
        text = self.entry_var.get().strip()
        audio_path = self._pending_audio_path
        if not text and not audio_path:
            return
        output_mode = self.output_mode.get()

        if audio_path:
            self.chat.add_bubble("user", text=os.path.basename(audio_path),
                                 audio_path=audio_path, on_play=self._play)
        else:
            self.chat.add_bubble("user", text=text)

        self.entry_var.set("")
        self._clear_pending_audio()
        pending = self.chat.add_bubble("pending", text="···")

        run_bg(self._send_bg, text, audio_path, output_mode, pending)

    def _send_bg(self, text, audio_path, output_mode, pending_bubble):
        f = None
        try:
            data = {"output": output_mode}
            files = None
            if audio_path:
                f = open(audio_path, "rb")
                files = {"file": (os.path.basename(audio_path), f)}
            else:
                data["text"] = text
            system_prompt = self.system_prompt.get().strip()
            if system_prompt:
                data["system_prompt"] = system_prompt
            model = self.selected_model.get().strip()
            if model:
                data["model"] = model

            r = requests.post(f"{self.controller_url.get().rstrip('/')}/converse",
                              files=files, data=data, timeout=TIMEOUT_LONG)
            r.raise_for_status()

            if output_mode == "text":
                body = r.json()
                self.after(0, self._on_reply, pending_bubble, "assistant", body.get("reply", ""),
                          None, body.get("model"))
            else:
                path = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
                with open(path, "wb") as out:
                    out.write(r.content)
                self.after(0, self._on_reply, pending_bubble, "assistant", "Voice reply", path,
                          r.headers.get("X-Model"))
        except requests.RequestException as exc:
            self.after(0, self._on_reply, pending_bubble, "error", error_detail(exc), None, None)
        finally:
            if f:
                f.close()

    def _on_reply(self, pending_bubble, style, text, audio_path, model_used=None):
        self.chat.remove_bubble(pending_bubble)
        self.chat.add_bubble(style, text=text, audio_path=audio_path, on_play=self._play,
                             caption=model_used)
        if audio_path:
            self._play(audio_path)


if __name__ == "__main__":
    STSChatApp().mainloop()
