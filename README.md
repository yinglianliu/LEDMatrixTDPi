# LED Matrix — TouchDesigner + Raspberry Pi

**Live demo: https://yinglianliu.github.io/LEDMatrix/**

Drives a **Waveshare P2 64×64 HUB75E LED matrix** with real-time visual effects generated in TouchDesigner and streamed over ArtNet to a Raspberry Pi Zero 2W.

---

## Hardware

| Component | Detail |
|-----------|--------|
| LED Panel | Waveshare RGB-Matrix-P2-64×64 (HUB75E, 1/32 scan) |
| Driver board | Adafruit RGB Matrix Bonnet |
| SBC | Raspberry Pi Zero 2W |
| Power | 5V 5A (panel ≤3A + Pi ≤1A) |

**Required hardware mod**: On the back of the Bonnet there is a 3-pad solder jumper labelled `16 / E / 8`. Bridge the **middle pad to `8`** — this connects the 5th row-address line (E) required by 64-row panels. Without this, the display shows two half-height repeated images.

---

## Architecture

```
TouchDesigner (Windows)
  └─ fx_switch → level1 → OUT (64×64)
       │
       ├─ viz_led (GLSL)        LED dot preview (640×640)
       │
       └─ artnet_sender         UDP → Pi Zero 2W
            (executeDAT)          ArtNet, 24 universes @ 512 bytes each

Raspberry Pi Zero 2W
  └─ artnet_matrix.py           ArtNet receiver
       └─ rgbmatrix              rpi-rgb-led-matrix library
            └─ LED Panel         64×64 physical display
```

---

## Visual Effects

Switch effects via `fx_switch.par.input` (0–6):

| Input | baseCOMP | Description |
|-------|----------|-------------|
| 0 | `fx_noise` | Organic noise with animated hue cycling |
| 1 | `fx_metaball` | 5-ball metaball liquid spheres (GLSL) |
| 2 | `fx_audio` | 32-band audio spectrum analyser |
| 3 | `fx_text` | Scrolling marquee with rainbow colour |
| 4 | `fx_audio_metaball` | Beat-reactive metaball; balls jump on each beat |
| 5 | `fx_ice_metaball` | Same as above, fixed ice-blue palette |
| 6 | `fx_camera` | Webcam feed with beat-reactive scatter + hue rotation |

---

## Repository Layout

```
LEDMatrix with TD/
├── LEDMatrixPiZero.toe      TouchDesigner project file
├── artnet_matrix.py         ArtNet receiver (runs on Pi)
├── effects/                 Effect ideas / scratch notes
├── pi_effects/              Standalone Pi runner (no TD required)
│   ├── main.py              Entry point
│   ├── config.py            All tunable parameters
│   ├── fx_noise.py
│   ├── fx_metaball.py
│   ├── fx_audio.py
│   ├── fx_audio_metaball.py
│   ├── fx_text.py
│   └── setup.sh             One-shot dependency installer
└── DEVLOG.md                Build notes and debugging lessons
```

---

## Raspberry Pi Setup

### 1. Install rpi-rgb-led-matrix

```bash
sudo apt-get install -y git cmake cython3 python3-dev python3-pillow
git clone https://github.com/hzeller/rpi-rgb-led-matrix.git
cd rpi-rgb-led-matrix

# Pi Zero 2W needs extra swap for C++ compilation
sudo dphys-swapfile swapoff
sudo sed -i 's/CONF_SWAPSIZE=.*/CONF_SWAPSIZE=1024/' /etc/dphys-swapfile
sudo dphys-swapfile setup && sudo dphys-swapfile swapon

sudo pip3 install --break-system-packages .
```

### 2. Disable audio (prevents LED flickering)

Edit `/boot/firmware/config.txt`:
```
dtoverlay=vc4-kms-v3d,noaudio
#dtparam=audio=on
```

Reboot after saving.

### 3. Run the ArtNet receiver

```bash
sudo python3 artnet_matrix.py
```

> **Set the Pi's IP** in `artnet_matrix.py` line `ARTNET_IP` before running.  
> `sudo` is required — rpi-rgb-led-matrix needs direct GPIO access.

---

## TouchDesigner Setup

1. Open `LEDMatrixPiZero.toe`
2. In `led_matrix/artnet_sender` DAT, update `ARTNET_IP = '192.168.x.x'` to match the Pi's IP
3. For audio effects: install **VB-Audio Virtual Cable** (free) and route music app output to `CABLE Input`; set TD `audio_in` device to `CABLE Output`
4. Press Play — the panel should light up within one frame

### LED Preview

`viz_led` (glslTOP, 640×640) renders each pixel as a glowing circular LED dot on a dark PCB background, visible in TD without the physical panel.

---

## Standalone Pi Runner (no TouchDesigner)

The `pi_effects/` folder is a self-contained runner — all effects run natively on the Pi.

```bash
# Install dependencies (once)
bash pi_effects/setup.sh

# Run
sudo python3 pi_effects/main.py

# Start on a specific effect
sudo python3 pi_effects/main.py --effect 2   # audio spectrum
```

Switch effects at runtime (type key + Enter):

| Key | Effect |
|-----|--------|
| `n` / `0` | Noise |
| `m` / `1` | Metaball |
| `a` / `2` | Audio spectrum |
| `t` / `3` | Scrolling text |
| `b` / `4` | Audio metaball |
| `q` | Quit |

All parameters (text, speed, audio sensitivity, colours) are in `pi_effects/config.py`.

---

## Common Configuration

### Change the scrolling text
- **TouchDesigner**: double-click `fx_text` → `txt` → Text parameter
- **Standalone Pi**: edit `TEXT_MESSAGE` in `pi_effects/config.py`

For Chinese text in TD: set `txt.par.font = 'Microsoft YaHei'`  
For Chinese text on Pi: install `fonts-wqy-zenhei` and set `TEXT_FONT = 'wqy-zenhei.ttc'`

### Tune audio sensitivity

| Parameter | Default | Effect |
|-----------|---------|--------|
| `BASE_GAIN` | 10.0 | Overall sensitivity |
| `ARCTAN_K` | 0.5 | Soft compression (lower = more dynamic range) |
| `ATTACK` | 0.5 | Bar rise speed (lower = faster) |
| `RELEASE` | 0.93 | Bar fall speed (higher = longer sustain) |
| `N_BARS` | 32 (TD) / 16 (Pi) | Frequency bands |

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Display shows top half twice | E address line not connected | Bridge Bonnet solder jumper (middle → `8`) |
| LED flickering during animation | `snd_bcm2835` PWM conflict | Add `noaudio` to vc4-kms-v3d in config.txt |
| Only 2–3 rows lit | Wrong row address type | Set `ROW_ADDRESS_TYPE = 0` in config |
| Audio bars always black | TD reads wrong audio device | Use VB-Audio loopback; set `audio_in` to `CABLE Output` |
| Audio bars stuck at 100% | Hard clipping | Lower `BASE_GAIN` or raise `ARCTAN_K` |
| `ImportError: rgbmatrix` | Library not installed | See Pi setup step 1 |

---

## Key Hardware Notes

- **ROW_ADDRESS_TYPE = 0**: The Waveshare P2 64×64 uses type 0 despite having a HUB75E connector. Type 1 causes only 2–3 rows to display.
- **GPIO slowdown = 4**: Required for Pi Zero 2W stability. Use 1–2 on Pi 4.
- **ArtNet packing**: 64×64×3 = 12,288 bytes → 24 universes of 512 bytes each, numbered sequentially.
- **GPIO pins used by Bonnet**: 4, 5, 6, 12, 13, 16, 17, 20, 21, 22, 23, 24, 26, 27. Free pins: 2, 3, 7, 8, 9, 10, 11, 14, 15, 19, 25.
