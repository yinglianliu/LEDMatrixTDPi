"""
LED Matrix unified launcher
===========================
Usage:
    sudo python3 run.py               # auto-detect (ArtNet first, fallback standalone)
    sudo python3 run.py --artnet      # force ArtNet mode
    sudo python3 run.py --standalone  # force standalone mode

SSH keyboard commands (press Enter after each):
    a  →  switch to ArtNet mode (waiting for TD)
    s  →  switch to standalone mode
    0-4, n/m/t/b  →  switch standalone effect (same keys as pi_effects)
    q  →  quit
"""

import sys
import time
import socket
import threading
import argparse

# ── matrix setup ──────────────────────────────────────────────────────────────

def build_matrix():
    from rgbmatrix import RGBMatrix, RGBMatrixOptions
    import importlib, sys as _sys
    _sys.path.insert(0, 'pi_effects')
    cfg = importlib.import_module('config')

    opts = RGBMatrixOptions()
    opts.rows               = cfg.ROWS
    opts.cols               = cfg.COLS
    opts.chain_length       = cfg.CHAIN_LENGTH
    opts.parallel           = cfg.PARALLEL
    opts.hardware_mapping   = cfg.HARDWARE_MAPPING
    opts.row_address_type   = cfg.ROW_ADDRESS_TYPE
    opts.gpio_slowdown      = cfg.GPIO_SLOWDOWN
    opts.pwm_bits           = cfg.PWM_BITS
    opts.drop_privileges    = cfg.DROP_PRIVILEGES
    return RGBMatrix(options=opts), cfg

# ── ArtNet mode ───────────────────────────────────────────────────────────────

ARTNET_PORT   = 6454
ARTNET_HEADER = 18      # ArtNet DMX header bytes
UNIVERSE_SIZE = 512     # bytes per universe
N_UNIVERSES   = 24      # 64×64×3 / 512 = 24

class ArtNetMode:
    def __init__(self, matrix, cfg):
        self.matrix = matrix
        self.cfg    = cfg
        self._stop  = threading.Event()
        self._frame = bytearray(cfg.ROWS * cfg.COLS * 3)
        self._lock  = threading.Lock()

    def start(self):
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        print('[ArtNet] listening on UDP :6454 — waiting for TD...')

    def stop(self):
        self._stop.set()

    def probe(self, timeout=5.0):
        """Return True if an ArtNet packet arrives within timeout seconds."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout)
        sock.bind(('', ARTNET_PORT))
        try:
            sock.recv(600)
            return True
        except socket.timeout:
            return False
        finally:
            sock.close()

    def _run(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.settimeout(1.0)
        sock.bind(('', ARTNET_PORT))

        canvas = self.matrix.CreateFrameCanvas()
        W, H   = self.cfg.COLS, self.cfg.ROWS

        while not self._stop.is_set():
            try:
                data, _ = sock.recvfrom(600)
            except socket.timeout:
                continue

            if len(data) < ARTNET_HEADER + 2:
                continue

            universe = data[14] | (data[15] << 8)
            payload  = data[ARTNET_HEADER:]

            with self._lock:
                offset = universe * UNIVERSE_SIZE
                end    = min(offset + len(payload), len(self._frame))
                if offset < len(self._frame):
                    self._frame[offset:end] = payload[:end - offset]

            if universe == N_UNIVERSES - 1:
                from PIL import Image
                img = Image.frombytes('RGB', (W, H), bytes(self._frame))
                canvas.SetImage(img)
                canvas = self.matrix.SwapOnVSync(canvas)

        sock.close()
        self.matrix.Clear()
        print('[ArtNet] stopped')

# ── Standalone mode ───────────────────────────────────────────────────────────

class StandaloneMode:
    EFFECTS = {
        'n': 0, '0': 0,
        'm': 1, '1': 1,
        'a': 2, '2': 2,
        't': 3, '3': 3,
        'b': 4, '4': 4,
    }

    def __init__(self, matrix, cfg):
        self.matrix   = matrix
        self.cfg      = cfg
        self._stop    = threading.Event()
        self._current = [0]

    def start(self, effect=0):
        self._stop.clear()
        self._current[0] = effect
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        print(f'[Standalone] running effect {effect}')

    def stop(self):
        self._stop.set()

    def set_effect(self, key):
        idx = self.EFFECTS.get(key)
        if idx is not None:
            self._current[0] = idx
            print(f'[Standalone] switched to effect {idx}')

    def _run(self):
        import sys
        sys.path.insert(0, 'pi_effects')
        from fx_noise          import NoiseEffect
        from fx_metaball       import MetaballEffect
        from fx_audio          import AudioEffect
        from fx_text           import TextEffect
        from fx_audio_metaball import AudioMetaballEffect
        from PIL import Image

        W, H = self.cfg.COLS, self.cfg.ROWS
        effects = [
            NoiseEffect(W, H),
            MetaballEffect(W, H),
            AudioEffect(W, H, self.cfg),
            TextEffect(W, H, self.cfg),
            AudioMetaballEffect(W, H, self.cfg),
        ]

        canvas     = self.matrix.CreateFrameCanvas()
        frame_time = 1.0 / self.cfg.TARGET_FPS
        t_start    = time.monotonic()

        while not self._stop.is_set():
            t     = time.monotonic() - t_start
            frame = time.monotonic()

            arr = effects[self._current[0]].render(t)
            img = Image.fromarray(arr, 'RGB')
            canvas.SetImage(img)
            canvas = self.matrix.SwapOnVSync(canvas)

            elapsed = time.monotonic() - frame
            sleep   = frame_time - elapsed
            if sleep > 0:
                time.sleep(sleep)

        for e in effects:
            e.cleanup()
        self.matrix.Clear()
        print('[Standalone] stopped')

# ── main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    group  = parser.add_mutually_exclusive_group()
    group.add_argument('--artnet',     action='store_true')
    group.add_argument('--standalone', action='store_true')
    args = parser.parse_args()

    print('Initialising LED matrix...')
    matrix, cfg = build_matrix()

    artnet     = ArtNetMode(matrix, cfg)
    standalone = StandaloneMode(matrix, cfg)
    active     = [None]   # 'artnet' or 'standalone'

    def switch_to(mode, effect=0):
        if active[0] == 'artnet':
            artnet.stop()
        elif active[0] == 'standalone':
            standalone.stop()
        time.sleep(0.2)

        if mode == 'artnet':
            artnet.start()
            active[0] = 'artnet'
        else:
            standalone.start(effect)
            active[0] = 'standalone'

    # ── auto-detect or forced start ──
    if args.artnet:
        switch_to('artnet')
    elif args.standalone:
        switch_to('standalone')
    else:
        print('Auto-detecting ArtNet signal (5 s)...')
        if artnet.probe(timeout=5.0):
            print('[Auto] ArtNet detected — starting ArtNet mode')
            switch_to('artnet')
        else:
            print('[Auto] No ArtNet signal — starting standalone mode')
            switch_to('standalone')

    # ── keyboard loop ──
    print()
    print('Commands: a=ArtNet  s=standalone  0-4=effect  q=quit')
    try:
        while True:
            line = input().strip().lower()
            if line == 'q':
                break
            elif line == 'a':
                switch_to('artnet')
                print('Commands: a=ArtNet  s=standalone  0-4=effect  q=quit')
            elif line == 's':
                switch_to('standalone')
                print('Commands: a=ArtNet  s=standalone  0-4=effect  q=quit')
            elif active[0] == 'standalone' and line in StandaloneMode.EFFECTS:
                standalone.set_effect(line)
    except EOFError:
        pass
    finally:
        if active[0] == 'artnet':
            artnet.stop()
        elif active[0] == 'standalone':
            standalone.stop()
        time.sleep(0.3)
        matrix.Clear()
        print('Bye.')


if __name__ == '__main__':
    main()
