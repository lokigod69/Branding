"""
Radial region generator — creates concentric rings or pie-slice sectors
centered at a focal point.
"""
import numpy as np
from engine.regions.base import RegionGenerator, RegionMap


class RadialGenerator(RegionGenerator):
    name = "Radial"
    description = "Concentric rings and/or pie slices from a focal point"

    def generate(self, width, height, params):
        rings = max(params.get("rings", 4), 1)
        sectors = max(params.get("sectors", 1), 1)
        center_x = params.get("center_x", 0.5)
        center_y = params.get("center_y", 0.5)

        cx = int(center_x * width)
        cy = int(center_y * height)

        yy, xx = np.mgrid[0:height, 0:width]
        dx = (xx - cx).astype(np.float32)
        dy = (yy - cy).astype(np.float32)

        # Distance from center, normalized to [0, 1]
        dist = np.sqrt(dx * dx + dy * dy)
        max_dist = np.sqrt(max(cx, width - cx) ** 2 + max(cy, height - cy) ** 2)
        if max_dist > 0:
            dist_norm = dist / max_dist
        else:
            dist_norm = np.zeros_like(dist)

        # Ring assignment
        ring_idx = np.clip((dist_norm * rings).astype(np.int32), 0, rings - 1)

        if sectors > 1:
            # Angle from center
            angle = np.arctan2(dy, dx)  # [-pi, pi]
            angle_norm = (angle + np.pi) / (2 * np.pi)  # [0, 1)
            sector_idx = np.clip((angle_norm * sectors).astype(np.int32), 0, sectors - 1)
            labels = ring_idx * sectors + sector_idx
            n_regions = rings * sectors
        else:
            labels = ring_idx
            n_regions = rings

        return RegionMap(labels.astype(np.int32), n_regions, {
            "center": (cx, cy), "rings": rings, "sectors": sectors,
        })


GENERATOR = RadialGenerator()
