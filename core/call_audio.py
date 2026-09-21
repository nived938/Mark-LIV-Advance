"""Two-way Windows call audio bridge.

Uses two virtual stereo/mono cable pairs when available:
- Cable A: JARVIS -> WhatsApp microphone.
- Cable B: WhatsApp speaker -> JARVIS input.

The bridge never claims that call audio is routed unless the required endpoints
are actually present and opened. Windows communications defaults are changed
temporarily so desktop calling apps that follow the Windows communications role
can use the bridge.
"""
from __future__ import annotations

import json
import os
import threading
import time
import wave
from pathlib import Path

import numpy as np

try:
    import sounddevice as sd
except Exception:
    sd = None


class CallAudioRouter:
    def __init__(self):
        self._lock = threading.RLock()
        self._active = False
        self._output_stream = None
        self._caller_stream = None
        self._enqueue = None
        self._loop = None
        self._original_roles = []
        self._last_error = ""
        self._speech_stop = threading.Event()
        self._speech_active = False

    @staticmethod
    def _devices():
        if sd is None:
            return []
        try:
            return list(sd.query_devices())
        except Exception:
            return []

    @classmethod
    def _find(cls, terms, direction):
        terms = tuple(str(x).casefold() for x in terms)
        matches = []
        for index, dev in enumerate(cls._devices()):
            name = str(dev.get("name", ""))
            low = name.casefold()
            channels = (
                dev.get("max_output_channels", 0)
                if direction == "output"
                else dev.get("max_input_channels", 0)
            )
            if channels and any(term in low for term in terms):
                matches.append((index, name))
        return matches

    @classmethod
    def _pick(cls, exact_terms, fallback_terms, direction):
        exact = cls._find(exact_terms, direction)
        if exact:
            return exact[0]
        fallback = cls._find(fallback_terms, direction)
        return fallback[0] if fallback else None

    @classmethod
    def find_cables(cls):
        a_in = cls._pick(
            ("cable-a input", "cable input a"),
            ("cable input",),
            "output",
        )
        a_out = cls._pick(
            ("cable-a output", "cable output a"),
            ("cable output",),
            "input",
        )
        b_out = cls._pick(
            ("cable-b output", "cable output b", "vb-audio virtual cable b output"),
            ("cable output b", "vb-audio virtual cable b output"),
            "input",
        )
        b_in = cls._pick(
            ("cable-b input", "cable input b", "vb-audio virtual cable b input"),
            ("cable input b", "vb-audio virtual cable b input"),
            "output",
        )
        return {
            "jarvis_to_phone": [a_in] if a_in else [],
            "phone_mic": [a_out] if a_out else [],
            "phone_to_jarvis": [b_out] if b_out else [],
            "phone_speaker": [b_in] if b_in else [],
        }

    @classmethod
    def status(cls) -> str:
        cables = cls.find_cables()
        lines = ["Call audio bridge status:"]
        for key, values in cables.items():
            label = {
                "jarvis_to_phone": "JARVIS → phone",
                "phone_mic": "WhatsApp microphone",
                "phone_to_jarvis": "phone → JARVIS",
                "phone_speaker": "WhatsApp speaker",
            }[key]
            lines.append(f"- {label}: " + (", ".join(name for _, name in values) if values else "not found"))
        if not any(cables.values()):
            lines.append(
                "Install VB-CABLE A+B (four virtual endpoints) or configure equivalent "
                "virtual audio routing before using two-way call speech."
            )
        return "\n".join(lines)

    @staticmethod
    def _default_device_id(data_flow, role):
        try:
            from pycaw.pycaw import AudioUtilities
            enum = AudioUtilities.GetDeviceEnumerator()
            dev = enum.GetDefaultAudioEndpoint(data_flow, role)
            return str(dev.GetId())
        except Exception:
            return ""

    @staticmethod
    def _set_default(device_id, roles):
        try:
            from pycaw.pycaw import AudioUtilities
            AudioUtilities.SetDefaultDevice(device_id, roles=roles)
            return True
        except Exception:
            return False

    @staticmethod
    def _device_id_by_name(name):
        try:
            from pycaw.pycaw import AudioUtilities
            for dev in AudioUtilities.GetAllDevices():
                if str(getattr(dev, "FriendlyName", "")).strip() == str(name).strip():
                    return str(dev.id)
        except Exception:
            pass
        return ""

    def _prepare_defaults(self, render_name, capture_name):
        try:
            from pycaw.constants import EDataFlow, ERole
            render_default = self._default_device_id(EDataFlow.eRender, ERole.eCommunications)
            capture_default = self._default_device_id(EDataFlow.eCapture, ERole.eCommunications)
            self._original_roles = [
                ("render", render_default),
                ("capture", capture_default),
            ]
            render_id = self._device_id_by_name(render_name)
            capture_id = self._device_id_by_name(capture_name)
            if not render_id or not capture_id:
                return False, "Could not resolve the virtual cable endpoint IDs through Windows Core Audio."
            ok_render = self._set_default(render_id, [ERole.eCommunications])
            ok_capture = self._set_default(capture_id, [ERole.eCommunications])
            if not (ok_render and ok_capture):
                return False, "Could not set Windows communications audio endpoints."
            return True, ""
        except Exception as exc:
            return False, str(exc)

    def _restore_defaults(self):
        try:
            from pycaw.constants import ERole
            render_id = next((v for k, v in self._original_roles if k == "render"), "")
            capture_id = next((v for k, v in self._original_roles if k == "capture"), "")
            if render_id:
                self._set_default(render_id, [ERole.eCommunications])
            if capture_id:
                self._set_default(capture_id, [ERole.eCommunications])
        except Exception:
            pass
        self._original_roles = []

    def begin(self, loop, enqueue):
        with self._lock:
            if self._active:
                return True, "Call audio bridge is already active."

            if os.name != "nt" or sd is None:
                return False, "Two-way call audio routing is available on Windows only."

            cables = self.find_cables()
            if not all(cables[key] for key in cables):
                return False, self.status()

            jarvis_out_idx, jarvis_out_name = cables["jarvis_to_phone"][0]
            mic_idx, mic_name = cables["phone_mic"][0]
            caller_idx, caller_name = cables["phone_to_jarvis"][0]

            ok, error = self._prepare_defaults(
                cables["phone_speaker"][0][1],
                mic_name,
            )
            if not ok:
                return False, error

            self._loop = loop
            self._enqueue = enqueue

            try:
                self._output_stream = sd.RawOutputStream(
                    samplerate=24000,
                    channels=1,
                    dtype="int16",
                    blocksize=1024,
                    device=jarvis_out_idx,
                )
                self._output_stream.start()

                def callback(indata, frames, _time, status):
                    if status:
                        pass
                    data = np.asarray(indata, dtype=np.int16)
                    if data.ndim > 1:
                        data = data[:, 0]
                    data_bytes = data.tobytes()
                    if self._loop and self._enqueue and data_bytes:
                        try:
                            self._loop.call_soon_threadsafe(
                                self._enqueue,
                                {"data": data_bytes, "mime_type": "audio/pcm"},
                            )
                        except Exception:
                            pass

                self._caller_stream = sd.InputStream(
                    samplerate=16000,
                    channels=1,
                    dtype="int16",
                    blocksize=1024,
                    device=caller_idx,
                    callback=callback,
                )
                self._caller_stream.start()
                self._active = True
                self._last_error = ""
                return True, (
                    f"Two-way call audio active. JARVIS output={jarvis_out_name}; "
                    f"phone capture={caller_name}."
                )
            except Exception as exc:
                self._last_error = str(exc)
                try:
                    if self._output_stream:
                        self._output_stream.stop()
                        self._output_stream.close()
                except Exception:
                    pass
                self._output_stream = None
                try:
                    if self._caller_stream:
                        self._caller_stream.stop()
                        self._caller_stream.close()
                except Exception:
                    pass
                self._caller_stream = None
                self._restore_defaults()
                return False, f"Could not open call audio streams: {exc}"

    def write_jarvis_audio(self, data: bytes):
        with self._lock:
            if not self._active or not self._output_stream:
                return
            try:
                self._output_stream.write(data)
            except Exception as exc:
                self._last_error = str(exc)

    def stop(self):
        with self._lock:
            for stream in (self._caller_stream, self._output_stream):
                try:
                    if stream:
                        stream.stop()
                        stream.close()
                except Exception:
                    pass
            self._caller_stream = None
            self._output_stream = None
            self._restore_defaults()
            self._active = False
            self._enqueue = None
            self._loop = None

    @property
    def active(self):
        with self._lock:
            return self._active

    def stop_speech_to_phone(self) -> None:
        with self._lock:
            self._speech_stop.set()

    @property
    def speech_active(self) -> bool:
        with self._lock:
            return self._speech_active

    def speak_to_phone(self, text: str) -> tuple[bool, str]:
        """Render Windows SAPI speech to a WAV and play it only to Cable A."""
        text = str(text or "").strip()
        if not text:
            return False, "There is no call message to speak."

        if not self.active:
            return False, "The two-way call audio bridge is not active."

        temp = Path(os.environ.get("TEMP", str(Path.home()))) / f"jarvis-call-{time.time_ns()}.wav"
        with self._lock:
            self._speech_stop.clear()
            self._speech_active = True
        try:
            import comtypes.client
            import pythoncom

            pythoncom.CoInitialize()
            try:
                voice = comtypes.client.CreateObject("SAPI.SpVoice")
                stream = comtypes.client.CreateObject("SAPI.SpFileStream")
                stream.Open(str(temp), 3, False)
                old = voice.AudioOutputStream
                voice.AudioOutputStream = stream
                try:
                    voice.Speak(text)
                finally:
                    voice.AudioOutputStream = old
                    stream.Close()
            finally:
                pythoncom.CoUninitialize()

            with wave.open(str(temp), "rb") as wf:
                channels = wf.getnchannels()
                width = wf.getsampwidth()
                rate = wf.getframerate()
                if channels != 1 or width != 2:
                    return False, "Windows SAPI returned an unsupported audio format."

                raw = wf.readframes(wf.getnframes())

            # SAPI commonly produces 22.05/44.1 kHz. sounddevice's shared-mode
            # output endpoint can perform the normal Windows conversion; only
            # the frame format has to remain PCM16 mono.
            with self._lock:
                stream = self._output_stream
                if not stream:
                    return False, "Call output stream is no longer active."
                stopped = self._speech_stop.is_set()
                if stopped:
                    return False, "Speech stopped."
                if rate != 24000:
                    # Open a temporary stream using the exact SAPI rate, then
                    # play it into the cable. This avoids a resampling library.
                    cables = self.find_cables()["jarvis_to_phone"]
                    if not cables:
                        return False, "JARVIS-to-phone virtual cable disappeared."
                    temp_stream = sd.RawOutputStream(
                        samplerate=rate,
                        channels=1,
                        dtype="int16",
                        blocksize=1024,
                        device=cables[0][0],
                    )
                    temp_stream.start()
                    try:
                        for start in range(0, len(raw), 4800):
                            if self._speech_stop.is_set():
                                return False, "Speech stopped."
                            temp_stream.write(raw[start:start + 4800])
                    finally:
                        temp_stream.stop()
                        temp_stream.close()
                else:
                    for start in range(0, len(raw), 4800):
                        if self._speech_stop.is_set():
                            return False, "Speech stopped."
                        stream.write(raw[start:start + 4800])
            if self._speech_stop.is_set():
                return False, "Speech stopped."
            return True, ""
        except Exception as exc:
            return False, str(exc)
        finally:
            with self._lock:
                self._speech_active = False
            try:
                temp.unlink()
            except Exception:
                pass


ROUTER = CallAudioRouter()
