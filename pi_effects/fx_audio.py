"""Audio reactive spectrum — 16 bars, loopback or microphone input.

Install dependency:  pip3 install sounddevice
"""

import numpy as np
import threading

try:
    import sounddevice as sd
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False
    print('[fx_audio] sounddevice not found — pip3 install sounddevice')


class AudioEffect:
    def __init__(self, W, H, cfg):
        self.W   = W
        self.H   = H
        self.cfg = cfg

        self.N_BARS    = cfg.N_BARS
        self.F_MIN     = cfg.F_MIN
        self.F_MAX     = cfg.F_MAX
        self.BASE_GAIN = cfg.BASE_GAIN
        self.FREQ_EXP  = cfg.FREQ_EXP
        self.ARCTAN_K  = cfg.ARCTAN_K
        self.ATTACK    = cfg.ATTACK
        self.RELEASE   = cfg.RELEASE

        self._lock       = threading.Lock()
        self._spectrum   = np.zeros(cfg.AUDIO_SAMPLE_RATE // 2 + 1)
        self._smooth     = np.zeros(self.N_BARS, dtype=np.float32)
        self._band_lo    = None
        self._band_hi    = None
        self._stream     = None

        if AUDIO_AVAILABLE:
            self._start_stream()

    # ── audio capture ────────────────────────────────────────────────────────

    def _audio_callback(self, indata, frames, time_info, status):
        mono = indata[:, 0] if indata.ndim > 1 else indata.ravel()
        fft  = np.abs(np.fft.rfft(mono, n=self.cfg.AUDIO_SAMPLE_RATE))
        with self._lock:
            self._spectrum[:len(fft)] = fft

    def _start_stream(self):
        try:
            self._stream = sd.InputStream(
                device          = self.cfg.AUDIO_DEVICE,
                channels        = 1,
                samplerate      = self.cfg.AUDIO_SAMPLE_RATE,
                blocksize       = self.cfg.AUDIO_BLOCK_SIZE,
                callback        = self._audio_callback,
            )
            self._stream.start()
            print('[fx_audio] audio stream started')
        except Exception as e:
            print(f'[fx_audio] stream error: {e}')

    # ── rendering ────────────────────────────────────────────────────────────

    def _build_bands(self, n):
        lo = np.zeros(self.N_BARS, dtype=np.int32)
        hi = np.zeros(self.N_BARS, dtype=np.int32)
        for b in range(self.N_BARS):
            f_lo = int(self.F_MIN * (self.F_MAX / self.F_MIN) ** (b / self.N_BARS))
            f_hi = max(f_lo + 1, int(self.F_MIN * (self.F_MAX / self.F_MIN) ** ((b + 1) / self.N_BARS)))
            lo[b] = max(0, min(f_lo, n - 1))
            hi[b] = max(0, min(f_hi, n - 1))
        self._band_lo = lo
        self._band_hi = hi

    def _bar_color(self, b):
        f = b / max(self.N_BARS - 1, 1)
        h = f * 4.5
        if h < 1.0:
            return np.array([1.0, h, 0.0])
        elif h < 2.0:
            return np.array([2.0 - h, 1.0, 0.0])
        elif h < 3.0:
            return np.array([0.0, 1.0, h - 2.0])
        elif h < 4.0:
            return np.array([0.0, 4.0 - h, 1.0])
        else:
            t = (h - 4.0) / 0.5
            return np.array([t * 0.65, 0.0, 1.0])

    def render(self, t: float) -> np.ndarray:
        W, H = self.W, self.H
        arr  = np.zeros((H, W, 3), dtype=np.uint8)
        arr[:, :, :] = 5   # dark background

        with self._lock:
            spec = self._spectrum.copy()

        n = len(spec)
        if self._band_lo is None:
            self._build_bands(n)

        # Per-band amplitude
        raws = np.array([spec[self._band_lo[b]:self._band_hi[b] + 1].max()
                         for b in range(self.N_BARS)], dtype=np.float32)

        gains  = np.array([
            self.BASE_GAIN * ((self.F_MIN * (self.F_MAX / self.F_MIN) ** (b / self.N_BARS)) / self.F_MIN) ** self.FREQ_EXP
            for b in range(self.N_BARS)], dtype=np.float32)

        target = (2.0 / np.pi) * np.arctan(raws * gains * self.ARCTAN_K)

        rising        = target > self._smooth
        self._smooth  = np.where(rising,
                                 self._smooth * (1 - self.ATTACK)  + target * self.ATTACK,
                                 self._smooth * self.RELEASE + target * (1 - self.RELEASE))

        bar_w = W // self.N_BARS
        for b in range(self.N_BARS):
            amp    = float(self._smooth[b])
            bar_px = int(amp * H)
            if bar_px <= 0:
                continue
            x0  = b * bar_w
            x1  = x0 + bar_w
            col = (self._bar_color(b) * 255).clip(0, 255).astype(np.uint8)
            arr[0:bar_px, x0:x1] = col
            arr[bar_px - 1, x0:x1] = np.minimum(255, col * 2)

        return arr

    def cleanup(self):
        if self._stream:
            self._stream.stop()
            self._stream.close()
