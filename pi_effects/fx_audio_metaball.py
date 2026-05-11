"""Audio-reactive Metaball effect.

Idle  : balls orbit smoothly on per-ball sinusoidal paths.
Audio : beat triggers random position jumps; energy boosts speed and radius.
Blend : audio_blend crossfades smoothly between idle and audio modes.
Colour: same-hue palette per beat, gradual crossfade, auto timed switch.

Requires:  pip3 install sounddevice
"""

import numpy as np
import threading

try:
    import sounddevice as sd
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False
    print('[fx_audio_metaball] sounddevice not found — pip3 install sounddevice')


class AudioMetaballEffect:

    N_BALLS = 5

    # --- shape ---
    BASE_RADII         = [0.09, 0.08, 0.08, 0.09, 0.07]
    METABALL_THRESHOLD = 1.0   # lower = more merged, higher = more separate

    # --- idle wander (no music) ---
    # Each ball orbits its own home zone so they stay spread out
    BALL_CENTER = [
        (0.28, 0.28),  # top-left
        (0.72, 0.28),  # top-right
        (0.50, 0.50),  # centre
        (0.28, 0.72),  # bottom-left
        (0.72, 0.72),  # bottom-right
    ]
    BALL_FREQ  = [0.13, 0.17, 0.11, 0.19, 0.15]  # orbit frequency per ball
    BALL_PHASE = [0.00, 1.26, 2.51, 3.77, 5.03]  # phase offset per ball
    IDLE_MARGIN = 0.18   # orbit radius within each home zone
    IDLE_LERP   = 0.04   # chase speed in idle mode

    # --- audio reactive ---
    AUDIO_MIN_ENERGY   = 0.03   # rolling avg below this = treat as silence
    BEAT_THRESHOLD     = 1.8    # instant_bass / rolling_avg to trigger beat
    BEAT_COOLDOWN      = 15     # min frames between beats (~0.5 s at 30 fps)
    BASS_LO            = 60
    BASS_HI            = 300
    AUDIO_LERP_BASE    = 0.06
    AUDIO_LERP_BOOST   = 3.0    # speed = base * (1 + energy * boost)

    # --- mode crossfade ---
    BLEND_RAMP_UP   = 0.05   # idle → audio transition speed
    BLEND_RAMP_DOWN = 0.015  # audio → idle fade-out speed (slower = more natural)

    # --- colour ---
    COLOR_LERP     = 0.04   # colour crossfade speed (lower = slower)
    COLOR_AUTO_SEC = 6.0    # seconds without colour change before auto palette switch
    POS_AUTO_SEC   = 8.0    # seconds without position change before auto nudge
    POS_IDLE_SEC   = 18.0   # seconds stuck with no position change before falling back to idle

    def __init__(self, W, H, cfg):
        self.W   = W
        self.H   = H
        self.cfg = cfg

        rng    = np.random.default_rng(42)
        margin = 0.15
        pos    = rng.uniform(margin, 1 - margin, (self.N_BALLS, 2)).astype(np.float32)

        self.pos    = pos
        self.target = pos.copy()
        self.radii  = np.array(self.BASE_RADII, dtype=np.float32)

        init_colors = np.array([
            [0.0,  0.6,  1.0],
            [1.0,  0.15, 0.5],
            [0.1,  1.0,  0.3],
            [1.0,  0.6,  0.0],
            [0.7,  0.1,  1.0],
        ], dtype=np.float32)
        self.colors       = init_colors.copy()
        self.color_target = init_colors.copy()

        # Grid (computed once)
        x = np.linspace(0, 1, W, dtype=np.float32)
        y = np.linspace(0, 1, H, dtype=np.float32)
        self.xx, self.yy = np.meshgrid(x, y)

        # Beat / energy state
        self._energy_window   = np.zeros(30, dtype=np.float32)
        self._energy_idx      = 0
        self._beat_energy     = 0.0
        self._beat_cooldown   = 0
        self._audio_blend     = 0.0
        self._last_color_time = 0.0
        self._last_pos_time   = 0.0

        # Audio stream
        self._lock     = threading.Lock()
        self._spectrum = np.zeros(cfg.AUDIO_SAMPLE_RATE // 2 + 1, dtype=np.float32)
        self._stream   = None
        if AUDIO_AVAILABLE:
            self._start_stream()

    # ── audio ────────────────────────────────────────────────────────────────

    def _start_stream(self):
        sr = self.cfg.AUDIO_SAMPLE_RATE
        try:
            self._stream = sd.InputStream(
                device    = self.cfg.AUDIO_DEVICE,
                channels  = 1,
                samplerate= sr,
                blocksize = self.cfg.AUDIO_BLOCK_SIZE,
                callback  = self._audio_callback,
            )
            self._stream.start()
            print('[fx_audio_metaball] audio stream started')
        except Exception as e:
            print(f'[fx_audio_metaball] stream error: {e}')

    def _audio_callback(self, indata, frames, time_info, status):
        mono = indata[:, 0] if indata.ndim > 1 else indata.ravel()
        sr   = self.cfg.AUDIO_SAMPLE_RATE
        fft  = np.abs(np.fft.rfft(mono, n=sr)).astype(np.float32)
        with self._lock:
            n = min(len(fft), len(self._spectrum))
            self._spectrum[:n] = fft[:n]

    def _process_audio(self):
        """Return (beat: bool, energy_norm: float 0-1, rolling_avg: float)."""
        with self._lock:
            lo = min(self.BASS_LO, len(self._spectrum) - 1)
            hi = min(self.BASS_HI, len(self._spectrum))
            bass = float(self._spectrum[lo:hi].mean()) if hi > lo else 0.0

        self._energy_window[self._energy_idx] = bass
        self._energy_idx = (self._energy_idx + 1) % 30
        avg = float(self._energy_window.mean()) + 1e-8

        self._beat_energy = self._beat_energy * 0.65 + bass * 0.35

        beat = False
        if bass > avg * self.BEAT_THRESHOLD and self._beat_cooldown <= 0:
            self._beat_cooldown = self.BEAT_COOLDOWN
            beat = True
        self._beat_cooldown = max(0, self._beat_cooldown - 1)

        energy_norm = min(1.0, self._beat_energy / avg)
        return beat, energy_norm, avg

    # ── colour helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _hue_to_rgb(h):
        """Pure saturated colour from hue h (0-1)."""
        h6 = (h % 1.0) * 6.0
        i  = int(h6) % 6
        f  = h6 - int(h6)
        lut = [
            (1.0, f,   0.0),
            (1-f, 1.0, 0.0),
            (0.0, 1.0, f  ),
            (0.0, 1-f, 1.0),
            (f,   0.0, 1.0),
            (1.0, 0.0, 1-f),
        ]
        return np.array(lut[i], dtype=np.float32)

    def _new_palette(self):
        """All balls get colours from the same random hue family."""
        base_hue   = np.random.rand()
        hue_spread = 0.12
        cols = np.empty((self.N_BALLS, 3), dtype=np.float32)
        for i in range(self.N_BALLS):
            offset = np.random.uniform(-hue_spread, hue_spread)
            cols[i] = self._hue_to_rgb(base_hue + offset)
        return cols

    def _new_targets(self):
        return np.random.uniform(0.15, 0.85, (self.N_BALLS, 2)).astype(np.float32)

    # ── rendering ────────────────────────────────────────────────────────────

    def render(self, t: float) -> np.ndarray:
        beat, energy, avg = self._process_audio()

        # Smooth crossfade between idle and audio mode
        # Also fall back to idle if positions have been stuck for too long
        pos_stuck    = (t - self._last_pos_time) > self.POS_IDLE_SEC
        target_blend = 0.0 if (avg <= self.AUDIO_MIN_ENERGY or pos_stuck) else 1.0
        ramp = self.BLEND_RAMP_UP if target_blend > self._audio_blend else self.BLEND_RAMP_DOWN
        self._audio_blend = self._audio_blend * (1.0 - ramp) + target_blend * ramp
        blend = float(self._audio_blend)

        # Idle targets: smooth sinusoidal orbit around each ball's home zone
        idle_target = np.empty((self.N_BALLS, 2), dtype=np.float32)
        for i in range(self.N_BALLS):
            f  = self.BALL_FREQ[i]
            p  = self.BALL_PHASE[i]
            cx, cy = self.BALL_CENTER[i]
            idle_target[i, 0] = cx + self.IDLE_MARGIN * np.sin(t * f * 2 * np.pi + p)
            idle_target[i, 1] = cy + self.IDLE_MARGIN * np.cos(t * f * 2 * np.pi + p * 1.3)

        # Audio targets: beat-triggered random positions
        if beat and blend > 0.3:
            self.target           = self._new_targets()
            self.color_target     = self._new_palette()
            self._last_color_time = t
            self._last_pos_time   = t

        # Auto palette switch if no colour change for COLOR_AUTO_SEC
        if t - self._last_color_time > self.COLOR_AUTO_SEC:
            self.color_target     = self._new_palette()
            self._last_color_time = t

        # Auto nudge positions if stuck for POS_AUTO_SEC (softer than full jump)
        if t - self._last_pos_time > self.POS_AUTO_SEC:
            self.target         = self.pos * 0.4 + self._new_targets() * 0.6
            self._last_pos_time = t

        # Gradually lerp current colours toward target
        self.colors += (self.color_target - self.colors) * self.COLOR_LERP

        # Blend idle and audio targets; blend lerp speed
        blended_target = idle_target * (1.0 - blend) + self.target * blend
        lerp = self.IDLE_LERP + (
            self.AUDIO_LERP_BASE * (1.0 + energy * self.AUDIO_LERP_BOOST) - self.IDLE_LERP
        ) * blend

        energy_eff = energy * blend
        self.pos  += (blended_target - self.pos) * lerp

        # Metaball field + per-ball weights for colour
        xx, yy  = self.xx, self.yy
        field   = np.zeros((self.H, self.W), dtype=np.float32)
        w_ball  = np.zeros((self.N_BALLS, self.H, self.W), dtype=np.float32)

        r_scale = 1.0 + energy_eff * 0.4
        for i in range(self.N_BALLS):
            bx, by = self.pos[i]
            r  = float(self.radii[i]) * r_scale
            d2 = (xx - bx) ** 2 + (yy - by) ** 2 + 1e-8
            w  = (r * r) / d2
            field    += w
            w_ball[i] = w

        # Shape: organic iso-surface + soft glow
        threshold = self.METABALL_THRESHOLD
        interior  = (field > threshold).astype(np.float32)
        glow      = np.exp(-np.abs(field - threshold) * 6.0) * 0.6

        # Colour: dominant ball per pixel — prevents intersection from going white
        dominant = np.argmax(w_ball, axis=0)          # (H, W)
        color    = self.colors[dominant]               # (H, W, 3)

        bfield = (interior + glow).clip(0.0, 1.0)
        bfield = (bfield * (1.0 + energy_eff * 0.3)).clip(0.0, 1.0)

        return (color * bfield[..., np.newaxis] * 255).astype(np.uint8)

    def cleanup(self):
        if self._stream:
            self._stream.stop()
            self._stream.close()
