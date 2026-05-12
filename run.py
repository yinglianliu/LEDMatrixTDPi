"""
LED Matrix unified launcher
===========================
Usage:
    sudo python3 run.py               # auto-detect (ArtNet first, fallback standalone)
    sudo python3 run.py --artnet      # force ArtNet mode
    sudo python3 run.py --standalone  # force standalone mode

SSH keyboard commands (press Enter after each):
    a        → switch to ArtNet mode
    s        → switch to standalone mode
    0-4      → switch standalone effect
    n/m/t/b  → switch standalone effect (same as 0-4)
    q        → quit
"""

import sys
import time
import socket
import threading
import argparse
import numpy as np
from PIL import Image

sys.path.insert(0, 'pi_effects')
import config as cfg

ARTNET_PORT   = 6454
UNIVERSE_SIZE = 512
N_UNIVERSES   = (cfg.ROWS * cfg.COLS * 3 + UNIVERSE_SIZE - 1) // UNIVERSE_SIZE

EFFECT_KEYS = {
    'n': 0, '0': 0,
    'm': 1, '1': 1,
    'a': 2, '2': 2,
    't': 3, '3': 3,
    'b': 4, '4': 4,
}

# ── shared state (written by keyboard thread, read by main thread) ─────────────
_mode    = ['standalone']   # 'artnet' or 'standalone'
_effect  = [0]
_stop    = threading.Event()
_switch  = threading.Event()   # signals main loop to switch mode


def _keyboard_thread():
    """Background thread: read single-key commands from stdin."""
    while not _stop.is_set():
        try:
            line = input().strip().lower()
        except EOFError:
            _stop.set()
            break
        if line == 'q':
            _stop.set()
            break
        elif line == 'a':
            _mode[0] = 'artnet'
            _switch.set()
            print('[kbd] switching to ArtNet')
        elif line == 's':
            _mode[0] = 'standalone'
            _switch.set()
            print('[kbd] switching to standalone')
        elif line in EFFECT_KEYS:
            _effect[0] = EFFECT_KEYS[line]
            print(f'[kbd] effect → {_effect[0]}')


# ── matrix setup ──────────────────────────────────────────────────────────────

def build_matrix():
    from rgbmatrix import RGBMatrix, RGBMatrixOptions
    opts = RGBMatrixOptions()
    opts.rows             = cfg.ROWS
    opts.cols             = cfg.COLS
    opts.chain_length     = cfg.CHAIN_LENGTH
    opts.parallel         = cfg.PARALLEL
    opts.hardware_mapping = cfg.HARDWARE_MAPPING
    opts.row_address_type = cfg.ROW_ADDRESS_TYPE
    opts.gpio_slowdown    = cfg.GPIO_SLOWDOWN
    opts.pwm_bits              = cfg.PWM_BITS
    opts.drop_privileges       = cfg.DROP_PRIVILEGES
    opts.disable_hardware_pulsing = getattr(cfg, 'NO_HARDWARE_PULSE', False)
    opts.limit_refresh_rate_hz    = 100   # cap refresh to reduce flicker
    return RGBMatrix(options=opts)


# ── ArtNet receiver (runs in main thread) ─────────────────────────────────────

def run_artnet(matrix):
    """Receive ArtNet UDP packets and display on matrix. Returns when mode changes."""
    print('[ArtNet] listening on UDP :6454 — waiting for TD...')
    frame_buf = bytearray(cfg.ROWS * cfg.COLS * 3)
    canvas    = matrix.CreateFrameCanvas()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.settimeout(0.5)
    sock.bind(('', ARTNET_PORT))

    try:
        while not _stop.is_set() and not _switch.is_set():
            try:
                data, _ = sock.recvfrom(600)
            except socket.timeout:
                continue

            if len(data) < 18 + 2:
                continue

            universe = data[14] | (data[15] << 8)
            payload  = data[18:]
            offset   = universe * UNIVERSE_SIZE
            end      = min(offset + len(payload), len(frame_buf))
            if offset < len(frame_buf):
                frame_buf[offset:end] = payload[:end - offset]

            if universe == N_UNIVERSES - 1:
                img = Image.frombytes('RGB', (cfg.COLS, cfg.ROWS), bytes(frame_buf))
                canvas.SetImage(img)
                canvas = matrix.SwapOnVSync(canvas)
    finally:
        sock.close()
        matrix.Clear()
        print('[ArtNet] stopped')


# ── standalone effects (runs in main thread) ───────────────────────────────────

def run_standalone(matrix):
    """Run pi_effects render loop. Returns when mode changes."""
    from fx_noise          import NoiseEffect
    from fx_metaball       import MetaballEffect
    from fx_audio          import AudioEffect
    from fx_text           import TextEffect
    from fx_audio_metaball import AudioMetaballEffect

    W, H = cfg.COLS, cfg.ROWS
    effects = [
        NoiseEffect(W, H),
        MetaballEffect(W, H),
        AudioEffect(W, H, cfg),
        TextEffect(W, H, cfg),
        AudioMetaballEffect(W, H, cfg),
    ]

    canvas     = matrix.CreateFrameCanvas()
    frame_time = 1.0 / cfg.TARGET_FPS
    t_start    = time.monotonic()
    cur        = _effect[0]
    print(f'[Standalone] running effect {cur}')

    try:
        while not _stop.is_set() and not _switch.is_set():
            # Check for effect change
            if _effect[0] != cur:
                cur = _effect[0]
                print(f'[Standalone] switched to effect {cur}')

            t     = time.monotonic() - t_start
            frame = time.monotonic()

            arr = effects[cur].render(t)
            canvas = matrix.CreateFrameCanvas()
            canvas.SetImage(Image.fromarray(arr, 'RGB'))
            matrix.SwapOnVSync(canvas)

            elapsed = time.monotonic() - frame
            sleep   = frame_time - elapsed
            if sleep > 0:
                time.sleep(sleep)
    finally:
        for e in effects:
            e.cleanup()
        matrix.Clear()
        print('[Standalone] stopped')


# ── probe for ArtNet ──────────────────────────────────────────────────────────

def probe_artnet(timeout=5.0):
    """Return True if an ArtNet packet arrives within timeout seconds."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.settimeout(timeout)
    try:
        sock.bind(('', ARTNET_PORT))
        sock.recv(600)
        return True
    except socket.timeout:
        return False
    finally:
        sock.close()


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    group  = parser.add_mutually_exclusive_group()
    group.add_argument('--artnet',     action='store_true')
    group.add_argument('--standalone', action='store_true')
    args = parser.parse_args()

    # Determine starting mode
    if args.artnet:
        _mode[0] = 'artnet'
    elif args.standalone:
        _mode[0] = 'standalone'
    else:
        print('Auto-detecting ArtNet signal (5 s)...')
        if probe_artnet(timeout=5.0):
            print('[Auto] ArtNet detected')
            _mode[0] = 'artnet'
        else:
            print('[Auto] No ArtNet signal — starting standalone')
            _mode[0] = 'standalone'

    print('Initialising LED matrix...')
    matrix = build_matrix()

    # Start keyboard input thread
    kbd = threading.Thread(target=_keyboard_thread, daemon=True)
    kbd.start()

    print('Commands: a=ArtNet  s=standalone  0-4=effect  q=quit')

    # Main loop: rendering always happens in main thread
    while not _stop.is_set():
        _switch.clear()

        if _mode[0] == 'artnet':
            run_artnet(matrix)
        else:
            run_standalone(matrix)

    matrix.Clear()
    print('Bye.')


if __name__ == '__main__':
    main()
