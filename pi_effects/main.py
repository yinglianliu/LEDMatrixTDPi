"""
LED Matrix Effects — standalone Pi Zero 2W runner
================================================
Usage:
    sudo python3 main.py             # start with noise effect
    sudo python3 main.py --effect 2  # start with specific effect (0-3)

Keys (press Enter after):
    n / 0   → Noise
    m / 1   → Metaball
    a / 2   → Audio Reactive
    t / 3   → Text
    b / 4   → Audio Metaball (beat-reactive)
    q       → Quit

Install dependencies:
    sudo apt-get install -y python3-pillow
    pip3 install sounddevice          # only for audio effect
"""

import sys
import time
import argparse
import threading
from PIL import Image

import config as cfg

# Import effects
from fx_noise          import NoiseEffect
from fx_metaball       import MetaballEffect
from fx_audio          import AudioEffect
from fx_text           import TextEffect
from fx_audio_metaball import AudioMetaballEffect


def build_matrix():
    from rgbmatrix import RGBMatrix, RGBMatrixOptions
    opts = RGBMatrixOptions()
    opts.rows                = cfg.ROWS
    opts.cols                = cfg.COLS
    opts.chain_length        = cfg.CHAIN_LENGTH
    opts.parallel            = cfg.PARALLEL
    opts.hardware_mapping    = cfg.HARDWARE_MAPPING
    opts.row_address_type    = cfg.ROW_ADDRESS_TYPE
    opts.gpio_slowdown       = cfg.GPIO_SLOWDOWN
    opts.pwm_bits            = cfg.PWM_BITS
    opts.drop_privileges     = cfg.DROP_PRIVILEGES
    return RGBMatrix(options=opts)


def array_to_canvas(canvas, arr):
    """Write (H, W, 3) uint8 numpy array to canvas via PIL SetImage."""
    img = Image.fromarray(arr, 'RGB')
    canvas.SetImage(img)


def input_thread(effect_holder, stop_event):
    """Background thread: read single-key commands from stdin."""
    key_map = {
        'n': 0, '0': 0,
        'm': 1, '1': 1,
        'a': 2, '2': 2,
        't': 3, '3': 3,
        'b': 4, '4': 4,
    }
    while not stop_event.is_set():
        try:
            line = input().strip().lower()
        except EOFError:
            break
        if line == 'q':
            stop_event.set()
            break
        if line in key_map:
            effect_holder[0] = key_map[line]
            print(f'[main] switched to effect {effect_holder[0]}')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--effect', type=int, default=0,
                        help='Starting effect: 0=noise 1=metaball 2=audio 3=text')
    args = parser.parse_args()

    W, H = cfg.COLS, cfg.ROWS

    print('Initialising LED matrix…')
    matrix = build_matrix()
    canvas = matrix.CreateFrameCanvas()

    print('Loading effects…')
    effects = [
        NoiseEffect(W, H),
        MetaballEffect(W, H),
        AudioEffect(W, H, cfg),
        TextEffect(W, H, cfg),
        AudioMetaballEffect(W, H, cfg),
    ]
    names = ['Noise', 'Metaball', 'Audio', 'Text', 'AudioMetaball']

    current = [args.effect]
    stop    = threading.Event()

    kbd = threading.Thread(target=input_thread, args=(current, stop), daemon=True)
    kbd.start()

    print(f'Running. Starting with: {names[current[0]]}')
    print('Commands: n=noise  m=metaball  a=audio  t=text  q=quit')

    frame_time = 1.0 / cfg.TARGET_FPS
    t_start    = time.monotonic()

    try:
        while not stop.is_set():
            t     = time.monotonic() - t_start
            frame = time.monotonic()

            arr = effects[current[0]].render(t)    # (H, W, 3) uint8
            array_to_canvas(canvas, arr)
            canvas = matrix.SwapOnVSync(canvas)

            elapsed = time.monotonic() - frame
            sleep   = frame_time - elapsed
            if sleep > 0:
                time.sleep(sleep)

    except KeyboardInterrupt:
        pass
    finally:
        print('Cleaning up…')
        for e in effects:
            e.cleanup()
        matrix.Clear()


if __name__ == '__main__':
    main()
