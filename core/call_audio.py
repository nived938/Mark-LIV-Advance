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
        self._one_way_active = False
        self._one_way_original_capture = ""
        self._one_way_original_capture_roles = []
        self._one_way_render_device = None
        self._one_way_capture_device_name = ""

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

    @classmethod
    def _find_one_way_loopback(cls):
        """Find a one-way Windows audio route for sending TTS into a call.

        Two families are supported:
        - Hardware/software loopback inputs such as Stereo Mix.
        - A normal two-endpoint VB-CABLE, where we render into "CABLE Input"
          and select "CABLE Output" as the call microphone.
        """
        if os.name != "nt" or sd is None:
            return None

        devices = cls._devices()
        captures = []
        renders = []

        for index, dev in enumerate(devices):
            name = str(dev.get("name", "")).strip()
            low = name.casefold()
            if dev.get("max_input_channels", 0):
                captures.append((index, name, low))
            if dev.get("max_output_channels", 0):
                renders.append((index, name, low))

        # Standard VB-CABLE / equivalent virtual cable.
        cable_capture_terms = (
            "cable output",
            "vb-audio virtual cable b output",
            "vb-audio point output",
        )
        for capture in captures:
            if not any(term in capture[2] for term in cable_capture_terms):
                continue

            paired_render = None
            if "cable output" in capture[2]:
                for render in renders:
                    if "cable input" in render[2]:
                        paired_render = render[:2]
                        break
            elif "virtual cable b output" in capture[2]:
                for render in renders:
                    if "virtual cable b input" in render[2]:
                        paired_render = render[:2]
                        break
            elif "point output" in capture[2]:
                for render in renders:
                    if "point input" in render[2]:
                        paired_render = render[:2]
                        break

            if paired_render:
                return {
                    "capture": capture[:2],
                    "render": paired_render,
                }

        # Hardware loopback devices. The normal Windows output device is fine
        # for these because the loopback device captures the speaker mix.
        loopback_terms = (
            "stereo mix",
            "what u hear",
            "wave out mix",
            "loopback",
            "speaker output",
        )
        for capture in captures:
            if any(term in capture[2] for term in loopback_terms):
                return {
                    "capture": capture[:2],
                    "render": None,
                }

        return None

    def begin_one_way(self) -> tuple[bool, str]:
        """Prepare one-way TTS routing into the Windows communications mic."""
        with self._lock:
            if self._one_way_active:
                return True, "One-way call speech routing is already active."

            if os.name != "nt" or sd is None:
                return False, "One-way call speech routing is available on Windows only."

            route = self._find_one_way_loopback()
            if route is None:
                return False, (
                    "No usable one-way audio route was found. Windows needs either "
                    "Stereo Mix/What U Hear/loopback or a two-endpoint virtual cable "
                    "(for example CABLE Input + CABLE Output)."
                )

            capture_index, capture_name = route["capture"]
            render = route.get("render")
            render_index, render_name = render if render else (None, "")

            try:
                from pycaw.constants import EDataFlow, ERole

                roles = (
                    ERole.eConsole,
                    ERole.eMultimedia,
                    ERole.eCommunications,
                )
                originals = []
                for role in roles:
                    originals.append(
                        (role, self._default_device_id(EDataFlow.eCapture, role))
                    )

                target_id = self._device_id_by_name(capture_name)
                if not target_id:
                    return False, (
                        f"Could not resolve the one-way capture device '{capture_name}' "
                        "through Windows Core Audio."
                    )

                changed = []
                for role, _old_id in originals:
                    if self._set_default(target_id, [role]):
                        changed.append(role)

                if len(changed) != len(roles):
                    # Put every role we changed back immediately.
                    for role, old_id in originals:
                        if old_id:
                            self._set_default(old_id, [role])
                    return False, (
                        f"Could not set '{capture_name}' as the Windows default "
                        "recording device for all audio roles."
                    )

                self._one_way_original_capture_roles = originals
                self._one_way_original_capture = next(
                    (old_id for role, old_id in originals if role == ERole.eCommunications),
                    "",
                )
                self._one_way_render_device = render_index
                self._one_way_capture_device_name = capture_name

                self._one_way_active = True
                self._last_error = ""

                if render_name:
                    return True, (
                        f"One-way call speech routing active: "
                        f"{render_name} → {capture_name}."
                    )
                return True, (
                    f"One-way call speech routing active via {capture_name}."
                )
            except Exception as exc:
                self._one_way_original_capture = ""
                self._one_way_original_capture_roles = []
                self._one_way_render_device = None
                return False, str(exc)

    def stop_one_way(self) -> None:
        with self._lock:
            if not self._one_way_active and not self._one_way_original_capture_roles:
                return

            try:
                from pycaw.constants import ERole
                for role, old_id in self._one_way_original_capture_roles:
                    if old_id:
                        self._set_default(old_id, [role])
            except Exception:
                pass

            self._one_way_original_capture = ""
            self._one_way_original_capture_roles = []
            self._one_way_render_device = None
            self._one_way_capture_device_name = ""
            self._one_way_active = False

    def bind_one_way_to_process(self, process_id: int) -> tuple[bool, str]:
        """Bind a running app's capture endpoint to the one-way call route.

        WhatsApp may have a per-application microphone choice that overrides the
        Windows global communications microphone. Bind the actual native
        WhatsApp process after acceptance, when its audio session exists.
        """
        with self._lock:
            if not self._one_way_active:
                return False, "One-way call speech routing is not active."
            capture_name = str(self._one_way_capture_device_name or "").strip()
        if not capture_name:
            return False, "The one-way capture device is unknown."
        last_error = ""
        for attempt in range(1, 7):
            try:
                import winappaudiorouter as war
                result = war.set_app_input_device(
                    process_id=int(process_id),
                    device=capture_name,
                )
                if not result:
                    # WhatsApp may put the actual media capture session in a
                    # child process. Route every active WhatsApp.exe input
                    # session as a second pass.
                    result = war.set_app_input_device(
                        process_name="WhatsApp.exe",
                        device=capture_name,
                    )
                if result:
                    return True, (
                        f"WhatsApp microphone routed to '{capture_name}' "
                        f"for process {int(process_id)}."
                    )
                last_error = "No active WhatsApp input audio session was exposed yet."
            except Exception as exc:
                last_error = str(exc)

            # WhatsApp may create its recording session asynchronously after
            # the call is accepted. Give the Windows audio service time to expose
            # the session, then retry the exact PID.
            if attempt < 6:
                time.sleep(0.4)

        return False, (
            f"Could not bind the WhatsApp microphone to '{capture_name}' "
            f"for process {int(process_id)}: {last_error}"
        )

    def speak_one_way(self, text: str) -> tuple[bool, str]:
        """Speak through the normal Windows output so Stereo Mix carries it to WhatsApp."""
        text = str(text or "").strip()
        if not text:
            return False, "There is no call message to speak."
        with self._lock:
            if not self._one_way_active:
                return False, "One-way call speech routing is not active."
            if sd is None:
                return False, "sounddevice is not available."
            render_device = self._one_way_render_device

        temp = Path(
            os.environ.get("TEMP", str(Path.home()))
        ) / f"jarvis-one-way-call-{time.time_ns()}.wav"
        try:
            import comtypes.client
            import pythoncom
            pythoncom.CoInitialize()
            try:
                voice = comtypes.client.CreateObject("SAPI.SpVoice")
                stream = comtypes.client.CreateObject("SAPI.SpFileStream")
                stream.Open(str(temp), 3, False)
                old_output = voice.AudioOutputStream
                voice.AudioOutputStream = stream
                try:
                    voice.Speak(text)
                finally:
                    voice.AudioOutputStream = old_output
                    stream.Close()
            finally:
                pythoncom.CoUninitialize()

            with wave.open(str(temp), "rb") as wf:
                channels = wf.getnchannels()
                width = wf.getsampwidth()
                rate = wf.getframerate()
                raw = wf.readframes(wf.getnframes())

            if channels != 1 or width != 2:
                return False, "Windows SAPI returned an unsupported audio format."

            # For a normal VB-CABLE, render directly into CABLE Input so
            # CABLE Output (the communications microphone) receives the TTS.
            # For Stereo Mix/loopback, device=None keeps the normal speaker
            # output and the loopback captures it.
            stream = sd.RawOutputStream(
                samplerate=rate,
                channels=1,
                dtype="int16",
                blocksize=1024,
                device=render_device,
            )
            stream.start()
            try:
                for start in range(0, len(raw), 4800):
                    stream.write(raw[start:start + 4800])
            finally:
                stream.stop()
                stream.close()
            return True, ""
        except Exception as exc:
            return False, str(exc)
        finally:
            try:
                temp.unlink()
            except Exception:
                pass


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
        self.stop_one_way()
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
    def one_way_active(self) -> bool:
        with self._lock:
            return self._one_way_active

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
