"""
ArtNet receiver for Waveshare P2 64x64 LED Matrix
Hardware: Raspberry Pi Zero 2W + Adafruit RGB Matrix Bonnet

Setup:
  1. Solder Bonnet E-jumper: bridge middle pad to '8' (back of board)
  2. Install library:
       git clone https://github.com/hzeller/rpi-rgb-led-matrix.git
       cd rpi-rgb-led-matrix
       make build-python PYTHON=$(which python3)
       sudo make install-python PYTHON=$(which python3)
  3. Disable audio: add 'dtparam=audio=off' to /boot/firmware/config.txt
  4. Run: sudo python3 artnet_matrix.py

TouchDesigner side:
  - Set ARTNET_IP in artnet_sender DAT to this Pi's IP address
  - The 64x64 image is packed as 24 ArtNet universes (512 bytes each)
"""

import socket
import threading
from rgbmatrix import RGBMatrix, RGBMatrixOptions

# ── Matrix configuration ────────────────────────────────────────────────────
MATRIX_ROWS = 64
MATRIX_COLS = 64
TOTAL_PIXELS = MATRIX_ROWS * MATRIX_COLS  # 4096

options = RGBMatrixOptions()
options.rows                = MATRIX_ROWS
options.cols                = MATRIX_COLS
options.chain_length        = 1
options.parallel            = 1
options.hardware_mapping    = 'adafruit-hat'
options.row_address_type    = 1     # E address line (required for 64-row panels)
options.gpio_slowdown       = 4     # Pi Zero 2W: use 3-4
options.pwm_bits            = 11
options.drop_privileges     = False

matrix = RGBMatrix(options=options)
canvas = matrix.CreateFrameCanvas()

# ── ArtNet receiver ─────────────────────────────────────────────────────────
ARTNET_PORT   = 6454
UNIVERSE_SIZE = 512
NUM_UNIVERSES = (TOTAL_PIXELS * 3 + UNIVERSE_SIZE - 1) // UNIVERSE_SIZE  # 24

pixel_buffer = bytearray(TOTAL_PIXELS * 3)
buffer_lock  = threading.Lock()
dirty        = threading.Event()


def parse_artnet(data: bytes) -> None:
    if len(data) < 18 or data[0:8] != b'Art-Net\x00':
        return
    if (data[8] | (data[9] << 8)) != 0x5000:   # opcode ArtDmx
        return
    if ((data[10] << 8) | data[11]) < 14:       # protocol version
        return

    universe = data[14] & 0x0F
    net      = data[15]
    length   = (data[16] << 8) | data[17]
    payload  = data[18:18 + length]

    uni_global = net * 16 + universe
    if uni_global >= NUM_UNIVERSES:
        return

    offset = uni_global * UNIVERSE_SIZE
    end    = min(offset + length, len(pixel_buffer))
    with buffer_lock:
        pixel_buffer[offset:end] = payload[:end - offset]
    dirty.set()


def receiver_thread() -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('', ARTNET_PORT))
    print(f'Listening for ArtNet on UDP:{ARTNET_PORT}')
    while True:
        try:
            data, _ = sock.recvfrom(600)
            parse_artnet(data)
        except Exception as e:
            print(f'Receiver error: {e}')


# ── Render loop ─────────────────────────────────────────────────────────────
def render_loop() -> None:
    global canvas
    print('Render loop started')
    while True:
        dirty.wait()
        dirty.clear()
        with buffer_lock:
            buf = bytes(pixel_buffer)

        for i in range(TOTAL_PIXELS):
            x = i % MATRIX_COLS
            y = i // MATRIX_COLS
            canvas.SetPixel(x, y, buf[i * 3], buf[i * 3 + 1], buf[i * 3 + 2])

        canvas = matrix.SwapOnVSync(canvas)


# ── Entry point ─────────────────────────────────────────────────────────────
if __name__ == '__main__':
    t = threading.Thread(target=receiver_thread, daemon=True)
    t.start()
    render_loop()
