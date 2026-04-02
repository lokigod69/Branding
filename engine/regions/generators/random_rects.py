"""
Random rectangles region generator — places randomized overlapping
rectangles to create fragmented, collage-like partitions.
"""
import numpy as np
from engine.regions.base import RegionGenerator, RegionMap


class RandomRectsGenerator(RegionGenerator):
    name = "Random Rectangles"
    description = "Overlapping random rectangles for fragmented partitions"

    def generate(self, width, height, params):
        n_rects = max(params.get("n_rects", 8), 1)
        min_size = params.get("min_size", 0.1)
        max_size = params.get("max_size", 0.4)
        seed = params.get("seed", 42)

        rng = np.random.default_rng(seed)
        # Start with region 0 as background
        labels = np.zeros((height, width), dtype=np.int32)
        centroids = [(width // 2, height // 2)]

        for i in range(1, n_rects + 1):
            rw = int(rng.uniform(min_size, max_size) * width)
            rh = int(rng.uniform(min_size, max_size) * height)
            rx = int(rng.uniform(0, width - rw))
            ry = int(rng.uniform(0, height - rh))

            rw = max(rw, 4)
            rh = max(rh, 4)
            rx = max(0, min(rx, width - rw))
            ry = max(0, min(ry, height - rh))

            labels[ry:ry + rh, rx:rx + rw] = i
            centroids.append((rx + rw // 2, ry + rh // 2))

        return RegionMap(labels, n_rects + 1, {"centroids": centroids})


GENERATOR = RandomRectsGenerator()
