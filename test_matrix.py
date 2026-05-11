"""Test different multiplexing values to find which shows all 64 rows."""
import sys, time
sys.path.insert(0, 'pi_effects')
import config as cfg
from rgbmatrix import RGBMatrix, RGBMatrixOptions

for mux in range(9):
    print(f"\nMultiplexing = {mux}  (press Enter to advance, q to quit)")
    try:
        opts = RGBMatrixOptions()
        opts.rows                     = cfg.ROWS
        opts.cols                     = cfg.COLS
        opts.hardware_mapping         = cfg.HARDWARE_MAPPING
        opts.row_address_type         = cfg.ROW_ADDRESS_TYPE
        opts.gpio_slowdown            = cfg.GPIO_SLOWDOWN
        opts.drop_privileges          = False
        opts.disable_hardware_pulsing = True
        opts.multiplexing             = mux

        matrix = RGBMatrix(options=opts)
        canvas = matrix.CreateFrameCanvas()
        canvas.Fill(255, 0, 0)
        matrix.SwapOnVSync(canvas)

        line = input()
        matrix.Clear()
        if line.strip().lower() == 'q':
            break
    except Exception as e:
        print(f"  Error: {e}")
        input("Press Enter to continue...")

print("Done")
