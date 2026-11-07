"""
estimate_depth.py (pixel by pixel method)
-----------------------------------------
Stage 2 of the depth-from-defocus pipeline: estimate a depth map from a scene
captured once with each mask, using the PSF pairs from calibrate.py (Zhou, Lin
& Nayar 2009; algorithm in dfd.py).

Steps:
  1. Load both scene RAWs (green channel), subtract the master dark.
  2. Downsample (default 2x, so ~1300 x 866 px) for speed. The PSFs are
     downsampled by the same factor.
  3. For every calibrated depth, jointly deconvolve the pair with that
     depth's PSF pair and measure the reconstruction error (dfd.estimate).
  4. Each pixel takes the depth with the smallest error. Pixels that are too
     dark (vignetted) or where the best depth barely beats the runner-up are
     marked low-confidence.

II-Post_Capture_Reconstruction/pixel_by_pixel_method/reconstruct.py makes the
all-in-focus image from the same deconvolution and this depth map.

Outputs (Out/Depth_Estimation/pixel_by_pixel_method/):
    depth_heatmap.png   capture | depth map | confident depth
    depth_mm.npy        depth per pixel (mm), at the processing resolution
    confidence.npy      boolean map of confident pixels
    settings.json       the scene and settings of this run, read by reconstruct.py

Run from this folder, after ../calibrate.py:
    python estimate_depth.py
    python estimate_depth.py --scene-dir Scale_2 --lam 0.3 --window 41
"""

import argparse
import json
import sys
from pathlib import Path

# The shared code (common.py and dfd.py) sits one folder up.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import BoundaryNorm
from scipy import ndimage as ndi

import dfd
from common import (CALIBRATION_FILE, CAPTURES, MASTER_DARK_FILE, OUT_DEPTH,
                    REPO, SCENE_DIR, SCENE_NAME, downsample, load_green,
                    read_exposure, to_display)

OUTPUT = OUT_DEPTH / "pixel_by_pixel_method"


def main():
    ap = argparse.ArgumentParser(description="Coded-aperture-pair depth estimation.")
    ap.add_argument("--scene-dir", default=SCENE_DIR,
                    help="Folder in Captures/Depth_Estimation_and_Reconstruction/ with mask1/mask2 RAWs")
    ap.add_argument("--downsample", type=int, default=2, help="Processing downsample factor")
    ap.add_argument("--lam", type=float, default=0.3,
                    help="Noise-to-signal weight of the image prior (selftest.py best: 0.1-1)")
    ap.add_argument("--window", type=int, default=31, help="Error averaging window (processed px)")
    ap.add_argument("--min-signal", type=float, default=0.05,
                    help="Low-confidence if local brightness < this x the image's 99th percentile")
    ap.add_argument("--min-margin", type=float, default=0.02,
                    help="Low-confidence if 2nd-best error is within this fraction of the best")
    args = ap.parse_args()

    if not CALIBRATION_FILE.exists():
        sys.exit("No calibration found. Run calibrate.py in App/Processing/I-Depth_Estimation/ first.")
    cal = np.load(CALIBRATION_FILE)
    dark = np.load(MASTER_DARK_FILE)
    depths = cal["depths_mm"]
    n = len(depths)
    if cal["saturated_energy"].max() > 0:
        print(f"WARNING: calibration used saturated PSFs "
              f"(up to {100 * cal['saturated_energy'].max():.0f}% clipped energy). Testing only.")

    # ---- load the scene pair -------------------------------------------------
    paths = [CAPTURES / args.scene_dir / SCENE_NAME.format(mask=m) for m in (1, 2)]
    for p in paths:
        if not p.exists():
            sys.exit(f"Missing scene capture: {p}")
    settings = [read_exposure(p) for p in paths]
    if settings[0] != settings[1]:
        print(f"WARNING: mask 1 and mask 2 shot with different settings {settings}")
    psf_iso, _, psf_f = cal["psf_settings"]
    if settings[0][2] != psf_f:
        print(f"WARNING: scene f-number {settings[0][2]} differs from calibration f/{psf_f}; "
              f"the PSFs do not apply")

    imgs, clips = zip(*(load_green(p) for p in paths))
    for m, c in enumerate(clips):
        if c.any():
            print(f"Note: scene mask {m + 1} has {int(c.sum())} clipped pixels")
    I1, I2 = (downsample(im - dark, args.downsample) for im in imgs)
    kernels = dfd.prepare_kernels(cal["kernels"], args.downsample)
    print(f"Scene {args.scene_dir}: {I1.shape[1]} x {I1.shape[0]} px, {n} candidate depths, "
          f"PSFs {kernels[0][0].shape[0]} px, lam {args.lam}, window {args.window}")

    # ---- depth search --------------------------------------------------------
    errors, _ = dfd.estimate(I1, I2, kernels, args.lam, args.window)
    best, margin = dfd.select_depth(errors)
    depth_mm = depths[best]

    brightness = ndi.uniform_filter((I1 + I2) / 2, args.window)
    confident = (brightness > args.min_signal * np.percentile(I1, 99)) & (margin > args.min_margin)

    OUTPUT.mkdir(parents=True, exist_ok=True)
    np.save(OUTPUT / "depth_mm.npy", depth_mm)
    np.save(OUTPUT / "confidence.npy", confident)
    # reconstruct.py reads these so it deconvolves the same pair the same way.
    (OUTPUT / "settings.json").write_text(json.dumps(
        {"scene_dir": args.scene_dir, "downsample": args.downsample,
         "lam": args.lam, "window": args.window}, indent=2))

    counts = np.bincount(best[confident], minlength=n)
    print(f"Confident pixels: {100 * confident.mean():.1f}%")
    for d, c in zip(depths, counts):
        print(f"  {d:6.0f} mm: {100 * c / max(confident.sum(), 1):5.1f}% of confident pixels")

    # ---- figure in the style of Zhou et al.: capture, depth map, confident depth
    cmap = plt.get_cmap("jet", n).copy()
    cmap.set_bad("black")
    norm = BoundaryNorm(np.arange(n + 1) - 0.5, n)
    fig, ax = plt.subplots(1, 3, figsize=(18, 4.8), layout="constrained")
    ax[0].imshow(to_display(I1), cmap="gray"); ax[0].set_title("Captured image (mask 1)")
    ax[1].imshow(best, cmap=cmap, norm=norm); ax[1].set_title("Estimated depth map")
    im = ax[2].imshow(np.ma.masked_where(~confident, best), cmap=cmap, norm=norm)
    ax[2].set_title("Depth map, confident pixels only")
    for a in ax:
        a.axis("off")
    cb = fig.colorbar(im, ax=ax, ticks=range(n), shrink=0.8, label="Distance from LCD")
    cb.ax.set_yticklabels([f"{d:.0f} mm" for d in depths])
    title = f"Coded aperture pair DfD, pixel by pixel method, scene {args.scene_dir}"
    if cal["saturated_energy"].max() > 0:
        title += "  (TEST: saturated PSFs)"
    fig.suptitle(title)
    fig.savefig(OUTPUT / "depth_heatmap.png", dpi=110)
    print(f"Saved depth_heatmap.png, depth_mm.npy, confidence.npy and settings.json "
          f"in {OUTPUT.relative_to(REPO)}")


if __name__ == "__main__":
    main()
