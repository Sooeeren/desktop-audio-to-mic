"""
Audio Engine for Desktop Audio to Discord Microphone
Captures desktop audio via Windows WASAPI Loopback, optionally mixes in physical microphone,
resamples/downmixes signals, and outputs to a virtual audio cable endpoint with real-time VU metering.
"""

import collections
import logging
import threading
import time
import numpy as np
import pyaudiowpatch as pyaudio

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("AudioEngine")


def resample_audio(data: np.ndarray, in_rate: int, out_rate: int) -> np.ndarray:
    """Resample float32 audio data using linear interpolation."""
    try:
        if in_rate == out_rate or len(data) == 0:
            return data
        old_len = len(data)
        new_len = int(round(old_len * out_rate / in_rate))
        if new_len <= 0:
            return np.zeros((0, data.shape[1] if data.ndim > 1 else 1), dtype=np.float32)
        old_idx = np.arange(old_len)
        new_idx = np.linspace(0, old_len - 1, num=new_len)
        if data.ndim == 1:
            return np.interp(new_idx, old_idx, data).astype(np.float32)
        resampled = np.zeros((new_len, data.shape[1]), dtype=np.float32)
        for ch in range(data.shape[1]):
            resampled[:, ch] = np.interp(new_idx, old_idx, data[:, ch])
        return resampled
    except Exception as e:
        logger.error(f"Error in resample_audio: {e}")
        return data


def adjust_channels(data: np.ndarray, in_ch: int, out_ch: int) -> np.ndarray:
    """Adjust channel count to match target channel configuration."""
    try:
        if in_ch == out_ch:
            return data
        if data.ndim == 1:
            data = data.reshape(-1, 1)

        if out_ch == 2:
            if in_ch == 1:
                return np.repeat(data, 2, axis=1)
            elif in_ch == 8:
                # 7.1 surround sound downmix
                fl = data[:, 0]
                fr = data[:, 1]
                fc = data[:, 2] * 0.707
                bl = data[:, 4] * 0.5
                br = data[:, 5] * 0.5
                sl = data[:, 6] * 0.5
                sr = data[:, 7] * 0.5
                left = fl + fc + bl + sl
                right = fr + fc + br + sr
                return np.column_stack((left, right))
            elif in_ch >= 2:
                left = np.mean(data[:, :in_ch // 2], axis=1)
                right = np.mean(data[:, in_ch // 2:], axis=1)
                return np.column_stack((left, right))
            else:
                return np.repeat(data, 2, axis=1)
        elif out_ch == 1:
            return np.mean(data, axis=1, keepdims=True)
        elif out_ch == 8:
            if data.shape[1] == 2:
                return np.repeat(data, 4, axis=1)
            elif data.shape[1] == 1:
                return np.repeat(data, 8, axis=1)

        # Fallback: pad or slice
        if data.shape[1] < out_ch:
            return np.pad(data, ((0, 0), (0, out_ch - data.shape[1])))
        else:
            return data[:, :out_ch]
    except Exception as e:
        logger.error(f"Error in adjust_channels: {e}")
EQ_FREQUENCIES = [60, 150, 400, 1000, 2500, 6000, 15000]


def apply_eq_and_fx(samples: np.ndarray, sample_rate: int, eq_gains: list, troll_mode: bool, troll_bass: float, troll_drive: float) -> np.ndarray:
    """
    Applies 7-band parametric EQ and optional Troll Mode (sub-bass boost + saturation).
    """
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
        self.is_running_flag = False

        # Volume & Mute states (thread-safe)
        self.desktop_volume = 1.0
        self.desktop_muted = False
        self.mic_volume = 1.0
        self.mic_muted = False

        # Meter levels (0.0 to 1.0)
        self.meter_desktop = 0.0
        self.meter_mic = 0.0
        self.meter_out = 0.0
        self.latest_samples = np.zeros(1024, dtype=np.float32)
        self._meter_lock = threading.RLock()

        # Audio streams
        self.lb_stream = None
        self.keepalive_stream = None
        self.mic_stream = None
        self.out_stream = None
        self.headset_stream = None

        # Thread-safe audio queues
        self.desktop_queue = collections.deque(maxlen=40)
        self.mic_queue = collections.deque(maxlen=40)
        self.headset_queue = collections.deque(maxlen=40)
        self._queue_lock = threading.Lock()
        self._headset_lock = threading.Lock()

        # Headset audio monitoring & passthrough
        self.headset_enabled = False
        self.headset_volume = 1.0
        self.headset_device = None
        self.current_out_rate = None
        self.current_out_ch = None

        # DSP Equalizer & Troll Mode FX
        self.eq_bands = [0.0] * 7
        self.troll_mode = False
        self.troll_bass = 28.0
        self.troll_drive = 3.5
        self._fx_lock = threading.Lock()

        self._stream_lock = threading.RLock()

    def is_running(self) -> bool:
        return self.is_running_flag

    def set_desktop_volume(self, vol: float):
        self.desktop_volume = max(0.0, min(2.0, vol))

    def set_desktop_muted(self, muted: bool):
        self.desktop_muted = bool(muted)

    def set_mic_volume(self, vol: float):
        self.mic_volume = max(0.0, min(2.0, vol))

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

    def set_headset_monitor(self, enabled: bool, device: dict = None, volume: float = None):
        """Configures live headset audio monitoring / passthrough."""
        with self._headset_lock:
            self.headset_enabled = bool(enabled)
            if device is not None:
                self.headset_device = device
            if volume is not None:
                self.headset_volume = max(0.0, min(2.0, float(volume)))

            if not self.headset_enabled:
                if self.headset_stream:
                    try:
                        if self.headset_stream.is_active():
                            self.headset_stream.stop_stream()
                        self.headset_stream.close()
                    except Exception:
                        pass
                    self.headset_stream = None
                self.headset_queue.clear()
            elif self.is_running_flag and self.current_out_rate and self.current_out_ch and self.headset_device:
                self._open_headset_stream_internal(self.current_out_rate, self.current_out_ch)

    def set_headset_volume(self, volume: float):
        with self._headset_lock:
            self.headset_volume = max(0.0, min(2.0, float(volume)))

    def _open_headset_stream_internal(self, out_rate: int, out_ch: int):
        with self._headset_lock:
            if not self.is_running_flag or not self.headset_enabled or not self.headset_device:
                return

            if self.headset_stream:
                try:
                    if self.headset_stream.is_active():
                        self.headset_stream.stop_stream()
                    self.headset_stream.close()
                except Exception:
                    pass
                self.headset_stream = None

            try:
                hs_info = self.headset_device.get("device_info", self.headset_device)
                hs_idx = int(hs_info["index"])
                hs_rate = int(hs_info.get("defaultSampleRate", out_rate))
                hs_ch = int(min(2, hs_info.get("maxOutputChannels", 2)))

                def headset_callback(in_data, frame_count, time_info, status):
                    try:
                        if not self.is_running_flag or not self.headset_enabled:
                            return (b'\x00' * (frame_count * hs_ch * 2), pyaudio.paContinue)
                        needed = frame_count
                        frames = []
                        collected = 0
                        with self._headset_lock:
                            while self.headset_queue and collected < needed:
                                c = self.headset_queue.popleft()
                                frames.append(c)
                                collected += len(c)

                        if frames:
                            comb = np.concatenate(frames, axis=0)
                            if comb.ndim == 1:
                                comb = comb.reshape(-1, 1)
                            if len(comb) >= needed:
                                play = comb[:needed]
                                rem = comb[needed:]
                                if len(rem) > 0:
                                    with self._headset_lock:
                                        self.headset_queue.appendleft(rem)
                            else:
                                play = np.pad(comb, ((0, needed - len(comb)), (0, 0)))
                        else:
                            play = np.zeros((needed, out_ch), dtype=np.float32)

                        if out_rate != hs_rate:
                            play = resample_audio(play, out_rate, hs_rate)
                        if play.shape[1] != hs_ch:
                            play = adjust_channels(play, play.shape[1], hs_ch)

                        eff = np.clip(play * self.headset_volume, -1.0, 1.0)
                        out_b = (eff * 32767.0).astype(np.int16).tobytes()
                        return (out_b, pyaudio.paContinue)
                    except Exception as ex:
                        logger.error(f"Error in headset_callback: {ex}")
                        return (b'\x00' * (frame_count * hs_ch * 2), pyaudio.paContinue)

                self.headset_stream = self.p.open(
                    format=pyaudio.paInt16,
                    channels=hs_ch,
                    rate=hs_rate,
                    output=True,
                    output_device_index=hs_idx,
                    stream_callback=headset_callback,
                    frames_per_buffer=1024
                )
                self.headset_stream.start_stream()
                logger.info(f"Headset monitor stream started on {self.headset_device.get('name')} ({hs_rate} Hz, {hs_ch} ch)")
            except Exception as e:
                logger.warning(f"Could not open headset monitor stream: {e}")
                self.headset_stream = None

    def get_meter_levels(self) -> tuple[float, float, float]:
        """Returns instantaneous (desktop, mic, output) audio levels (0.0 - 1.0)."""
        with self._meter_lock:
            d = self.meter_desktop
            m = self.meter_mic
            o = self.meter_out
            self.meter_desktop = max(0.0, self.meter_desktop * 0.85)
            self.meter_mic = max(0.0, self.meter_mic * 0.85)
            self.meter_out = max(0.0, self.meter_out * 0.85)
            return (d, m, o)

    def get_latest_samples(self) -> np.ndarray:
        """Returns a copy of the latest desktop audio samples for visualizer graphing."""
        with self._meter_lock:
            return np.copy(self.latest_samples)

    def start(self, desktop_source: dict, target_mic: dict, real_mic: dict = None, mix_mic: bool = False):
        """
        Starts audio capture and streaming.
        :param desktop_source: dict from DeviceManager.get_desktop_sources()
        :param target_mic: dict from DeviceManager.get_target_microphones()
        :param real_mic: dict from DeviceManager.get_real_microphones() (optional)
        :param mix_mic: bool whether to mix real mic
        """
        with self._stream_lock:
            if self.is_running_flag:
                self.stop()

            logger.info("Initializing audio streaming engine...")
            self.p = pyaudio.PyAudio()

            # Target virtual mic specs
            target_out_info = target_mic["device_info"]
            out_rate = int(target_out_info["defaultSampleRate"])
            # Match target device channels (handles 1, 2, or 8 channels cleanly)
            out_ch = int(target_out_info["maxOutputChannels"])
            out_idx = int(target_out_info["index"])

            # Desktop loopback source specs
            lb_info = desktop_source["loopback_info"]
            in_rate = int(lb_info["defaultSampleRate"])
            in_ch = int(lb_info["maxInputChannels"])
            lb_idx = int(lb_info["index"])

            # Keep-alive speaker specs
            speaker_info = desktop_source["output_info"]
            speaker_idx = int(speaker_info["index"])
            speaker_ch = int(speaker_info["maxOutputChannels"])
            speaker_rate = int(speaker_info["defaultSampleRate"])

            logger.info(f"Target Mic: {target_mic['name']} ({out_rate} Hz, {out_ch} ch)")
            logger.info(f"Desktop Source: {desktop_source['name']} ({in_rate} Hz, {in_ch} ch)")

            self.desktop_queue.clear()
            self.mic_queue.clear()

            # 1. Desktop Loopback Callback (protected with try/except)
            def loopback_callback(in_data, frame_count, time_info, status):
                try:
                    if not self.is_running_flag:
                        return (None, pyaudio.paAbort)
                    if not in_data or len(in_data) == 0:
                        return (None, pyaudio.paContinue)

                    raw = np.frombuffer(in_data, dtype=np.int16).astype(np.float32) / 32768.0
                    if len(raw) % in_ch != 0:
                        return (None, pyaudio.paContinue)
                    raw = raw.reshape(-1, in_ch)

                    # Compute desktop level before volume/mute for visualizer
                    peak = float(np.max(np.abs(raw))) if len(raw) > 0 else 0.0
                    with self._meter_lock:
                        self.meter_desktop = max(self.meter_desktop, min(1.0, peak))
                        if len(raw) > 0:
                            mono = raw[:, 0] if raw.ndim > 1 else raw
                            if len(mono) >= 1024:
                                self.latest_samples = np.copy(mono[:1024])
                            else:
                                self.latest_samples = np.pad(mono, (0, 1024 - len(mono)))

                    # Apply volume / mute
                    eff_vol = 0.0 if self.desktop_muted else self.desktop_volume
                    raw = raw * eff_vol

                    # Resample if needed
                    if in_rate != out_rate:
                        raw = resample_audio(raw, in_rate, out_rate)

                    # Channel adjust
                    if in_ch != out_ch:
                        raw = adjust_channels(raw, in_ch, out_ch)

                    with self._queue_lock:
                        self.desktop_queue.append(raw)
                    return (None, pyaudio.paContinue)
                except Exception as ex:
                    logger.error(f"Error in loopback_callback: {ex}")
                    return (None, pyaudio.paContinue)

            # 2. Keep-alive Callback (silence on source speaker so WASAPI stays active)
            def keepalive_callback(in_data, frame_count, time_info, status):
                try:
                    if not self.is_running_flag:
                        return (None, pyaudio.paAbort)
                    return (b'\x00' * (frame_count * speaker_ch * 2), pyaudio.paContinue)
                except Exception:
                    return (b'', pyaudio.paContinue)

            # 3. Real Mic Callback (if enabled)
            mic_rate = None
            mic_ch = None
            if mix_mic and real_mic:
                real_mic_info = real_mic["device_info"]
                mic_rate = int(real_mic_info["defaultSampleRate"])
                mic_ch = int(real_mic_info["maxInputChannels"])
                mic_idx = int(real_mic_info["index"])
                logger.info(f"Physical Mic: {real_mic['name']} ({mic_rate} Hz, {mic_ch} ch)")

                def mic_callback(in_data, frame_count, time_info, status):
                    try:
                        if not self.is_running_flag:
                            return (None, pyaudio.paAbort)
                        if not in_data or len(in_data) == 0:
                            return (None, pyaudio.paContinue)

                        raw_mic = np.frombuffer(in_data, dtype=np.int16).astype(np.float32) / 32768.0
                        if len(raw_mic) % mic_ch != 0:
                            return (None, pyaudio.paContinue)
                        raw_mic = raw_mic.reshape(-1, mic_ch)

                        peak_m = float(np.max(np.abs(raw_mic))) if len(raw_mic) > 0 else 0.0
                        with self._meter_lock:
                            self.meter_mic = max(self.meter_mic, min(1.0, peak_m))

                        eff_vol = 0.0 if self.mic_muted else self.mic_volume
                        raw_mic = raw_mic * eff_vol

                        if mic_rate != out_rate:
                            raw_mic = resample_audio(raw_mic, mic_rate, out_rate)
                        if mic_ch != out_ch:
                            raw_mic = adjust_channels(raw_mic, mic_ch, out_ch)

                        with self._queue_lock:
                            self.mic_queue.append(raw_mic)
                        return (None, pyaudio.paContinue)
                    except Exception as ex:
                        logger.error(f"Error in mic_callback: {ex}")
                        return (None, pyaudio.paContinue)

            # 4. Target Virtual Mic Output Callback (protected with try/except)
            def output_callback(in_data, frame_count, time_info, status):
                try:
                    if not self.is_running_flag:
                        return (None, pyaudio.paAbort)
                    needed = frame_count

                    # Pull desktop frames
                    desktop_frames = []
                    collected_d = 0
                    with self._queue_lock:
                        while self.desktop_queue and collected_d < needed:
                            chunk = self.desktop_queue.popleft()
                            desktop_frames.append(chunk)
                            collected_d += len(chunk)

                    if desktop_frames:
                        combined_d = np.concatenate(desktop_frames, axis=0)
                        if combined_d.ndim == 1:
                            combined_d = combined_d.reshape(-1, 1)
                        if combined_d.shape[1] != out_ch:
                            combined_d = adjust_channels(combined_d, combined_d.shape[1], out_ch)

                        if len(combined_d) >= needed:
                            d_play = combined_d[:needed]
                            remainder = combined_d[needed:]
                            if len(remainder) > 0:
                                with self._queue_lock:
                                    self.desktop_queue.appendleft(remainder)
                        else:
                            d_play = np.pad(combined_d, ((0, needed - len(combined_d)), (0, 0)))
                    else:
                        d_play = np.zeros((needed, out_ch), dtype=np.float32)

                    # Pull mic frames if enabled
                    if mix_mic and real_mic:
                        mic_frames = []
                        collected_m = 0
                        with self._queue_lock:
                            while self.mic_queue and collected_m < needed:
                                chunk = self.mic_queue.popleft()
                                mic_frames.append(chunk)
                                collected_m += len(chunk)

                        if mic_frames:
                            combined_m = np.concatenate(mic_frames, axis=0)
                            if combined_m.ndim == 1:
                                combined_m = combined_m.reshape(-1, 1)
                            if combined_m.shape[1] != out_ch:
                                combined_m = adjust_channels(combined_m, combined_m.shape[1], out_ch)

                            if len(combined_m) >= needed:
                                m_play = combined_m[:needed]
                                remainder = combined_m[needed:]
                                if len(remainder) > 0:
                                    with self._queue_lock:
                                        self.mic_queue.appendleft(remainder)
                            else:
                                m_play = np.pad(combined_m, ((0, needed - len(combined_m)), (0, 0)))
                        else:
                            m_play = np.zeros((needed, out_ch), dtype=np.float32)

                        to_play = np.clip(d_play + m_play, -1.0, 1.0)
                    else:
                        to_play = np.clip(d_play, -1.0, 1.0)

                    # Apply Equalizer & Troll Mode FX
                    with self._fx_lock:
                        cur_eq = list(self.eq_bands)
                        cur_troll = self.troll_mode
                        cur_bass = self.troll_bass
                        cur_drive = self.troll_drive

                    if any(abs(g) > 0.1 for g in cur_eq) or cur_troll:
                        to_play = apply_eq_and_fx(to_play, out_rate, cur_eq, cur_troll, cur_bass, cur_drive)

                    # Compute output level and store samples for visualizer
                    peak_out = float(np.max(np.abs(to_play))) if len(to_play) > 0 else 0.0
                    with self._meter_lock:
                        self.meter_out = max(self.meter_out, min(1.0, peak_out))
                        mono_vis = np.mean(to_play, axis=1) if to_play.ndim > 1 else to_play
                        if len(mono_vis) >= 1024:
                            self.latest_samples = np.copy(mono_vis[-1024:])
                        elif len(mono_vis) > 0:
                            self.latest_samples = np.pad(mono_vis, (0, 1024 - len(mono_vis)))

                    # If headset monitor is active, push a copy to the headset queue
                    if self.headset_enabled:
                        with self._headset_lock:
                            self.headset_queue.append(np.copy(to_play))

                    out_bytes = (to_play * 32767.0).astype(np.int16).tobytes()
                    return (out_bytes, pyaudio.paContinue)
                except Exception as ex:
                    logger.error(f"Error in output_callback: {ex}")
                    return (b'\x00' * (frame_count * out_ch * 2), pyaudio.paContinue)

            try:
                # Open streams
                self.current_out_rate = out_rate
                self.current_out_ch = out_ch

                self.keepalive_stream = self.p.open(
                    format=pyaudio.paInt16,
                    channels=speaker_ch,
                    rate=speaker_rate,
                    output=True,
                    output_device_index=speaker_idx,
                    stream_callback=keepalive_callback,
                    frames_per_buffer=1024
                )

                self.lb_stream = self.p.open(
                    format=pyaudio.paInt16,
                    channels=in_ch,
                    rate=in_rate,
                    input=True,
                    input_device_index=lb_idx,
                    stream_callback=loopback_callback,
                    frames_per_buffer=1024
                )

                if mix_mic and real_mic:
                    self.mic_stream = self.p.open(
                        format=pyaudio.paInt16,
                        channels=mic_ch,
                        rate=mic_rate,
                        input=True,
                        input_device_index=mic_idx,
                        stream_callback=mic_callback,
                        frames_per_buffer=1024
                    )

                self.out_stream = self.p.open(
                    format=pyaudio.paInt16,
                    channels=out_ch,
                    rate=out_rate,
                    output=True,
                    output_device_index=out_idx,
                    stream_callback=output_callback,
                    frames_per_buffer=1024
                )

                self.is_running_flag = True

                self.keepalive_stream.start_stream()
                self.lb_stream.start_stream()
                if self.mic_stream:
                    self.mic_stream.start_stream()
                self.out_stream.start_stream()

                if self.headset_enabled and self.headset_device:
                    self._open_headset_stream_internal(out_rate, out_ch)

                logger.info("Audio engine successfully started!")
            except Exception as e:
                self.stop()
                logger.error(f"Failed to start audio engine: {e}")
                raise

    def stop(self):
        """Stops all audio streams gracefully."""
        with self._stream_lock:
            self.is_running_flag = False

            for stream in [self.lb_stream, self.keepalive_stream, self.mic_stream, self.out_stream, self.headset_stream]:
                if stream:
                    try:
                        if stream.is_active():
                            stream.stop_stream()
                        stream.close()
                    except Exception as e:
                        logger.warning(f"Error closing stream: {e}")

            self.lb_stream = None
            self.keepalive_stream = None
            self.mic_stream = None
            self.out_stream = None
            self.headset_stream = None
            with self._headset_lock:
                self.headset_queue.clear()

            if self.p:
                try:
                    self.p.terminate()
                except Exception:
                    pass
                self.p = None

            with self._queue_lock:
                self.desktop_queue.clear()
                self.mic_queue.clear()

            with self._meter_lock:
                self.meter_desktop = 0.0
                self.meter_mic = 0.0
                self.meter_out = 0.0
                self.latest_samples = np.zeros(1024, dtype=np.float32)

            logger.info("Audio engine stopped.")
