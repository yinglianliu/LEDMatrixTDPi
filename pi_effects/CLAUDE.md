# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this directory.

---

## What this folder is

A **standalone runner for Pi Zero 2W** — no TouchDesigner required. Runs directly on the Pi with 5 visual effects switchable from the keyboard.

```
main.py               ← entry point
config.py             ← all tunable parameters (edit here)
fx_noise.py           ← generative noise effect
fx_metaball.py        ← metaball liquid-sphere effect
fx_audio.py           ← audio-reactive spectrum effect
fx_audio_metaball.py  ← beat-reactive metaball effect
fx_text.py            ← scrolling text marquee effect
setup.sh              ← one-shot dependency installer
```

---

## Quick start

```bash
# Install dependencies (once only)
bash setup.sh

# Run (must use sudo)
sudo python3 main.py

# Start on a specific effect
sudo python3 main.py --effect 0   # noise
sudo python3 main.py --effect 1   # metaball
sudo python3 main.py --effect 2   # audio spectrum
sudo python3 main.py --effect 3   # text
sudo python3 main.py --effect 4   # audio metaball
```

Switch effects at runtime by typing a key and pressing Enter:
- `n` or `0` → noise
- `m` or `1` → metaball
- `a` or `2` → audio reactive spectrum
- `t` or `3` → scrolling text
- `b` or `4` → audio metaball (beat-triggered random positions)
- `q` → quit

---

## Common edits — `config.py` is all you need

### Change the text message
```python
TEXT_MESSAGE = 'HAPPY MOTHERS DAY'
```

### Change text size
```python
TEXT_FONT_SIZE = 14   # larger = bigger; for a 64 px tall panel, 10–20 is recommended
```

### Change scroll speed
```python
TEXT_SPEED = 1   # pixels/frame; 1=60 px/s, 0.5=30 px/s (slower), 2=120 px/s (faster)
```

### Change font (Chinese support)
```python
TEXT_FONT = 'wqy-zenhei.ttc'   # WenQuanYi Zen Hei, supports CJK
# Install: sudo apt-get install -y fonts-wqy-zenhei
```
The default `DejaVuSans-Bold.ttf` covers Latin and common symbols only.

### Change matrix resolution (if using a different panel)
```python
ROWS = 64
COLS = 64
```

### Change target frame rate
```python
TARGET_FPS = 30   # 25–30 recommended for Pi Zero 2W
```

### Change audio input device
```python
AUDIO_DEVICE = None   # None = system default
# List available devices: python3 -c "import sounddevice; print(sounddevice.query_devices())"
AUDIO_DEVICE = 1      # set to the desired device index
```

### Tune audio spectrum sensitivity
```python
BASE_GAIN = 10.0   # overall sensitivity (higher = more reactive, lower = avoids clipping)
ARCTAN_K  = 0.5    # soft compression strength (lower = more dynamic headroom)
N_BARS    = 16     # number of frequency bands (4/8/16/32; more = thinner bars)
ATTACK    = 0.5    # bar rise speed (lower = faster attack)
RELEASE   = 0.93   # bar fall speed (higher = slower decay / longer sustain)
```

---

## Effect file reference

### `fx_noise.py` — NoiseEffect
Layered sin/cos functions simulate organic noise; hue drifts over time. No config.py entries — tweak coefficients directly in the file.

Key variables (at the top of `render()`):
```python
np.sin(xx * 1.0 + t * 0.71)   # 0.71 controls spatial frequency × speed
```

### `fx_metaball.py` — MetaballEffect
5 coloured liquid spheres. Each ball is defined as a tuple in `self.balls`:
```python
# (speed_x, speed_y, radius, phase_x, phase_y, colour RGB 0-1)
(0.71, 0.53, 0.13, 0.0, 0.0, (0.0, 0.6, 1.0)),
```
Edit this list directly to change colour, size, and speed.

### `fx_audio.py` — AudioEffect
Requires an audio input device. On Pi, use a USB sound card or I2S microphone.
- **USB sound card** (easiest): plug in and set `AUDIO_DEVICE = None` — usually auto-detected
- **I2S microphone** (e.g. INMP441): requires additional kernel configuration — follow a Pi I2S mic tutorial

Spectrum tuning parameters: see the `config.py` section above.

### `fx_audio_metaball.py` — AudioMetaballEffect
Metaball rendering combined with audio beat detection.

**How it works**: monitors low-frequency energy (60–300 Hz). When the instantaneous energy exceeds 1.8× the 30-frame rolling average, a beat is declared — all balls fly to new random positions, colours randomise, and ball radii pulse with the energy level.

Tunable parameters (class attributes at the top of `fx_audio_metaball.py`):

| Parameter | Default | Effect |
|-----------|---------|--------|
| `BEAT_THRESHOLD` | 1.8 | Energy ratio to trigger a beat (lower = more sensitive, higher = hard hits only) |
| `BEAT_COOLDOWN` | 15 | Minimum frames between beats (~0.5 s at 30 fps) |
| `LERP_SPEED` | 0.06 | How fast balls chase their target (0.01 = slow drift, 0.2 = instant snap) |
| `IDLE_DRIFT` | 0.002 | Random position drift amplitude between beats |

### `fx_text.py` — TextEffect
Text is rendered to a wide PIL strip; the strip scrolls right-to-left one frame at a time.
- Colour cycles through the rainbow automatically (white text + hue tint per frame)
- Loop length is auto-detected from the actual rendered text width — no blank waiting period

---

## Hardware configuration (edit if wiring differs)

Hardware parameters in `config.py`:

| Parameter | Default | Notes |
|-----------|---------|-------|
| `HARDWARE_MAPPING` | `'adafruit-hat'` | Use this for the Adafruit RGB Matrix Bonnet |
| `ROW_ADDRESS_TYPE` | `1` | Required for 64-row panels (E address line — solder jumper must be bridged) |
| `GPIO_SLOWDOWN` | `4` | Pi Zero 2W: use 3–4; Pi 4: use 1–2 |
| `PWM_BITS` | `11` | Higher = smoother colour gradients, but more CPU load |

---

## Troubleshooting

**`ImportError: No module named 'rgbmatrix'`**
→ The rpi-rgb-led-matrix library is not installed. See the installation notes in `artnet_matrix.py` in the parent directory.

**Flickering display / unstable colours**
→ Increase `GPIO_SLOWDOWN` (try 4 or 5).

**Text not showing / garbled characters**
→ Check the font file path. Run `fc-list` to list installed fonts.

**Audio effect is all black / no response**
→ 1. Check that the mic or sound card is recognised: `arecord -l`
→ 2. Verify sounddevice is installed: `pip3 install sounddevice`
→ 3. Set `AUDIO_DEVICE` to an explicit device index in `config.py`

**Display shows only the top half, repeated twice**
→ The E address-line solder jumper on the Bonnet has not been bridged (or is bridged to the wrong pad). See the main project README.
