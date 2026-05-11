import sys, time, numpy as np
sys.path.insert(0, 'pi_effects')
import config as cfg
from rgbmatrix import RGBMatrix, RGBMatrixOptions
from PIL import Image

def make_matrix(limit_hz=0):
    opts = RGBMatrixOptions()
    opts.rows                     = cfg.ROWS
    opts.cols                     = cfg.COLS
    opts.hardware_mapping         = cfg.HARDWARE_MAPPING
    opts.row_address_type         = cfg.ROW_ADDRESS_TYPE
    opts.gpio_slowdown            = cfg.GPIO_SLOWDOWN
    opts.drop_privileges          = False
    opts.disable_hardware_pulsing = True
    if limit_hz > 0:
        opts.limit_refresh_rate_hz = limit_hz
    return RGBMatrix(options=opts)

arr = np.full((cfg.ROWS, cfg.COLS, 3), [255, 0, 0], dtype='uint8')
img = Image.fromarray(arr, 'RGB')

# Test 1: loop with 30fps sleep
print("Test 1: loop + sleep(0.033)...")
m = make_matrix()
c = m.CreateFrameCanvas()
end = time.monotonic() + 5.0
while time.monotonic() < end:
    c.SetImage(img)
    c = m.SwapOnVSync(c)
    time.sleep(0.033)
m.Clear()
input("Test 1 done — rows lit? Press Enter for Test 2...")

# Test 2: limit refresh rate via options
print("Test 2: limit_refresh_rate_hz=100...")
m2 = make_matrix(limit_hz=100)
c2 = m2.CreateFrameCanvas()
end = time.monotonic() + 5.0
while time.monotonic() < end:
    c2.SetImage(img)
    c2 = m2.SwapOnVSync(c2)
m2.Clear()
input("Test 2 done — rows lit? Press Enter to quit...")
print("Done")
