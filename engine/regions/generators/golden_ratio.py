"""
Golden Ratio region generator — partitions image using recursive golden
ratio subdivisions, creating aesthetically balanced regions that respect
natural compositional harmony.
"""
import numpy as np
from engine.regions.base import RegionGenerator, RegionMap

PHI = (1 + np.sqrt(5)) / 2  # ≈ 1.618


class GoldenRatioGenerator(RegionGenerator):
    name = "Golden Ratio"
    description = "Recursive golden-ratio subdivisions for aesthetic partitions"

    def generate(self, width, height, params):
        depth = max(params.get("depth", 4), 1)
        seed = params.get("seed", 42)
        rng = np.random.default_rng(seed)

        labels = np.zeros((height, width), dtype=np.int32)
        region_id = [0]
        centroids = []

        def subdivide(x0, y0, x1, y1, d, horizontal=True):
            w = x1 - x0
            h = y1 - y0
            if d <= 0 or w < 2 or h < 2:
                labels[y0:y1, x0:x1] = region_id[0]
                centroids.append(((x0 + x1) // 2, (y0 + y1) // 2))
                region_id[0] += 1
                return

            if horizontal:
                split = int(x0 + w / PHI)
                # Slight randomization for organic feel
                jitter = int(rng.integers(-w // 20, w // 20 + 1))
                split = max(x0 + 1, min(x1 - 1, split + jitter))
                subdivide(x0, y0, split, y1, d - 1, not horizontal)
                subdivide(split, y0, x1, y1, d - 1, not horizontal)
            else:
                split = int(y0 + h / PHI)
                jitter = int(rng.integers(-h // 20, h // 20 + 1))
                split = max(y0 + 1, min(y1 - 1, split + jitter))
                subdivide(x0, y0, x1, split, d - 1, not horizontal)
                subdivide(x0, split, x1, y1, d - 1, not horizontal)

        start_horiz = width >= height
        subdivide(0, 0, width, height, depth, start_horiz)

        return RegionMap(labels, region_id[0], {
            "depth": depth,
            "centroids": centroids,
        })


GENERATOR = GoldenRatioGenerator()
