"""
Linux Audio Engine using PyAudio with PulseAudio / PipeWire.
Captures desktop loopback from monitor sources, mixes physical microphone,
and streams audio to the virtual Discord microphone sink.
"""

import collections
import logging
import threading
import time
import numpy as np

try:
    import pyaudio
except ImportError:
    pyaudio = None

logger = logging.getLogger("AudioEngineLinux")


class AudioEngine:
    def __init__(self, on_error=None):
        self.on_error = on_error
        self.p = None
        self.in_stream = None
        self.out_stream = None
        self.mic_stream = None

        self.desktop_volume = 1.0
        self.mic_volume = 1.0
        self.desktop_muted = False
        self.mic_muted = False

        self.is_running_flag = False
        self._stream_lock = threading.RLock()
        self._meter_lock = threading.RLock()
        self._queue_lock = threading.Lock()

        # Meter levels (0.0 to 1.0)
        self.desktop_level = 0.0
        self.mic_level = 0.0
        self.out_level = 0.0

        # Ring buffer for live visualizer graph
        self._vis_samples = np.zeros(1024, dtype=np.float32)

        # Worker thread
        self.worker_thread = None
        self.stop_event = threading.Event()

    def set_desktop_volume(self, vol: float):
        self.desktop_volume = max(0.0, min(2.0, vol))

    def set_mic_volume(self, vol: float):
        self.mic_volume = max(0.0, min(2.0, vol))

    def set_desktop_muted(self, muted: bool):
        self.desktop_muted = bool(muted)

    def set_mic_muted(self, muted: bool):
        self.mic_muted = bool(muted)

    def is_running(self) -> bool:
        return self.is_running_flag

    def get_meter_levels(self) -> tuple[float, float, float]:
        with self._meter_lock:
            return (self.desktop_level, self.mic_level, self.out_level)

    def get_latest_samples(self) -> np.ndarray:
        with self._meter_lock:
            return np.copy(self._vis_samples)

    def start(self, desktop_source: dict, target_sink: dict, real_mic: dict = None, mix_mic: bool = False):
        with self._stream_lock:
            if self.is_running_flag:
                self.stop()

            if pyaudio is None:
                raise RuntimeError("PyAudio is not installed. Run: pip install pyaudio")

            logger.info(f"Starting Linux Audio Engine:")
            logger.info(f"  Desktop Source: {desktop_source['name']} (Index {desktop_source['index']})")
            logger.info(f"  Target Sink: {target_sink['name']} (Index {target_sink['index']})")
            if mix_mic and real_mic:
                logger.info(f"  Voice Mic: {real_mic['name']} (Index {real_mic['index']})")

            self.p = pyaudio.PyAudio()

            in_idx = desktop_source["index"]
            in_rate = int(desktop_source["rate"])
            in_ch = max(1, min(2, desktop_source["channels"]))

            out_idx = target_sink["index"]
            out_rate = int(target_sink["rate"])
            out_ch = max(1, min(2, target_sink["channels"]))

            buffer_size = 1024
            desktop_queue = collections.deque(maxlen=16)
            mic_queue = collections.deque(maxlen=16)

            # 1. Desktop Input Stream Callback
            def in_callback(in_data, frame_count, time_info, status):
                try:
                    if not self.is_running_flag:
                        return (None, pyaudio.paAbort)
                    audio = np.frombuffer(in_data, dtype=np.int16).astype(np.float32) / 32768.0
                    audio = audio.reshape(-1, in_ch)

                    # Compute level
                    peak = float(np.max(np.abs(audio))) if len(audio) > 0 else 0.0
                    with self._meter_lock:
                        self.desktop_level = self.desktop_level * 0.7 + peak * 0.3

                    if self.desktop_muted:
                        audio = np.zeros_like(audio)
                    else:
                        audio = audio * self.desktop_volume

                    with self._queue_lock:
                        desktop_queue.append(audio)
                    return (None, pyaudio.paContinue)
                except Exception:
                    return (None, pyaudio.paContinue)

            # 2. Mic Input Stream Callback (if enabled)
            mic_ch = 1
            if mix_mic and real_mic:
                mic_idx = real_mic["index"]
                mic_rate = int(real_mic["rate"])
                mic_ch = max(1, min(2, real_mic["channels"]))

                def mic_callback(in_data, frame_count, time_info, status):
                    try:
                        if not self.is_running_flag:
                            return (None, pyaudio.paAbort)
                        audio = np.frombuffer(in_data, dtype=np.int16).astype(np.float32) / 32768.0
                        audio = audio.reshape(-1, mic_ch)

                        peak = float(np.max(np.abs(audio))) if len(audio) > 0 else 0.0
                        with self._meter_lock:
                            self.mic_level = self.mic_level * 0.7 + peak * 0.3

                        if self.mic_muted:
                            audio = np.zeros_like(audio)
                        else:
                            audio = audio * self.mic_volume

                        with self._queue_lock:
                            mic_queue.append(audio)
                        return (None, pyaudio.paContinue)
                    except Exception:
                        return (None, pyaudio.paContinue)
            else:
                mic_callback = None

            # 3. Target Output Stream Callback
            def out_callback(in_data, frame_count, time_info, status):
                try:
                    if not self.is_running_flag:
                        return (None, pyaudio.paAbort)

                    d_audio = None
                    with self._queue_lock:
                        if desktop_queue:
                            d_audio = desktop_queue.popleft()

                    m_audio = None
                    if mic_callback:
                        with self._queue_lock:
                            if mic_queue:
                                m_audio = mic_queue.popleft()

                    if d_audio is None and m_audio is None:
                        out = np.zeros((frame_count, out_ch), dtype=np.float32)
                    elif d_audio is not None and m_audio is not None:
                        # Ensure equal length and mix
                        min_len = min(len(d_audio), len(m_audio))
                        out = d_audio[:min_len] + m_audio[:min_len]
                        if len(out) < frame_count:
                            out = np.pad(out, ((0, frame_count - len(out)), (0, 0)))
                    elif d_audio is not None:
                        out = d_audio
                        if len(out) < frame_count:
                            out = np.pad(out, ((0, frame_count - len(out)), (0, 0)))
                    else:
                        out = m_audio
                        if len(out) < frame_count:
                            out = np.pad(out, ((0, frame_count - len(out)), (0, 0)))

                    # Ensure output channel count matches
                    if out.shape[1] < out_ch:
                        out = np.repeat(out, out_ch, axis=1)
                    elif out.shape[1] > out_ch:
                        out = out[:, :out_ch]

                    # Clamp to prevent clipping
                    out = np.clip(out, -1.0, 1.0)

                    # Update master output VU & visualizer ring buffer
                    peak = float(np.max(np.abs(out))) if len(out) > 0 else 0.0
                    with self._meter_lock:
                        self.out_level = self.out_level * 0.7 + peak * 0.3
                        if out.ndim > 1:
                            mono = np.mean(out, axis=1)
                        else:
                            mono = out
                        take = min(len(mono), len(self._vis_samples))
                        self._vis_samples = np.roll(self._vis_samples, -take)
                        self._vis_samples[-take:] = mono[:take]

                    out_int16 = (out * 32767.0).astype(np.int16)
                    return (out_int16.tobytes(), pyaudio.paContinue)
                except Exception:
                    silent = np.zeros((frame_count, out_ch), dtype=np.int16)
                    return (silent.tobytes(), pyaudio.paContinue)

            # Open streams
            self.in_stream = self.p.open(
                format=pyaudio.paInt16,
                channels=in_ch,
                rate=in_rate,
                input=True,
                input_device_index=in_idx,
                stream_callback=in_callback,
                frames_per_buffer=buffer_size
            )

            if mic_callback:
                self.mic_stream = self.p.open(
                    format=pyaudio.paInt16,
                    channels=mic_ch,
                    rate=mic_rate,
                    input=True,
                    input_device_index=mic_idx,
                    stream_callback=mic_callback,
                    frames_per_buffer=buffer_size
                )

            self.out_stream = self.p.open(
                format=pyaudio.paInt16,
                channels=out_ch,
                rate=out_rate,
                output=True,
                output_device_index=out_idx,
                stream_callback=out_callback,
                frames_per_buffer=buffer_size
            )

            self.is_running_flag = True
            self.in_stream.start_stream()
            if self.mic_stream:
                self.mic_stream.start_stream()
            self.out_stream.start_stream()
            logger.info("Linux Audio Engine successfully started!")

    def stop(self):
        with self._stream_lock:
            self.is_running_flag = False

            for s in [self.in_stream, self.mic_stream, self.out_stream]:
                if s:
                    try:
                        s.stop_stream()
                        s.close()
                    except Exception:
                        pass

            self.in_stream = None
            self.mic_stream = None
            self.out_stream = None

            if self.p:
                try:
                    self.p.terminate()
                except Exception:
                    pass
                self.p = None

            with self._meter_lock:
                self.desktop_level = 0.0
                self.mic_level = 0.0
                self.out_level = 0.0
                self._vis_samples.fill(0.0)

            logger.info("Linux Audio Engine stopped.")
