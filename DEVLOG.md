# Dev Log

## 2026-05-09 — Audio Reactive LED Matrix: First Build

---

### [TD] scriptTOP output is frozen — never updates

**Symptom**: `audio_viz` scriptTOP renders a static frame even when audio data changes.

**Cause**: When a scriptTOP has no wired TOP input, TouchDesigner assumes its inputs are unchanged and skips re-cooking. Even if the Python code reads a CHOP that changes every frame, TD never triggers a new cook.

**Fix**: Create a 1×1 `noiseTOP` named `cook_trigger` with `tz = absTime.seconds`. Wire it into `audio_viz` input 0. The changing noiseTOP forces a cook every frame.

**Lesson**: TD's cook model is demand-driven — operators only recompute when a downstream consumer requests it AND an input has changed. Reading a CHOP inside Python does not, by itself, trigger a cook.

---

### [TD] audiospectrumCHOP frequency indexing is completely wrong

**Symptom**: Low-frequency bars (0–37) read 0.0000; high-frequency bars (58–63) are inexplicably loud — the opposite of expected.

**Cause**: With `frequencylog=1.0`, the 22 050 output samples are **logarithmically distributed**, not linear. Using the linear formula `idx = int(freq / (F_MAX*2/n))` maps:
- What we think is 60 Hz → actually queries ~20 Hz (near silence)
- What we label "high freq" → actually mid-range 500–600 Hz

**Fix**: Set `audiospectrumCHOP.frequencylog = 0` (linear mode). In linear mode, sample index `k ≈ k Hz`, so `idx = int(freq_in_hz)` works directly.

**Verify**:
```python
row = op('spectrum1').numpyArray()[0]
print(row[60])    # should be energy at 60 Hz
print(row[1000])  # should be energy at 1 kHz
```

**Lesson**: Never assume CHOP samples are linearly distributed. Always verify index-to-frequency mapping before writing any lookup logic.

---

### [TD] scriptTOP numpy array Y-axis is inverted

**Symptom**: Spectrum bars grow downward from the top of the display instead of upward from the bottom.

**Cause**: In `copyNumpyArray`, TD follows the **OpenGL convention**: `arr[0]` = bottom of the display, `arr[H-1]` = top. Writing to `arr[H-bar_px:H]` fills the top region, so bars appear inverted.

Note: this is the **opposite** of `TOP.numpyArray()` (read mode), where `row[0]` = image top. Write direction and read direction differ.

**Fix**: Use `arr[0:bar_px]` — fill upward from row 0 (bottom).
```python
arr[0:bar_px, x0:x1, :3] = col          # bar body
arr[bar_px-1, x0:x1, :3] = peak_color   # bright tip
```

**Lesson**: TD's coordinate origin is inconsistent across contexts (OpenGL bottom-origin vs image top-origin). Test with a solid colour block to verify direction before building any pixel layout.

---

### [TD] Bars stuck at 100% for extended periods

**Symptom**: Spectrum bars hit the ceiling and stay there, making it impossible to see dynamics.

**Cause**: Using `min(1.0, raw * gain)` hard-clips everything above 1.0 to 100%. Mid-frequency bands (300–1000 Hz) routinely produce gain-amplified values of 2–3, all collapsed to the same 100%.

**Fix**: Replace with **arctan soft compression**:
```python
target = (2.0 / np.pi) * np.arctan(raw * gain * ARCTAN_K)
```
arctan never reaches 1.0 — loud signals approach but never hit the ceiling, preserving dynamic distinction.

| Raw × gain | `min(1.0)` | `arctan(k=0.5)` |
|-----------|-----------|-----------------|
| 0.5 | 50% | 31% |
| 1.0 | 100% ← clipped | 50% |
| 2.0 | 100% ← clipped | 67% |
| 4.0 | 100% ← clipped | 79% |

**Lesson**: Hard clipping destroys dynamic range. Use sigmoid / arctan / tanh for audio visualisation.

---

### [TD] High-frequency bars (right side) always dark

**Symptom**: Low-frequency bars respond to music; 5–8 kHz bars are always black.

**Cause 1**: A global `MIN_SQUELCH = 0.003` mutes everything below it, but 5–8 kHz signal levels are naturally only ~0.001.

**Cause 2**: Audio energy decreases naturally with frequency. High-frequency bins can be 50–100× quieter than low-frequency bins; a single fixed gain can only serve one range.

**Fix**: Remove the squelch threshold; use **frequency-weighted gain**:
```python
gain = BASE_GAIN * (freq / F_MIN) ** FREQ_EXP  # FREQ_EXP ≈ 0.7
```
Low freq gain ≈ 10; high freq gain ≈ 250. Each band gets a gain appropriate to its natural energy level.

**Lesson**: The core challenge of spectrum visualisation is the enormous dynamic range difference across frequency bands. A single fixed gain can only expose one region.

---

### [TD] Adaptive noise floor causes "flash and vanish" flickering

**Symptom**: Bars don't rise and fall smoothly — they flash brightly and immediately disappear.

**Cause**: An adaptive noise floor was filtering ambient noise with asymmetric decay:
- Signal absent → floor drops fast (`NOISE_FALL = 0.92`, -8% per frame)
- Signal present → floor rises slowly

Between beats (0.3–0.5 s), `0.92^30 ≈ 0.08` — the floor collapses from 0.05 to 0.004. On the next beat, the signal/floor ratio hits 300+, instantly clipping every bar to 100%, producing the strobe effect.

**Fix**: Remove the adaptive noise floor entirely. Use fixed frequency-weighted gain plus arctan compression. Volume variability is normal; soft compression handles it without dynamic thresholding.

**Lesson**: Adaptive mechanisms are hard to tune for attack/release — too slow and they miss transitions, too fast and they chase the signal itself, eliminating what you wanted to show.

---

### [Audio] Microphone picks up heavy ambient noise

**Symptom**: In a quiet room, the 375–692 Hz ambient noise already registers at 71%, drowning the music signal.

**Cause**: The built-in microphone captures fan noise, air conditioning, and electrical interference concentrated in the low-to-mid frequency range.

**Fix**: Use **VB-Audio Virtual Cable** for a clean loopback:
- Install (free): https://vb-audio.com/Cable/
- In Windows Volume Mixer, route the music app output to `CABLE Input (VB-Audio)`
- In TD, set `audio_in` device to `CABLE Output (VB-Audio)`
- In Windows Recording devices → CABLE Output → Properties → Listen → check "Listen to this device" and select real speakers — this lets TD analyse AND the user hear audio simultaneously

**Result**: After switching, all frequency bands read 0.00000 in silence — completely clean.

---

### [Audio] Changed default system output but the app still routes to the old device

**Symptom**: Windows default playback device changed to `CABLE Input`, but TD spectrum still reads silence.

**Cause**: Some apps (Spotify, Apple Music) maintain their own audio device setting, or were already opened on the old device and do not follow system default changes.

**Fix**: Open Windows **Volume Mixer** (right-click taskbar → Open Volume Mixer), find the specific music app, and change its output device to `CABLE Input` individually.

**Diagnose**:
```python
import numpy as np
a = op('/project1/led_matrix/audio_in')
arr = a.numpyArray()
print(float(np.sqrt(np.mean(arr**2))))  # active music should be > 0.01
```

---

### [Hardware] Adafruit RGB Matrix Bonnet does not support 64-row panels by default

**Symptom** (expected — confirmed in theory before testing): 64×64 matrix shows two half-height repeated images, or rows are misaddressed.

**Cause**: The Bonnet connects only 4 row-address lines (A/B/C/D), supporting up to 32 rows. 64-row panels require a 5th address line (E).

**Fix**: On the back of the Bonnet there is a 3-pad solder jumper labelled `16 / E / 8`. Bridge the **middle pad to the `8` pad**. This pre-routed trace connects the E address line to Raspberry Pi GPIO 8.

Software: `options.row_address_type = 1` in `artnet_matrix.py`.

---

### [TD] GLSL shader error: `sTD2DInputs: redeclaration of array`

**Symptom**: Declaring `uniform sampler2D sTD2DInputs[1];` at the top of a GLSL shader causes a compile error in the info DAT.

**Cause**: TouchDesigner automatically injects the `sTD2DInputs` declaration before compiling. A manual declaration conflicts with it.

**Fix**: Remove the `uniform sampler2D sTD2DInputs[1];` line. Use `texture(sTD2DInputs[0], uv)` directly. Same rule applies to `uTD2DInfos`.

---

### [TD] `TDTime.seconds` is not available in GLSL

**Symptom**: Writing `float t = TDTime.seconds;` in a GLSL shader causes `'TDTime' : undeclared identifier`.

**Cause**: `TDTime` is not a built-in GLSL uniform in TD. `absTime` is Python-only.

**Fix**: In the glslTOP Vectors page, create a vec4 uniform:
- `vec0name` = `uVars`
- `vec0valuex` Expression = `absTime.seconds`

In the shader, declare `uniform vec4 uVars;` and access time via `uVars.x`.

---

### [TD] After moving an operator into a baseCOMP, the callbacks DAT is renamed and scriptTOP stops executing

**Symptom**: After moving `audio_viz` into the `fx_audio` baseCOMP, the spectrum display goes black and no parameter changes have any effect.

**Cause**: When `COMP.copy(vz_src)` copies a scriptTOP, if the target COMP already contains a DAT with the same name, TD appends a numeric suffix to the docked callbacks DAT (`audio_viz_callbacks` → `audio_viz_callbacks1`). The scriptTOP's `callbacks` parameter is left empty — no callbacks ever run.

**Fix**: Use `execute_python` to find the actual docked DAT name, then set `vz.par.callbacks = 'audio_viz_callbacks1'` manually.

**Diagnose**:
```python
vz = op('/project1/led_matrix/fx_audio/audio_viz')
print([d.name for d in vz.docked])  # find actual docked DAT name
print(vz.par.callbacks.val)          # check if callbacks param is empty
```

**Lesson**: After copying a scriptTOP into a baseCOMP, always verify the `callbacks` parameter — do not rely on the dock relationship alone.

---

### [TD] scriptTOP resolution set to 64 but output is still 128

**Symptom**: `resolutionw=64`, `resmult=False`, but `vz.width` returns 128.

**Cause**: When callbacks are empty, `copyNumpyArray` is never called and the output stays at the 128×128 cached state from a previous cook.

**Fix**: Fix the callbacks connection first, then hardcode `W = 64; H = 64` in the code — do not rely on `scriptOp.width`, which may return a stale cached value.

---

### [TD] Pressing Enter in the TD DAT editor does not commit changes

**Symptom**: Editing `N_BARS` in the TD DAT editor produces no visible change.

**Cause**: In TD's textDAT editor, Enter = newline. **Escape** = commit and apply. Without pressing Escape, the edit is not submitted and the Python module is not reloaded.

**Fix**: Press **Escape** after editing. If still no effect, right-click the scriptTOP → **Reset Script** to force a module reload.

---

### [TD] 16 spectrum bars move in sync instead of responding independently

**Symptom**: Adjacent bars light up and go dark together, behaving as a single unit rather than independent frequency bands.

**Cause**: With `fftsize=8192`, frequency resolution ≈ 5.4 Hz/bin. Low-frequency bands (60–200 Hz) are only 4–12 Hz wide — smaller than one FFT bin. Multiple bars share a single bin and get identical values.

**Fix**:
1. Set `fftsize = 16384` (resolution improves to 2.7 Hz/bin)
2. Read the full spectrum with `numpyArray()` and take the **max** across all bins in each band, not a single point sample
3. Raise the low-frequency floor from 40 Hz to 60 Hz to skip the region where resolution is insufficient

```python
band = row[idx_lo:idx_hi]
raws[b] = band.max()   # not row[single_idx]
```

---

## 2026-05-10 — baseCOMP Refactor + Text Effect

---

### [TD] After COMP.copy(), callbacks DAT is renamed and the parameter is left empty

**Symptom**: After moving `audio_viz` into the `fx_audio` baseCOMP, the scriptTOP output is black and no code changes have any effect.

**Cause**: `COMP.copy()` renames docked DATs if a name collision exists in the target COMP (`audio_viz_callbacks` → `audio_viz_callbacks1`). The `callbacks` parameter is left empty — no callbacks run.

**Diagnose**:
```python
vz = op('/project1/led_matrix/fx_audio/audio_viz')
print([d.name for d in vz.docked])  # find actual name
print(vz.par.callbacks.val)          # confirm it is empty
```

**Fix**: `vz.par.callbacks = 'audio_viz_callbacks1'`

**Lesson**: After any copy into a baseCOMP, always verify the `callbacks` parameter.

---

### [TD] scriptTOP resolution set to 64 but output is 128

**Symptom**: `resolutionw=64`, `resmult=False`, but `scriptOp.width` returns 128.

**Cause**: With an empty callbacks parameter, `copyNumpyArray` is never called and output stays at the previous 128×128 cached state. Even after fixing callbacks, `scriptOp.width` may return the stale size from the last cook.

**Fix**: Hardcode `W = 64; H = 64` in the callbacks — never read from `scriptOp.width`.

---

### [TD] Reset All Parameters clears manually-set resolution

**Symptom**: Right-click operator → Reset All Parameters resets `resolutionw` back to the default (256).

**Fix**: Use **Reset Parameter** (single parameter only), never **Reset All Parameters**. Restore via MCP: `resolutionw=64`, `resolutionh=64`, `resmult=False`.

---

### [TD] textTOP `fontcolor` parameter does not support expressions

**Symptom**: Assigning an expression to `fontcolorr.expr` throws `Error in parameter fontcolor`.

**Fix**: Place an `hsvadjustTOP` downstream with `hueoffset.expr = 'absTime.seconds * 40 % 360'`. Important: the text color must be a saturated hue (e.g. pure red R=1, G=0, B=0) — white text has zero saturation so hue rotation has no effect.

---

### [TD] textTOP canvas wider than actual text causes a long pause in the scroll loop

**Symptom**: After the text passes, there is a long blank wait before it reappears, because the scriptTOP is scrolling across 512 px of empty canvas.

**Cause**: `textTOP` is set to 512×64 but the text only occupies ~150–200 px. The scroll loop length is based on the full 512 px width.

**Fix**: Auto-detect the actual text extent in the scroll callbacks:
```python
mask = np.any(src[:, :, :3] > 0.02, axis=(0, 2))
text_right = int(np.where(mask)[0][-1]) + 1 if np.any(mask) else src_w
effective_w = text_right + W // 2  # text width + half-screen pause
total = W + effective_w
```

---

### [TD] Default textTOP font does not support Chinese characters

**Symptom**: Chinese characters typed into the textTOP Text parameter appear as blanks or garbled.

**Cause**: The default font (Verdana) does not include CJK characters.

**Fix**: Set the `font` parameter to a CJK-capable font (Windows built-in options):
- `Microsoft YaHei` (recommended)
- `SimHei`

---

### [TD] Editing N_BARS inside a baseCOMP has no effect

**Symptom**: Entering `fx_audio`, editing `N_BARS` in `audio_viz_callbacks`, and pressing Escape produces no visible change.

**Cause**: The active callbacks DAT is named `audio_viz_callbacks1` (renamed by TD during the copy). The DAT being edited (`audio_viz_callbacks`) is not connected to anything.

**Fix**: Inside the baseCOMP, identify the DAT that has a blue dock wire to the scriptTOP — that is the active one. Confirm with MCP: `[d.name for d in vz.docked]`.

---

## 2026-05-10 — fx_audio_metaball baseCOMP Development

---

### [TD] Two audiodeviceinCHOPs on the same device — one gets silence

**Symptom**: `fx_audio_metaball` has its own `audio_in` pointed at VB-Audio Virtual Cable, but `spectrum1.bass` reads 0 while `fx_audio/audio_in` works fine.

**Cause**: TD does not allow two `audiodeviceinCHOP` operators to simultaneously capture the same device. The second CHOP receives no signal.

**Fix**: Delete `audio_in` and `spectrum1` from `fx_audio_metaball`. Reference `fx_audio/spectrum1` directly in callbacks:
```python
sp = scriptOp.parent().parent().op('fx_audio/spectrum1')
```

**Lesson**: When multiple baseCOMPs share one audio source, open only one `audiodeviceinCHOP`. Other COMPs navigate to it by relative path.

---

### [TD] `op()` inside scriptTOP callbacks resolves relative to the scriptTOP, not the callbacks DAT

**Symptom**: `op('spectrum1')` returns None inside callbacks, even though `spectrum1` is a sibling of `amb_viz` in the same baseCOMP.

**Cause**: Inside scriptTOP callbacks, `op()` resolves relative to the scriptTOP operator itself (`amb_viz`), not the DAT file that contains the code. `op('spectrum1')` looks for a child of `amb_viz`, which doesn't exist.

**Fix**: Always navigate using `scriptOp` as the anchor:
```python
# sibling inside the same baseCOMP:
sp = scriptOp.parent().op('spectrum1')
# sibling in a different baseCOMP one level up:
sp = scriptOp.parent().parent().op('fx_audio/spectrum1')
```

---

### [TD] `scriptOp.store()` inside `onCook` causes a cook dependency loop

**Symptom**: After calling `scriptOp.store('key', data)` inside `onCook`, TD reports "Cook dependency loop detected".

**Cause**: `store()` triggers TD's dependency update mechanism. This causes the scriptTOP to request a re-cook of itself during its own cook, creating a circular dependency.

**Fix**: Use a **module-level variable** to persist state across frames. Module-level variables in a textDAT survive between cooks without touching TD's dependency system:
```python
_S = None

def onCook(scriptOp):
    global _S
    if _S is None:
        _init_state()
```

---

### [Design] Metaball intersection turns white

**Symptom**: When two balls overlap, the intersection area becomes white and visually washed out.

**Cause**: Classic metaball compositing uses weighted-average colour blending. `interior + glow` can exceed 1.0 before being clipped — all channels clip to 1 = white.

**Fix**: Two-step approach:
1. Use `np.argmax(w_ball, axis=0)` to find which ball dominates each pixel; take that ball's colour (always fully saturated)
2. Compute a brightness field separately and clamp it to 1: `bfield = (interior + glow).clip(0, 1)`

Result = saturated colour × brightness field — can never overflow to white.

---

### [Design] Same-hue colour palette + auto timed colour change

**Implementation**:
- On each beat, pick a random `base_hue`; all 5 balls get colours within `base_hue ± hue_spread` — keeps the palette cohesive
- `COLOR_AUTO_SEC = 6.0`: if no colour change has occurred for this many seconds, automatically switch to a new palette
- `COLOR_LERP = 0.04`: colour changes are gradual crossfades (~1–2 s), not instant cuts
- Beat resets the auto-switch timer to prevent double-triggering

**Key parameters** (top of `amb_callbacks` DAT):
```python
COLOR_AUTO_SEC = 6.0   # seconds of no change before auto palette switch
COLOR_LERP     = 0.04  # colour crossfade speed
hue_spread     = 0.12  # palette width in _random_colors(); 0=identical, 0.25=quarter colour wheel
```
