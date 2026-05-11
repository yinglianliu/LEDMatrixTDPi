"""Test: solid red in a loop (same pattern as run.py) for 5 seconds."""
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

print(f"Array shape: {arr.shape}, Image size: {img.size}")
print("Running solid red loop for 5 seconds...")

end = time.monotonic() + 5.0
count = 0
while time.monotonic() < end:
    canvas.SetImage(img)
    canvas = matrix.SwapOnVSync(canvas)
    count += 1

print(f"Rendered {count} frames")
matrix.Clear()
print("Done — how many rows lit up?")
