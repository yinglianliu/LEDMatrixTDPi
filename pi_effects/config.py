# Hardware and runtime configuration for Pi Zero 2W + Adafruit RGB Matrix Bonnet
# Waveshare P2 64x64 HUB75E panel

ROWS               = 64
COLS               = 64
CHAIN_LENGTH       = 1
PARALLEL           = 1
HARDWARE_MAPPING   = 'adafruit-hat'
ROW_ADDRESS_TYPE   = 0    # Waveshare P2 64x64 uses type 0 (not 1 despite HUB75E)
GPIO_SLOWDOWN      = 4    # Pi Zero 2W: 3-4
PWM_BITS           = 11
DROP_PRIVILEGES    = False
NO_HARDWARE_PULSE  = True  # avoids conflict with snd_bcm2835 on Pi OS Bookworm+

TARGET_FPS         = 30   # Pi Zero 2W comfortable ceiling

# Text effect
TEXT_MESSAGE       = 'HAPPY MOTHERS DAY'
TEXT_FONT          = 'DejaVuSans-Bold.ttf'   # usually at /usr/share/fonts/truetype/dejavu/
TEXT_FONT_SIZE     = 14
TEXT_SPEED         = 1    # pixels per frame

# Audio effect
AUDIO_DEVICE       = None  # None = system default; set to int index if needed
AUDIO_SAMPLE_RATE  = 44100
AUDIO_BLOCK_SIZE   = 1024
N_BARS             = 16
F_MIN              = 60.0
F_MAX              = 8000.0
BASE_GAIN          = 10.0
FREQ_EXP           = 0.7
ARCTAN_K           = 0.5
ATTACK             = 0.5
RELEASE            = 0.93
