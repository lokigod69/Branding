"""
Voronoi region generator — creates organic cell-like partitions using
random seed points and nearest-neighbor assignment.
"""
import numpy as np
from engine.regions.base import RegionGenerator, RegionMap


class VoronoiGenerator(RegionGenerator):
    name = "Voronoi"
    description = "Organic cell-like partitions from random seed points"

    def generate(self, width, height, params):
        n_cells = max(params.get("n_cells", 12), 2)
        seed = params.get("seed", 42)
        regularity = params.get("regularity", 0.0)

        rng = np.random.default_rng(seed)

        if regularity > 0:
            # Semi-regular: start from grid and jitter
            cols = max(int(np.sqrt(n_cells * width / height)), 1)
            rows = max(int(n_cells / cols), 1)
            n_cells = rows * cols
            points = []
            for r in range(rows):
                for c in range(cols):
                    cx = (c + 0.5) / cols * width
                    cy = (r + 0.5) / rows * height
                    jitter_x = (1 - regularity) * (width / cols * 0.4)
                    jitter_y = (1 - regularity) * (height / rows * 0.4)
                    cx += rng.uniform(-jitter_x, jitter_x)
                    cy += rng.uniform(-jitter_y, jitter_y)
                    points.append((cx, cy))
            points = np.array(points, dtype=np.float32)
        else:
            # Pure random
            px = rng.uniform(0, width, n_cells).astype(np.float32)
            py = rng.uniform(0, height, n_cells).astype(np.float32)
            points = np.stack([px, py], axis=1)

        # Assign each pixel to nearest seed — vectorized via broadcasting
        yy, xx = np.mgrid[0:height, 0:width]
        xx = xx.astype(np.float32)
        yy = yy.astype(np.float32)

        # Chunk processing for memory efficiency on large images
        labels = np.zeros((height, width), dtype=np.int32)
        chunk_size = max(height // 4, 64)

        for y_start in range(0, height, chunk_size):
            y_end = min(y_start + chunk_size, height)
            chunk_h = y_end - y_start
            # (chunk_h, W, 1) - (1, 1, N)
            dx = xx[y_start:y_end, :, np.newaxis] - points[np.newaxis, np.newaxis, :, 0]
            dy = yy[y_start:y_end, :, np.newaxis] - points[np.newaxis, np.newaxis, :, 1]
            dist_sq = dx * dx + dy * dy
            labels[y_start:y_end, :] = np.argmin(dist_sq, axis=2)

        actual_n = len(points)
        centroids = [(int(p[0]), int(p[1])) for p in points]
        return RegionMap(labels, actual_n, {"centroids": centroids})


GENERATOR = VoronoiGenerator()
