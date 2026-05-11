"""Test A: don't capture SwapOnVSync return (draw to same canvas each frame)"""
import sys, time, numpy as np
sys.path.insert(0, 'pi_effects')
import config as cfg
from rgbmatrix import RGBMatrix, RGBMatrixOptions
from PIL import Image

opts = RGBMatrixOptions()
opts.rows             = cfg.ROWS
opts.cols             = cfg.COLS
opts.hardware_mapping = cfg.HARDWARE_MAPPING
opts.row_address_type = cfg.ROW_ADDRESS_TYPE
opts.gpio_slowdown    = cfg.GPIO_SLOWDOWN
opts.drop_privileges  = False

matrix = RGBMatrix(options=opts)
canvas = matrix.CreateFrameCanvas()

arr = np.full((cfg.ROWS, cfg.COLS, 3), [255, 0, 0], dtype='uint8')
img = Image.fromarray(arr, 'RGB')

print("Test A: NOT capturing SwapOnVSync return, 5 seconds...")
end = time.monotonic() + 5.0
while time.monotonic() < end:
    canvas.SetImage(img)
    matrix.SwapOnVSync(canvas)   # return NOT captured

print("Test A done. How many rows?")
matrix.Clear()
time.sleep(1)

# Test B: using DrawFrame instead
canvas2 = matrix.CreateFrameCanvas()
print("Test B: draw once, then wait...")
canvas2.SetImage(img)
matrix.SwapOnVSync(canvas2)
input("Test B: press Enter to quit...")
matrix.Clear()
