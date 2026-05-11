import sys, time
sys.path.insert(0, 'pi_effects')
import config as cfg
from rgbmatrix import RGBMatrix, RGBMatrixOptions

opts = RGBMatrixOptions()
opts.rows                     = cfg.ROWS
opts.cols                     = cfg.COLS
opts.hardware_mapping         = cfg.HARDWARE_MAPPING
opts.row_address_type         = cfg.ROW_ADDRESS_TYPE
opts.gpio_slowdown            = cfg.GPIO_SLOWDOWN
opts.drop_privileges          = False
opts.disable_hardware_pulsing = True

matrix = RGBMatrix(options=opts)

# Test A: canvas.Fill in a loop (no PIL)
print("Test A: canvas.Fill(255,0,0) loop 5s...")
canvas = matrix.CreateFrameCanvas()
end = time.monotonic() + 5.0
while time.monotonic() < end:
    canvas.Fill(255, 0, 0)
    canvas = matrix.SwapOnVSync(canvas)
matrix.Clear()
input("Test A done — rows lit? Enter for Test B...")

# Test B: matrix.Fill directly (no canvas)
print("Test B: matrix.Fill(255,0,0) + input...")
matrix.Fill(255, 0, 0)
input("Test B done — rows lit? Enter to quit...")
matrix.Clear()
