"""Metaball effect — 5 coloured blobs that merge smoothly."""

import numpy as np


class MetaballEffect:
    def __init__(self, W, H):
        self.W = W
        self.H = H
        x = np.linspace(0, 1, W)
        y = np.linspace(0, 1, H)
        self.xx, self.yy = np.meshgrid(x, y)

        # Ball definitions: (speed_x, speed_y, radius, phase_x, phase_y, color)
        self.balls = [
            (0.71, 0.53, 0.13, 0.0,  0.0,  (0.0,  0.6, 1.0)),   # cyan-blue
            (1.13, 0.79, 0.11, 2.1,  1.0,  (1.0,  0.15, 0.5)),   # pink
            (0.47, 1.23, 0.10, 4.2,  2.0,  (0.1,  1.0,  0.3)),   # green
            (0.89, 0.61, 0.12, 1.5,  3.1,  (1.0,  0.6,  0.0)),   # orange
            (0.31, 1.41, 0.09, 3.0,  0.5,  (0.7,  0.1,  1.0)),   # purple
        ]

    def render(self, t: float) -> np.ndarray:
        xx, yy = self.xx, self.yy
        field  = np.zeros((self.H, self.W), dtype=np.float32)
        w_r    = np.zeros((self.H, self.W, 3), dtype=np.float32)
        w_sum  = np.zeros((self.H, self.W), dtype=np.float32)

        for (sx, sy, r, px, py, col) in self.balls:
            bx = 0.5 + 0.38 * np.cos(t * sx + px)
            by = 0.5 + 0.38 * np.sin(t * sy + py)
            d2 = (xx - bx) ** 2 + (yy - by) ** 2 + 1e-6
            w  = r * r / d2
            field += w
            for c in range(3):
                w_r[..., c] += w * col[c]
            w_sum += w

        # Isosurface threshold
        threshold  = 1.0
        interior   = (field > threshold).astype(np.float32)
        edge_glow  = np.exp(-np.abs(field - threshold) * 4.0) * 0.8

        # Normalised colour
        w_sum  = np.maximum(w_sum, 1e-6)[..., np.newaxis]
        color  = w_r / w_sum                                    # 0..1 per channel

        # Slow global hue drift
        drift    = t * 0.04
        r, g, b  = color[..., 0], color[..., 1], color[..., 2]
        drifted  = np.stack([
            r * (1 - 0.25) + g * 0.25,
            g * (1 - 0.25) + b * 0.25,
            b * (1 - 0.25) + r * 0.25,
        ], axis=-1)

        result = drifted * interior[..., np.newaxis] + drifted * edge_glow[..., np.newaxis]
        return (result.clip(0, 1) * 255).astype(np.uint8)

    def cleanup(self):
        pass
