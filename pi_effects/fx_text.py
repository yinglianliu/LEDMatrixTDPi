"""Scrolling text marquee — right to left, loops seamlessly.

Requires:  python3-pillow  (sudo apt-get install python3-pillow)
Chinese:   set font to a CJK font, e.g. /usr/share/fonts/truetype/wqy/wqy-zenhei.ttc
"""

import numpy as np
import os
from PIL import Image, ImageDraw, ImageFont


def _find_font(font_name: str, size: int) -> ImageFont.FreeTypeFont:
    """Try to load the requested font, fall back to default."""
    search_dirs = [
        '/usr/share/fonts/truetype/dejavu/',
        '/usr/share/fonts/truetype/liberation/',
        '/usr/share/fonts/truetype/wqy/',
        '/usr/share/fonts/',
        os.path.dirname(__file__),
    ]
    for d in search_dirs:
        path = os.path.join(d, font_name)
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    print(f'[fx_text] font "{font_name}" not found, using default')
    return ImageFont.load_default()


def _render_text_strip(text: str, font: ImageFont.FreeTypeFont,
                        color: tuple, H: int) -> np.ndarray:
    """Render text onto a wide PIL image, return as (H, W, 3) uint8 numpy array."""
    # Measure text size
    dummy = Image.new('RGB', (1, 1))
    draw  = ImageDraw.Draw(dummy)
    bbox  = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0] + 4
    text_h = bbox[3] - bbox[1] + 4

    # Create canvas tall enough for the matrix
    img  = Image.new('RGB', (text_w, H), (0, 0, 0))
    draw = ImageDraw.Draw(img)
    y_off = (H - text_h) // 2 - bbox[1]  # vertically centre
    draw.text((2, y_off), text, font=font, fill=color)

    return np.array(img, dtype=np.uint8)


class TextEffect:
    def __init__(self, W: int, H: int, cfg):
        self.W   = W
        self.H   = H
        self._pos = 0.0  # scroll position (float pixels)

        font = _find_font(cfg.TEXT_FONT, cfg.TEXT_FONT_SIZE)

        # Render text strip (white so colour can be controlled separately)
        self._strip = _render_text_strip(cfg.TEXT_MESSAGE, font, (255, 255, 255), H)
        self._strip_w = self._strip.shape[1]
        self._speed   = cfg.TEXT_SPEED

        # Build hue-cycle lookup (updates each render via _hue_t)
        self._hue_t = 0.0

    def _hue_tint(self, t: float) -> tuple:
        """Cycle through rainbow colours."""
        h = (t * 40 / 360) % 1.0
        h6 = h * 6
        i = int(h6) % 6
        f = h6 - int(h6)
        lut = [
            (1, f, 0), (1-f, 1, 0), (0, 1, f),
            (0, 1-f, 1), (f, 0, 1), (1, 0, 1-f),
        ]
        return tuple(int(c * 255) for c in lut[i])

    def render(self, t: float) -> np.ndarray:
        W, H = self.W, self.H
        strip_w = self._strip_w
        total   = W + strip_w        # full cycle in pixels
        frame   = int(self._pos)

        arr = np.zeros((H, W, 3), dtype=np.uint8)

        for x_out in range(W):
            src_x = x_out + frame - W   # src_x<0: text hasn't entered yet
            if 0 <= src_x < strip_w:
                arr[:, x_out] = self._strip[:H, src_x]

        # Apply hue tint to white pixels
        r, g, b = self._hue_tint(t)
        mask = arr[:, :, 0] > 10   # non-black pixels
        arr[mask, 0] = (arr[mask, 0].astype(np.uint16) * r // 255).astype(np.uint8)
        arr[mask, 1] = (arr[mask, 1].astype(np.uint16) * g // 255).astype(np.uint8)
        arr[mask, 2] = (arr[mask, 2].astype(np.uint16) * b // 255).astype(np.uint8)

        self._pos = (self._pos + self._speed) % total
        return arr

    def cleanup(self):
        pass
