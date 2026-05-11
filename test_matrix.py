"""Definitive test: single SwapOnVSync with sleep (no loop)."""
import sys, time, numpy as np
sys.path.insert(0, 'pi_effects')
import config as cfg
from rgbmatrix import RGBMatrix, RGBMatrixOptions
from PIL import Image

opts = RGBMatrixOptions()
opts.rows                     = cfg.ROWS
opts.cols                     = cfg.COLS
opts.hardware_mapping         = cfg.HARDWARE_MAPPING
opts.row_address_type         = cfg.ROW_ADDRESS_TYPE
opts.gpio_slowdown            = cfg.GPIO_SLOWDOWN
opts.drop_privileges          = False
opts.disable_hardware_pulsing = True

matrix = RGBMatrix(options=opts)

def show(r, g, b, label, seconds):
    canvas = matrix.CreateFrameCanvas()
    canvas.Fill(r, g, b)
    matrix.SwapOnVSync(canvas)
    print(f"{label} — showing for {seconds}s, count the rows NOW")
    time.sleep(seconds)
    matrix.Clear()
    time.sleep(0.5)

show(255,   0,   0, "RED",   5)
show(  0, 255,   0, "GREEN", 5)
show(  0,   0, 255, "BLUE",  5)

print("Done — all tests complete")
