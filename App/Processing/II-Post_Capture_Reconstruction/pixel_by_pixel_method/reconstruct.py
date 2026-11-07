"""
reconstruct.py (pixel by pixel method)
--------------------------------------
Recover the all-in-focus image from the scene pair and the depth map that
I-Depth_Estimation/pixel_by_pixel_method/estimate_depth.py saved (Zhou, Lin &
Nayar 2009; algorithm in dfd.py).

The script deconvolves the pair at every calibrated depth with dfd.estimate,
the same joint Wiener deconvolution the depth search ran. Each pixel then
takes its value from the deconvolution at its own depth (dfd.compose).

The script reads the scene and settings from the depth run's settings.json,
so both halves work on the same pair. It runs the depth script first when no
depth run exists yet.

Output (Out/Post_Capture_Reconstruction/pixel_by_pixel_method/):
    all_in_focus.png    deconvolved sharp image

Run from this folder, after I-Depth_Estimation/calibrate.py:
    python reconstruct.py
"""

import json
import subprocess
import sys
from pathlib import Path

DEPTH_FOLDER = Path(__file__).resolve().parents[2] / "I-Depth_Estimation"
# The shared code (common.py and dfd.py) sits in I-Depth_Estimation.
sys.path.insert(0, str(DEPTH_FOLDER))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import dfd
from common import (CALIBRATION_FILE, CAPTURES, MASTER_DARK_FILE, OUT_DEPTH,
                    OUT_RECONSTRUCTION, REPO, SCENE_NAME, downsample,
                    load_green, to_display)

DEPTH_SCRIPT = DEPTH_FOLDER / "pixel_by_pixel_method" / "estimate_depth.py"
DEPTH_RUN = OUT_DEPTH / "pixel_by_pixel_method"
OUTPUT = OUT_RECONSTRUCTION / "pixel_by_pixel_method"


def main():
    if not all((DEPTH_RUN / f).exists() for f in ("depth_mm.npy", "settings.json")):
        print("No pixel by pixel depth map yet. Running its depth script first.")
        subprocess.run([sys.executable, str(DEPTH_SCRIPT)], check=True)
    settings = json.loads((DEPTH_RUN / "settings.json").read_text())
    depth_mm = np.load(DEPTH_RUN / "depth_mm.npy")
    factor = settings["downsample"]

    with np.load(CALIBRATION_FILE) as cal:
        depths = cal["depths_mm"]
        kernels = dfd.prepare_kernels(cal["kernels"], factor)
    dark = np.load(MASTER_DARK_FILE)
    paths = [CAPTURES / settings["scene_dir"] / SCENE_NAME.format(mask=m) for m in (1, 2)]
    I1, I2 = (downsample(load_green(p)[0] - dark, factor) for p in paths)
    if depth_mm.shape != I1.shape:
        sys.exit(f"The depth map is {depth_mm.shape} px but the scene is {I1.shape} px. "
                 f"Rerun the depth script.")

    # Turn each pixel's depth in mm back into the index of that depth's PSF pair.
    best = np.argmin(np.abs(depth_mm[None] - depths[:, None, None]), axis=0)

    _, latents = dfd.estimate(I1, I2, kernels, settings["lam"], settings["window"])
    sharp = dfd.compose(latents, best)

    OUTPUT.mkdir(parents=True, exist_ok=True)
    plt.imsave(OUTPUT / "all_in_focus.png", to_display(np.clip(sharp, 0, None)), cmap="gray")
    print(f"Saved {(OUTPUT / 'all_in_focus.png').relative_to(REPO)}")


if __name__ == "__main__":
    main()
