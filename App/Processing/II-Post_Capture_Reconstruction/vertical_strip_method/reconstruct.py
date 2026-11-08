# Reconstruct a sharper image using two RAW captures and a saved depth map.
#
# How to use:
# 1. Run calibrate.py in App/Processing/I-Depth_Estimation/ once.
# 2. Use the same SCENE and DOWNSAMPLE settings as the depth script.
# 3. Run: python reconstruct.py
# 4. The script reads Out/Depth_Estimation/vertical_strip_method/depth_mm.npy.
#    It runs I-Depth_Estimation/vertical_strip_method/estimate_depth.py first
#    when that file is missing.
# 5. The script saves all_in_focus.png and reconstruction_comparison.png, the
#    photo and the sharp image side by side, in
#    Out/Post_Capture_Reconstruction/vertical_strip_method/.

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
from scipy import fft

import dfd
from common import (CAPTURES, CALIBRATION_FILE, MASTER_DARK_FILE, OUT_DEPTH,
                    OUT_RECONSTRUCTION, SCENE_NAME, downsample, load_green,
                    save_comparison, to_display)

SCENE = "Scale_1"
DOWNSAMPLE = 2
LAM = 0.5
RIDGE = 0.003
DEPTH_SCRIPT = DEPTH_FOLDER / "vertical_strip_method" / "estimate_depth.py"
DEPTH_MAP = OUT_DEPTH / "vertical_strip_method" / "depth_mm.npy"
OUTPUT = OUT_RECONSTRUCTION / "vertical_strip_method"


def reconstruct_at_depth(image1, image2, psf1, psf2):
    # Reconstruct one image using the blur kernels at this depth.
    height, width = image1.shape
    scale = max(float(np.mean(np.abs(image1) + np.abs(image2)) / 2), 1.)
    padding = max(psf1.shape[0], psf2.shape[0]) // 2 + 1
    padded_height = fft.next_fast_len(height + 2 * padding)
    padded_width = fft.next_fast_len(width + 2 * padding, real=True)
    pads = ((padding, padded_height - height - padding),
            (padding, padded_width - width - padding))
    first = np.pad(image1 / scale, pads, mode="reflect")
    second = np.pad(image2 / scale, pads, mode="reflect")
    blur1 = dfd.psf2otf(psf1, (padded_height, padded_width))
    blur2 = dfd.psf2otf(psf2, (padded_height, padded_width))
    frequency = (fft.rfftfreq(padded_width)[None, :]**2 +
                 fft.fftfreq(padded_height)[:, None]**2)
    recovered = (fft.rfft2(first) * blur1.conj() + fft.rfft2(second) * blur2.conj()) / (
        abs(blur1)**2 + abs(blur2)**2 + LAM * frequency + RIDGE)
    image = fft.irfft2(recovered, (padded_height, padded_width))
    return image[padding:padding + height, padding:padding + width] * scale


def main():
    if not DEPTH_MAP.exists():
        print("No vertical strip depth map yet. Running its depth script first.")
        subprocess.run([sys.executable, str(DEPTH_SCRIPT)], check=True)

    with np.load(CALIBRATION_FILE) as data:
        distances = np.asarray(data["depths_mm"], dtype=float)
        psf_pairs = np.asarray(data["kernels"])
    order = np.argsort(distances)
    distances, psf_pairs = distances[order], psf_pairs[order]

    dark = np.load(MASTER_DARK_FILE)
    folder = CAPTURES / SCENE
    images = [load_green(folder / SCENE_NAME.format(mask=mask))[0] - dark
              for mask in (1, 2)]
    image1, image2 = [downsample(image, DOWNSAMPLE) for image in images]
    psfs = dfd.prepare_kernels(psf_pairs, DOWNSAMPLE)
    depth_map = np.load(DEPTH_MAP)

    # Copy each depth's reconstruction into the columns at that depth.
    reconstructed = np.zeros_like(image1, dtype=np.float64)
    for depth, (psf1, psf2) in zip(distances, psfs):
        columns = depth_map[0] == depth
        if np.any(columns):
            image = reconstruct_at_depth(image1, image2, psf1, psf2)
            reconstructed[:, columns] = image[:, columns]

    OUTPUT.mkdir(parents=True, exist_ok=True)
    after = to_display(np.maximum(reconstructed, 0))
    plt.imsave(OUTPUT / "all_in_focus.png", after, cmap="gray")
    save_comparison(to_display(np.maximum(image1, 0)), after,
                    OUTPUT / "reconstruction_comparison.png")


if __name__ == "__main__":
    main()
