"""Solid fill test with ROW_ADDRESS_TYPE=0."""
import sys, time
sys.path.insert(0, 'pi_effects')
import config as cfg
from rgbmatrix import RGBMatrix, RGBMatrixOptions

opts = RGBMatrixOptions()
opts.rows                     = cfg.ROWS
opts.cols                     = cfg.COLS
opts.hardware_mapping         = cfg.HARDWARE_MAPPING
opts.row_address_type         = 0       # testing 0 instead of config value
opts.gpio_slowdown            = cfg.GPIO_SLOWDOWN
opts.drop_privileges          = False
opts.disable_hardware_pulsing = True

matrix = RGBMatrix(options=opts)
canvas = matrix.CreateFrameCanvas()

canvas.Fill(255, 0, 0)
matrix.SwapOnVSync(canvas)
print("Solid RED with row_addr_type=0 — count all lit rows")
input("Press Enter to quit...")
matrix.Clear()
