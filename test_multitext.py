import asyncio
import numpy as np
from engine.io_handler import ImageMeta
from engine.pipeline import execute_pipeline
from pathlib import Path
import cv2

async def main():
    # create generic pure black 500x500 image
    image = np.zeros((500, 500, 3), dtype=np.float32)
    meta = ImageMeta(original_path="dummy", format="JPEG", icc_profile=None, bit_depth=8, has_alpha=False, original_size=(500, 500))
    
    stages = [{"type": "signing", "enabled": True}]
    signing_configs = [
        {
            "text": "LAZART",
            "layout": {"size_rel_width": 0.5, "position": {"x_pct": 0.2, "y_pct": 0.2}},
            "effect": {"type": "difference", "strength": 1.0}
        },
        {
            "text": "LAZART",
            "layout": {"size_rel_width": 0.5, "position": {"x_pct": 0.8, "y_pct": 0.8}},
            "effect": {"type": "difference", "strength": 1.0}
        }
    ]
    
    result = execute_pipeline(image, meta, stages, signing_configs)
    
    # Save output
    out_path = "test_multitext.png"
    output_8bit = (result * 255.0).clip(0, 255).astype(np.uint8)
    cv2.imwrite(out_path, output_8bit)
    print(f"Saved to {out_path} - visually inspect if both texts exist.")

if __name__ == "__main__":
    asyncio.run(main())
