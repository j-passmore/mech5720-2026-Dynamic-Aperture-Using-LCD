"""Find the light seeds on the mean frame of each panel position. Writes seeds_auto.json beside this script.

Run after load_all.py. A seed is a blob centre and radius in half-size pixels, found by
Laplacian-of-Gaussian detection on the downscaled mean luminance inside a loose region above the cake.
final_analysis.py then applies the stricter polygons in roi_polygons.json, the size rule and the
contrast rule. The committed seeds_auto.json is what this script wrote, so the step can be skipped.

Run from this folder:
  python3 seeds.py
  python3 seeds.py --out ../../../../Out/Custom_Bokeh/ncc
"""
import json
from pathlib import Path

import cv2
import numpy as np
from skimage.feature import blob_log

from bokeh_ncc import HERE, STAGES, parse_args

DS = 4


def loose_roi(h, w):
    k = w / 1800.0
    poly = np.array([(0, 0), (1800, 0), (1800, 880), (1250, 820), (1250, 650), (800, 640), (800, 560), (0, 560)]) * k
    m = np.zeros((h, w), np.uint8)
    cv2.fillPoly(m, [poly.astype(np.int32)], 1)
    return m.astype(bool)


def main():
    a = parse_args(__doc__)
    out = {}
    for st in STAGES:
        m = np.load(Path(a.out) / f"mean_{st}.npy")
        h, w = m.shape
        s = cv2.resize(m, (w // DS, h // DS), interpolation=cv2.INTER_AREA)
        s = s / np.percentile(s, 99.5)
        roi = cv2.resize(loose_roi(h, w).astype(np.uint8), (w // DS, h // DS), interpolation=cv2.INTER_NEAREST).astype(bool)
        blobs = blob_log(np.clip(s, 0, 1), min_sigma=15, max_sigma=26, num_sigma=8, threshold=0.025, overlap=0.3)
        out[st] = [(int(x * DS), int(y * DS), int(sg * np.sqrt(2) * DS)) for (y, x, sg) in blobs if roi[int(y), int(x)]]
    with open(HERE / "seeds_auto.json", "w") as f:
        json.dump(out, f)
    print({k: len(v) for k, v in out.items()}, "seeds, written to", HERE / "seeds_auto.json")


if __name__ == "__main__":
    main()
