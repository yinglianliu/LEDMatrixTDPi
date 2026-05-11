from rgbmatrix import RGBMatrix, RGBMatrixOptions
import sys, numpy as np
sys.path.insert(0, 'pi_effects')
import config as cfg
from PIL import Image

opts = RGBMatrixOptions()
opts.rows = cfg.ROWS
opts.cols = cfg.COLS
opts.hardware_mapping = cfg.HARDWARE_MAPPING
opts.row_address_type = cfg.ROW_ADDRESS_TYPE
opts.gpio_slowdown = cfg.GPIO_SLOWDOWN
opts.drop_privileges = False

matrix = RGBMatrix(options=opts)
canvas = matrix.CreateFrameCanvas()

# Fill entire matrix with solid red
arr = np.full((64, 64, 3), [255, 0, 0], dtype='uint8')
canvas.SetImage(Image.fromarray(arr, 'RGB'))
matrix.SwapOnVSync(canvas)

input('Press Enter to quit...')
matrix.Clear()
