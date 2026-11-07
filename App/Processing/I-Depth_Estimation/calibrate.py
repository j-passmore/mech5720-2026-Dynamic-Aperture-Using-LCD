"""
calibrate.py
------------
Stage 1 of the depth-from-defocus pipeline: build the master dark and turn
the raw point-source captures into a calibrated PSF pair for every depth.

  1. Master dark = mean of the lens-cap dark frames. It contains the black
     level, dark current and dark fixed-pattern noise. Ambient light was
     measured to be ~0 DN above dark (well below the 7 DN read noise), so
     subtracting this removes all three.
  2. For each depth in distances.yaml, load the mask-1 and mask-2 PSF RAWs,
     take the green channel, subtract the master dark.
  3. Crop both PSFs around a COMMON centre (the centroid of the two summed),
     so the shift between the two masks' PSFs - itself a depth cue for these
     asymmetric apertures - is preserved.
  4. Remove any residual background (median of the crop border) and zero
     pixels below NOISE_CUT x read noise.
  5. Normalise so the mask-1 PSF sums to 1 and the mask-2 PSF keeps its
     relative brightness (mask 2 transmits more light). The scene images then
     need no brightness correction, as long as both masks were shot at the
     same exposure.

Saturated PSFs are refused unless --allow-saturated is given: clipped pixels
flatten the PSF core, which is exactly where the coded pattern is.

Outputs (Out/Depth_Estimation/calibration/):
    master_dark.npy     half-res green master dark (DN)
    calibration.npz     PSF pairs + metadata, read by every depth and reconstruction script
    psf_pairs.png       visual check of every PSF pair

Run from this folder (App/Processing/I-Depth_Estimation/):
    python calibrate.py
    python calibrate.py --allow-saturated      # test with current data
    python calibrate.py --psf-dir Scale_1/psfs_v2 --psf-name "m{mask}_psf{index}.CR2"
"""

import argparse
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy import ndimage as ndi

from common import (CALIBRATION_FILE, CAPTURES, DARK_GLOB, MASTER_DARK_FILE,
                    OUTPUT, PSF_DIR, PSF_NAME, REPO, load_green,
                    parse_distances, read_exposure)

NOISE_CUT = 3.0        # zero PSF pixels below this many x read noise
ENERGY_RADIUS = 0.99   # auto crop: radius holding this fraction of PSF energy
MAX_HALF_SIZE = 300    # largest crop half-width allowed (half-res pixels)


def build_master_dark():
    paths = sorted(CAPTURES.glob(DARK_GLOB))
    if len(paths) < 2:
        sys.exit(f"Need at least 2 dark frames matching {CAPTURES / DARK_GLOB}")
    exposures = {read_exposure(p) for p in paths}
    if len(exposures) > 1:
        print(f"Warning: dark frames have mixed settings {exposures}")
    frames = [load_green(p)[0] for p in paths]
    dark = np.mean(frames, axis=0)
    # temporal read noise of ONE frame, from the difference of two frames
    read_noise = float(np.std(frames[0] - frames[1]) / np.sqrt(2))
    print(f"Master dark: {len(paths)} frames {exposures.pop()}, mean {dark.mean():.1f} DN, "
          f"single-frame read noise {read_noise:.2f} DN")
    return dark, read_noise, read_exposure(paths[0])


def find_centre(img, search_radius=200):
    """Peak of the smoothed image, refined to the intensity centroid around it."""
    sm = ndi.gaussian_filter(img, 3)
    y, x = np.unravel_index(np.argmax(sm), sm.shape)
    y0, y1 = max(0, y - search_radius), y + search_radius + 1
    x0, x1 = max(0, x - search_radius), x + search_radius + 1
    win = np.clip(img[y0:y1, x0:x1], 0, None)
    cy, cx = ndi.center_of_mass(win)
    return int(round(y0 + cy)), int(round(x0 + cx))


def energy_radius(img, centre, frac):
    """Smallest radius around centre holding `frac` of the positive energy."""
    cy, cx = centre
    r_max = MAX_HALF_SIZE
    win = np.clip(img[cy - r_max:cy + r_max + 1, cx - r_max:cx + r_max + 1], 0, None)
    yy, xx = np.indices(win.shape) - r_max
    rr = np.hypot(yy, xx).ravel()
    order = np.argsort(rr)
    cum = np.cumsum(win.ravel()[order])
    return int(np.ceil(rr[order][np.searchsorted(cum, frac * cum[-1])]))


def crop(img, centre, half):
    cy, cx = centre
    return img[cy - half:cy + half + 1, cx - half:cx + half + 1].copy()


def clean_psf(c, read_noise):
    border = np.concatenate([c[:8].ravel(), c[-8:].ravel(), c[:, :8].ravel(), c[:, -8:].ravel()])
    c = c - np.median(border)
    c[c < NOISE_CUT * read_noise] = 0
    return c


def main():
    ap = argparse.ArgumentParser(description="Build master dark and calibrated PSF pairs.")
    ap.add_argument("--allow-saturated", action="store_true",
                    help="Continue even if PSFs contain clipped pixels (for testing only)")
    ap.add_argument("--half-size", type=int,
                    help="PSF crop half-width in half-res pixels (default: auto)")
    ap.add_argument("--psf-dir", default=PSF_DIR, help=f"PSF folder in captures/ (default {PSF_DIR})")
    ap.add_argument("--psf-name", default=PSF_NAME,
                    help=f"PSF file pattern with {{mask}} and {{index}} (default {PSF_NAME})")
    args = ap.parse_args()
    OUTPUT.mkdir(parents=True, exist_ok=True)

    dark, read_noise, dark_exp = build_master_dark()
    np.save(MASTER_DARK_FILE, dark)

    distances = parse_distances()
    print(f"Depths from distances.yaml: {distances}")

    # ---- load, dark-subtract and centre every PSF pair ----------------------
    pairs = []
    for idx, mm in distances.items():
        paths = [CAPTURES / args.psf_dir / args.psf_name.format(mask=m, index=idx) for m in (1, 2)]
        for p in paths:
            if not p.exists():
                sys.exit(f"Missing PSF capture: {p}")
        exps = [read_exposure(p) for p in paths]
        if exps[0] != exps[1]:
            print(f"Warning: psf{idx} masks shot with different settings {exps}; "
                  f"their relative brightness will be wrong")
        if exps[0] != dark_exp:
            print(f"Warning: psf{idx} settings {exps[0]} differ from dark frames {dark_exp}")
        imgs, clips = zip(*(load_green(p) for p in paths))
        imgs = [im - dark for im in imgs]
        centre = find_centre(imgs[0] + imgs[1])
        pairs.append(dict(index=idx, mm=mm, imgs=imgs, clips=clips, centre=centre))

    # ---- one crop size for all depths, set by the biggest (closest) PSF ------
    if args.half_size:
        half = args.half_size
    else:
        half = max(energy_radius(p["imgs"][0] + p["imgs"][1], p["centre"], ENERGY_RADIUS)
                   for p in pairs)
        half = min(half + 5, MAX_HALF_SIZE)
    print(f"PSF crop: {2 * half + 1} x {2 * half + 1} half-res pixels")

    # ---- crop, clean, check saturation, normalise ---------------------------
    kernels, centres, ratios, sat_frac = [], [], [], []
    for p in pairs:
        c = [clean_psf(crop(im, p["centre"], half), read_noise) for im in p["imgs"]]
        clipped = [crop(cl, p["centre"], half) for cl in p["clips"]]
        sat = [float(ci[cl].sum() / ci.sum()) if ci.sum() > 0 else 0.0 for ci, cl in zip(c, clipped)]
        total1 = c[0].sum()
        kernels.append([c[0] / total1, c[1] / total1])
        centres.append(p["centre"])
        ratios.append(c[1].sum() / total1)
        sat_frac.append(sat)
        print(f"  psf{p['index']} {p['mm']:6.0f} mm  centre (x={p['centre'][1]}, y={p['centre'][0]})  "
              f"mask2/mask1 light {ratios[-1]:.2f}  energy in clipped px: "
              f"mask1 {100 * sat[0]:.1f}%  mask2 {100 * sat[1]:.1f}%")

    worst = max(max(s) for s in sat_frac)
    if worst > 0 and not args.allow_saturated:
        sys.exit(f"\nPSFs are saturated (up to {100 * worst:.0f}% of PSF energy in clipped pixels). "
                 f"Reshoot with a shorter exposure, or rerun with --allow-saturated to test anyway.")
    if worst > 0:
        print(f"\nWARNING: continuing with saturated PSFs (--allow-saturated). Results are for testing only.")

    np.savez(CALIBRATION_FILE,
             depths_mm=np.array([p["mm"] for p in pairs]),
             psf_index=np.array([p["index"] for p in pairs]),
             kernels=np.array(kernels),                  # (n_depths, 2, S, S)
             centres=np.array(centres),                  # (n_depths, 2) as (y, x), half-res px
             transmission_ratio=np.array(ratios),
             saturated_energy=np.array(sat_frac),
             read_noise=read_noise,
             psf_dir=args.psf_dir,
             psf_settings=np.array(read_exposure(
                 CAPTURES / args.psf_dir / args.psf_name.format(mask=1, index=pairs[0]["index"]))))
    print(f"Saved {CALIBRATION_FILE.relative_to(REPO)}")

    # ---- visual check --------------------------------------------------------
    n = len(pairs)
    fig, axes = plt.subplots(2, n, figsize=(3 * n, 7), squeeze=False)
    for j, (p, k) in enumerate(zip(pairs, kernels)):
        vmax = max(k[0].max(), k[1].max())
        for m in range(2):
            ax = axes[m, j]
            ax.imshow(np.sqrt(k[m] / vmax), cmap="magma", vmin=0, vmax=1)
            ax.set_title(f"{p['mm']:.0f} mm  mask {m + 1}\nclipped {100 * sat_frac[j][m]:.0f}%", fontsize=9)
            ax.axis("off")
    fig.suptitle("Calibrated PSF pairs (sqrt scale, common centre per depth)")
    fig.tight_layout()
    fig.savefig(OUTPUT / "psf_pairs.png", dpi=110)
    print(f"Saved {(OUTPUT / 'psf_pairs.png').relative_to(REPO)}")


if __name__ == "__main__":
    main()
