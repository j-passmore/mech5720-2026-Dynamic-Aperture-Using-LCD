# Reconstruct a sharper image using two RAW captures and a saved depth map.
#
# How to use:
# 1. Copy dfd.py and common.py from another reconstruction method into this folder.
# 2. Run I-Depth_Estimation/vertical_strip_method/estimate_depth.py first.
# 3. Copy I-Depth_Estimation/vertical_strip_method/output/depth_mm.npy here,
#    next to reconstruct.py.
# 4. Use the same SCENE and DOWNSAMPLE settings as the depth script.
# 5. Run: python reconstruct.py
# 6. The image is saved in
#    II-Post_Capture_Reconstruction/vertical_strip_method/output/.

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy import fft

import dfd
from common import (CAPTURES, CALIBRATION_FILE, MASTER_DARK_FILE,
                    SCENE_NAME, downsample, load_green, to_display)

SCENE = "Scale_1/pair2"
DOWNSAMPLE = 2
LAM = 0.5
RIDGE = 0.003
DEPTH_MAP = Path(__file__).resolve().parent / "depth_mm.npy"
OUTPUT = Path(__file__).resolve().parent / "output"


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

    OUTPUT.mkdir(exist_ok=True)
    plt.imsave(OUTPUT / "all_in_focus.png", to_display(np.maximum(reconstructed, 0)),
               cmap="gray")


if __name__ == "__main__":
    main()
