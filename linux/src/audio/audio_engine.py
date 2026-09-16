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
    try:
        import pyaudiowpatch as pyaudio
    except ImportError:
        pyaudio = None

logger = logging.getLogger("AudioEngineLinux")


EQ_FREQUENCIES = [60, 150, 400, 1000, 2500, 6000, 15000]


def apply_eq_and_fx(samples: np.ndarray, sample_rate: int, eq_gains: list, troll_mode: bool, troll_bass: float, troll_drive: float) -> np.ndarray:
    """Applies 7-band parametric EQ and optional Troll Mode."""
    has_eq = any(abs(g) > 0.1 for g in eq_gains)
    if not has_eq and not troll_mode:
        return samples

    n = len(samples)
    if n < 16:
        return samples

    try:
        freqs = np.fft.rfftfreq(n, 1.0 / sample_rate)

        if has_eq:
            log_f = np.log10(np.maximum(freqs, 20.0))
            log_centers = np.log10(EQ_FREQUENCIES)
            gain_db = np.interp(log_f, log_centers, eq_gains)
            gain_linear = 10.0 ** (gain_db / 20.0)
        else:
            gain_linear = np.ones_like(freqs)

        if troll_mode:
            troll_boost = 10.0 ** (troll_bass / 20.0)
            troll_curve = np.where(freqs < 120, troll_boost, np.where(freqs < 280, 1.0 + (troll_boost - 1.0) * (280 - freqs) / 160.0, 1.0))
            gain_linear *= troll_curve

        fft_vals = np.fft.rfft(samples, axis=0)
        fft_vals *= gain_linear[:, None]
        filtered = np.fft.irfft(fft_vals, n=n, axis=0)

        if troll_mode:
            filtered = np.tanh(filtered * troll_drive)
            filtered = np.clip(filtered, -0.98, 0.98)
        else:
            filtered = np.clip(filtered, -1.0, 1.0)

        return filtered.astype(np.float32)
    except Exception as ex:
        logger.error(f"Error in apply_eq_and_fx: {ex}")
        return samples


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

        # DSP Equalizer & Troll Mode FX
        self.eq_bands = [0.0] * 7
        self.troll_mode = False
        self.troll_bass = 28.0
        self.troll_drive = 3.5
        self._fx_lock = threading.Lock()

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

    def set_eq_bands(self, bands: list):
        """Sets 7-band EQ gains in dB (-12.0 to +12.0)."""
        with self._fx_lock:
            self.eq_bands = [float(b) for b in bands[:7]]

    def set_troll_mode(self, enabled: bool, bass: float = 28.0, drive: float = 3.5):
        """Toggles Troll Mode (extreme sub-bass boost & soft-clip overdrive)."""
        with self._fx_lock:
            self.troll_mode = bool(enabled)
            self.troll_bass = float(bass)
            self.troll_drive = float(drive)

    def apply_eq_and_fx(self, samples: np.ndarray, sample_rate: int = 48000) -> np.ndarray:
        """Applies current EQ and Troll Mode FX to an audio chunk."""
        with self._fx_lock:
            cur_eq = list(self.eq_bands)
            cur_troll = self.troll_mode
            cur_bass = self.troll_bass
            cur_drive = self.troll_drive
        return apply_eq_and_fx(samples, sample_rate, cur_eq, cur_troll, cur_bass, cur_drive)

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

                    # Apply Equalizer & Troll Mode FX
                    with self._fx_lock:
                        cur_eq = list(self.eq_bands)
                        cur_troll = self.troll_mode
                        cur_bass = self.troll_bass
                        cur_drive = self.troll_drive

                    if any(abs(g) > 0.1 for g in cur_eq) or cur_troll:
                        out = apply_eq_and_fx(out, out_rate, cur_eq, cur_troll, cur_bass, cur_drive)
                    else:
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
