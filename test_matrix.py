from rgbmatrix import RGBMatrix, RGBMatrixOptions
import sys, numpy as np
sys.path.insert(0, 'pi_effects')
import config as cfg
from PIL import Image

# Test different ROW_ADDRESS_TYPE values
for row_addr_type in [0, 1, 2, 3]:
    print(f"\nTesting ROW_ADDRESS_TYPE = {row_addr_type}")
    opts = RGBMatrixOptions()
    opts.rows = cfg.ROWS
    opts.cols = cfg.COLS
    opts.hardware_mapping = cfg.HARDWARE_MAPPING
    opts.row_address_type = row_addr_type
    opts.gpio_slowdown = cfg.GPIO_SLOWDOWN
    opts.drop_privileges = False

    matrix = RGBMatrix(options=opts)
    canvas = matrix.CreateFrameCanvas()
    arr = np.full((64, 64, 3), [255, 0, 0], dtype='uint8')
    canvas.SetImage(Image.fromarray(arr, 'RGB'))
    matrix.SwapOnVSync(canvas)

    input('Press Enter for next type...')
    matrix.Clear()

print("Done")
