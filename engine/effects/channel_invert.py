"""
channel_invert.py — Single-Channel Inversion Effect

Inverts only R, G, or B channel inside the mask area.
Gives directional color "inversions" (toward red, green, blue).
"""

import numpy as np
from engine.effects.base import BaseEffect


class ChannelInvertEffect(BaseEffect):
    name = "Channel Invert"
    description = "Invert a single color channel for a directional color shift."
    category = "signature"

    def apply(self, image, mask, params):
        channel = params.get("channel", "r").lower()
        channel_map = {"r": 0, "g": 1, "b": 2}
        ch_idx = channel_map.get(channel, 0)

        result = image.copy()
        result[:, :, ch_idx] = 1.0 - result[:, :, ch_idx]

        return result

    def get_default_params(self):
        return {"channel": "r"}


EFFECT = ChannelInvertEffect()
