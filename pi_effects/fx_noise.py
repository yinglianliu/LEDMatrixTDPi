"""Animated generative noise with hue cycling."""

import numpy as np
import time


def _hsv_to_rgb(h, s, v):
    """Vectorized HSV → RGB, all inputs are (H, W) arrays in range [0, 1]."""
    h6 = h * 6.0
    i  = h6.astype(np.int32) % 6
    f  = h6 - np.floor(h6)
    p  = v * (1.0 - s)
    q  = v * (1.0 - s * f)
    t  = v * (1.0 - s * (1.0 - f))

    r = np.select([i==0, i==1, i==2, i==3, i==4, i==5], [v, q, p, p, t, v])
    g = np.select([i==0, i==1, i==2, i==3, i==4, i==5], [t, v, v, q, p, p])
    b = np.select([i==0, i==1, i==2, i==3, i==4, i==5], [p, p, t, v, v, q])

    rgb = np.stack([r, g, b], axis=-1)
    return (rgb * 255).clip(0, 255).astype(np.uint8)


class NoiseEffect:
    def __init__(self, W, H):
        self.W = W
        self.H = H
        x = np.linspace(0, 2 * np.pi, W)
        y = np.linspace(0, 2 * np.pi, H)
        self.xx, self.yy = np.meshgrid(x, y)

    def render(self, t: float) -> np.ndarray:
        xx, yy = self.xx, self.yy

        # Layered sine waves for organic feel
        noise = (np.sin(xx * 1.0 + t * 0.71) * np.cos(yy * 0.8 - t * 0.53) +
                 np.sin(xx * 1.7 - t * 0.43) * np.sin(yy * 1.5 + t * 0.67) +
                 np.cos((xx + yy) * 0.9 + t * 0.31)) / 3.0

        brightness = (noise + 1.0) / 2.0                       # 0..1
        hue        = (xx / (2 * np.pi) * 0.6 + t * 0.08) % 1  # slow drift
        saturation = np.ones_like(hue)

        return _hsv_to_rgb(hue, saturation, brightness)

    def cleanup(self):
        pass
