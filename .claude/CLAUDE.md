# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Project: LED Matrix + TouchDesigner

Drives a **Waveshare P2 64×64 HUB75E LED matrix** via ArtNet from TouchDesigner, running on a **Raspberry Pi Zero 2W** with an **Adafruit RGB Matrix Bonnet**. The TD project generates visuals, previews them in a LED-dot simulator, and streams pixel data over UDP.

---

## Hardware

| Component | Detail |
|-----------|--------|
| LED Panel | Waveshare RGB-Matrix-P2-64×64 (HUB75E, 1/32 scan, 5V/3A ≤15W) |
| Driver board | Adafruit RGB Matrix Bonnet |
| SBC | Raspberry Pi Zero 2W |
| Power | 5V 5A sufficient (panel ≤3A + Pi ≤1A) |

**Critical hardware step**: the Bonnet has a 3-pad solder jumper on its **back side** labelled `16 / E / 8`. Bridge the middle pad to **`8`** to enable the 5th row-address line required by 64-row panels. Without this the display shows two half-height repeated images.

GPIO pins consumed by the Bonnet: 4, 5, 6, 12, 13, 16, 17, 20, 21, 22, 23, 24, 26, 27.  
Free for other use: 2, 3, 7, 8, 9, 10, 11, 14, 15, 19, 25.

---

## Raspberry Pi Setup

Install rpi-rgb-led-matrix:
```bash
sudo apt-get install -y git python3-dev python3-pillow
git clone https://github.com/hzeller/rpi-rgb-led-matrix.git
cd rpi-rgb-led-matrix
make build-python PYTHON=$(which python3)
sudo make install-python PYTHON=$(which python3)
```

Disable audio to avoid PWM conflict — add `dtparam=audio=off` to `/boot/firmware/config.txt`.

Run the ArtNet receiver (`artnet_matrix.py` in this repo root):
```bash
sudo python3 artnet_matrix.py
```

Key parameters in `artnet_matrix.py`:
- `RPI_IP` — set this to the Pi's actual IP before running
- `options.hardware_mapping = 'adafruit-hat'`
- `options.row_address_type = 1` (for E-address / 1/32 scan)
- `options.gpio_slowdown = 4` (Pi Zero 2W)

---

## TouchDesigner Network — `/project1/led_matrix`

### Signal flow

```
fx_noise         ──┐
fx_metaball      ──┤
fx_audio         ──┤  fx_switch → level1 → OUT (64×64)
fx_text          ──┤                           │
fx_audio_metaball──┤              ┌────────────┴────────────┐
fx_ice_metaball  ──┘         viz_led (GLSL)           artnet_sender
                             PREVIEW (640×640)        (executeDAT, every frame)
                             LED dot simulation       → ArtNet UDP to Pi
```

Switch effects by changing `fx_switch.par.input`: `0`=noise, `1`=metaball, `2`=audio, `3`=text, `4`=audio metaball, `5`=ice metaball.

### Effects (baseCOMPs)

| baseCOMP | Key operators inside | Description |
|----------|----------------------|-------------|
| `fx_noise` | `noise1` → `hsv1` → `OUT` | Sparse noise with animated hue cycling |
| `fx_metaball` | `metaballs` (glslTOP) → `OUT` | 5-ball metaball GLSL; time via `vec0valuex = absTime.seconds` |
| `fx_audio` | `audio_in` → `spectrum1` → `audio_viz` → `OUT` | 32-band spectrum analyser (scriptTOP) |
| `fx_text` | `txt` (textTOP 512×64) → `scroller` (scriptTOP) → `colorize` → `OUT` | Scrolling marquee, right-to-left loop |
| `fx_audio_metaball` | `amb_trigger` → `amb_viz` → `out1` | Beat-reactive metaball (scriptTOP); reads `fx_audio/spectrum1` |
| `fx_ice_metaball` | same structure as fx_audio_metaball | Same beat behaviour, fixed single-hue ice-blue palette (no colour changes) |

### Audio reactive chain (inside `fx_audio`)

```
audio_in (audiodeviceinCHOP, device = CABLE Output VB-Audio)
    → spectrum1 (audiospectrumCHOP, fftsize=16384, frequencylog=0)
    → audio_viz (scriptTOP 64×64)
    → OUT
```

- `cook_trigger` — 1×1 noiseTOP (`tz = absTime.seconds`) connected as dummy input to force every-frame cooking.
- Active callbacks DAT: **`audio_viz_callbacks1`** (renamed after copy — `callbacks` par points to it explicitly).
- Hardcode `W = 64; H = 64` in callbacks — do NOT use `scriptOp.width` (may return stale cached size).

### Audio Metaball chain (inside `fx_audio_metaball`)

```
amb_trigger (1×1 noiseTOP, tz=absTime.seconds) → amb_viz (scriptTOP 64×64) → out1
                                                  ↑
                                     reads fx_audio/spectrum1 by path
                                     (no separate audio_in — reuses fx_audio's capture)
```

- Callbacks DAT: **`amb_callbacks`** — contains all beat detection + rendering logic.
- `op()` inside callbacks is relative to `amb_viz`; use `scriptOp.parent().parent().op('fx_audio/spectrum1')` to reach the spectrum CHOP.
- State (ball positions, colors, energy window) stored in module-level `_S` dict — avoids `scriptOp.store()` which causes cook dependency loops.
- Two modes blended via `audio_blend` (0=idle, 1=audio): idle = sinusoidal orbits per ball; audio = beat-triggered random jumps.

### Text effect chain (inside `fx_text`)

```
txt (textTOP 512×64) → scroller (scriptTOP 64×64) → colorize (hsvadjustTOP) → OUT
text_trigger (1×1 noiseTOP) → scroller  ← forces every-frame cooking
```

- Change text: `txt.par.text` — double-click `fx_text` → `txt` → Text parameter.
- Chinese text: set `txt.par.font = 'Microsoft YaHei'` first.
- Scroll speed: `SPEED` in `scroller_callbacks` (pixels/frame; 0.5 = 30 px/s).
- Loop timing: auto-detected from actual text pixel extent — no manual adjustment needed.
- Color animation: `colorize.par.hueoffset.expr = 'absTime.seconds * 40 % 360'` — text must be a saturated color (e.g. pure red), not white (white has no saturation, hue rotation has no effect).

### LED preview

`OUT → viz_led (glslTOP 640×640) → PREVIEW`

The `viz_led` GLSL shader (`viz_led_pixel` textDAT) renders each 64×64 pixel as a glowing circular LED dot on a dark PCB background. The shader declares no uniforms — `sTD2DInputs` is auto-provided by TD.

### ArtNet sender

`artnet_sender` (executeDAT, `frameStart` enabled) reads `OUT.numpyArray()` every frame and sends 24 ArtNet universe packets (512 bytes each, 64×64×3 = 12,288 bytes total) to the Pi.

**Change the Pi IP** in `artnet_sender` DAT: `ARTNET_IP = '192.168.x.x'`

---

## Key Gotchas

### scriptTOP doesn't cook without a changing input
TD caches scriptTOP output if no inputs changed. Always connect a time-varying 1×1 noiseTOP (`tz = absTime.seconds`) as a dummy input.

### After COMP.copy(), verify the callbacks parameter
When copying a scriptTOP into a baseCOMP, TD renames docked DATs if a name collision exists (`callbacks` → `callbacks1`). The `callbacks` parameter is left empty — code never runs. Always check:
```python
print([d.name for d in script_top.docked])
print(script_top.par.callbacks.val)
```
Fix with: `script_top.par.callbacks = 'actual_dat_name'`.

### Hardcode W/H in scriptTOP callbacks
`scriptOp.width` can return a stale cached value from the previous cook. Always hardcode `W = 64; H = 64` inside `onCook` rather than reading from `scriptOp`.

### audiospectrumCHOP frequency indexing
With `frequencylog=0` (linear output): sample index `k ≈ k Hz` — use `idx = int(freq_hz)` directly. With `frequencylog=1` the samples are log-distributed and this formula is wrong.

### numpy Y-axis in scriptTOP (OpenGL convention)
In `copyNumpyArray`, row `0` = **bottom** of display (OpenGL convention). To draw bars growing from the bottom up: `arr[0:bar_px]`, not `arr[H-bar_px:H]`.

### Use arctan compression instead of min(1.0, x)
`min(1.0, raw*gain)` hard-clips at 100% — bars get stuck. Replace with:
```python
target = (2.0 / np.pi) * np.arctan(raw * gain * ARCTAN_K)
```

### Audio loopback for clean signal
Use **VB-Audio Virtual Cable**: Windows playback → `CABLE Input`, TD `audio_in` → `CABLE Output`. Enable "Listen to this device" on CABLE Output to hear audio simultaneously. Without loopback, mic picks up ambient noise that saturates low-frequency bands.

### Reset All Parameters wipes manual settings
Use **Reset Parameter** (single param) not **Reset All Parameters** — the latter resets `resolutionw`, `resolutionh`, and other hand-tuned values.

### textTOP fontcolor doesn't support expressions
Animate color by placing `hsvadjustTOP` downstream. Text must be a saturated color (not white) for hue rotation to have any effect.

---

## Tuning Parameters

### Audio spectrum (`fx_audio/audio_viz_callbacks1`)

| Parameter | Default | Effect |
|-----------|---------|--------|
| `ATTACK` | 0.5 | Bar rise speed (lower = faster) |
| `RELEASE` | 0.93 | Bar fall speed (higher = slower sustain) |
| `BASE_GAIN` | 10.0 | Overall sensitivity |
| `FREQ_EXP` | 0.7 | High-freq boost exponent |
| `ARCTAN_K` | 0.5 | Compression (lower = more headroom before ceiling) |
| `N_BARS` | 32 | Frequency bars (bar_w = 64/N_BARS px each) |
| `F_MIN` / `F_MAX` | 60 / 8000 Hz | Displayed frequency range |

### Text marquee (`fx_text/scroller_callbacks`)

| Parameter | Default | Effect |
|-----------|---------|--------|
| `SPEED` | 0.5 | Pixels per frame (0.5 = 30 px/s at 60 fps) |

### Audio Metaball (`fx_audio_metaball/amb_callbacks`)

Audio source: reuses `fx_audio/spectrum1` — no separate `audiodeviceinCHOP` (two CHOPs on the same device both get silence).

**Shape**

| Parameter | Default | Effect |
|-----------|---------|--------|
| `BASE_RADII` | [0.09…0.07] | Base radius per ball; larger = bigger balls that merge more easily |
| `METABALL_THRESHOLD` | 1.0 | Iso-surface merge threshold; lower = blobs fuse sooner, higher = more separate |

**Idle behaviour (no music)**

| Parameter | Default | Effect |
|-----------|---------|--------|
| `BALL_CENTER` | corners + center | Home orbit center for each ball; spread across the canvas |
| `IDLE_MARGIN` | 0.18 | Orbit radius around each home center; smaller = tighter wandering |
| `BALL_FREQ` | [0.13…0.15] | Orbit frequency per ball; all different to prevent synchronisation |
| `IDLE_LERP` | 0.04 | Chase speed toward idle target (lower = slower, smoother) |

**Audio response**

| Parameter | Default | Effect |
|-----------|---------|--------|
| `AUDIO_MIN_ENERGY` | 0.03 | Rolling avg below this is treated as silence |
| `BEAT_THRESHOLD` | 1.8 | Instant bass / rolling avg ratio required to fire a beat |
| `BEAT_COOLDOWN` | 15 | Minimum frames between beats (~0.5 s at 30 fps) |
| `AUDIO_LERP_BASE` | 0.06 | Base ball chase speed during audio mode |
| `AUDIO_LERP_BOOST` | 3.0 | Extra speed multiplier on loud moments: `speed = base × (1 + energy × boost)` |

**Mode crossfade**

| Parameter | Default | Effect |
|-----------|---------|--------|
| `BLEND_RAMP_UP` | 0.05 | Idle → audio transition speed (lower = slower fade-in, ~1/ramp frames) |
| `BLEND_RAMP_DOWN` | 0.015 | Audio → idle fade-out speed (slower than fade-in for a natural decay) |

**Colour**

| Parameter | Default | Effect |
|-----------|---------|--------|
| `COLOR_LERP` | 0.04 | Colour crossfade speed; beat triggers a gradual shift, not an instant cut |
| `COLOR_AUTO_SEC` | 6.0 | Seconds without a colour change before an automatic palette switch |
| `hue_spread` | 0.12 | Width of the colour family on each beat (in `_random_colors`); 0 = identical, 0.25 = quarter colour wheel |
