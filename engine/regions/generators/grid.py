"""Grid region generator — divides image into NxM rectangles."""
import numpy as np
from engine.regions.base import RegionGenerator, RegionMap


class GridGenerator(RegionGenerator):
    name = "Grid"
    description = "Divide image into NxM rectangular cells"

    def generate(self, width, height, params):
        cols = max(params.get("cols", 4), 1)
        rows = max(params.get("rows", 4), 1)

        labels = np.zeros((height, width), dtype=np.int32)
        cell_h = height / rows
        cell_w = width / cols

        for r in range(rows):
            for c in range(cols):
                y0 = int(r * cell_h)
                y1 = int((r + 1) * cell_h)
                x0 = int(c * cell_w)
                x1 = int((c + 1) * cell_w)
                labels[y0:y1, x0:x1] = r * cols + c

        n = rows * cols
        metadata = {
            "rows": rows, "cols": cols,
            "centroids": [
                (int((c + 0.5) * cell_w), int((r + 0.5) * cell_h))
                for r in range(rows) for c in range(cols)
            ],
        }
        return RegionMap(labels, n, metadata)


GENERATOR = GridGenerator()
