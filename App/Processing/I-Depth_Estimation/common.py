"""
common.py
---------
Shared settings and helpers for the coded-aperture depth-from-defocus
pipeline (Zhou, Lin & Nayar, "Coded Aperture Pairs for Depth from Defocus",
ICCV 2009).

All processing uses the GREEN channel only, taken straight from the raw
Bayer data: each 2x2 Bayer cell holds two green photosites, which are
averaged into one pixel. This gives a linear, un-interpolated, half-resolution
image (2601 x 1732 on the EOS 60D).
"""

import re
from pathlib import Path

import numpy as np
import rawpy
from PIL import Image

# ---- Paths -----------------------------------------------------------------
# This file sits in App/Processing/I-Depth_Estimation/. Both depth methods and
# both reconstruction methods import it, so every script reads the same photos
# and the same calibration.
REPO = Path(__file__).resolve().parents[3]
CAPTURES = REPO / "Captures" / "Depth_Estimation_and_Reconstruction"
OUT_DEPTH = REPO / "Out" / "Depth_Estimation"
OUT_RECONSTRUCTION = REPO / "Out" / "Post_Capture_Reconstruction"
OUTPUT = OUT_DEPTH / "calibration"          # calibrate.py and psf_fourier.py write here
DISTANCES_FILE = CAPTURES / "distances.yaml"

# ---- Calibration inputs (relative to CAPTURES) -----------------------------
DARK_GLOB = "fpn/d*.CR2"                    # lens-cap dark frames
# The report used the second PSF set. The first set, Scale_1/psfs with names
# mask{mask}_psf{index}.CR2, stays in the repo for comparison.
PSF_DIR = "Scale_1/psfs_v2"
PSF_NAME = "m{mask}_psf{index}.CR2"         # mask = 1 or 2, index = psfN in distances.yaml

# ---- Scene inputs (relative to CAPTURES) ----------------------------------
SCENE_DIR = "Scale_1"
SCENE_NAME = "mask{mask}.CR2"

CALIBRATION_FILE = OUTPUT / "calibration.npz"
MASTER_DARK_FILE = OUTPUT / "master_dark.npy"


def read_exposure(path):
    """(ISO, exposure time s, f-number) from the CR2's EXIF, or Nones."""
    try:
        exif = Image.open(path).getexif().get_ifd(0x8769)
        return (exif.get(0x8827), float(exif.get(0x829A)), float(exif.get(0x829D)))
    except Exception:
        return (None, None, None)


def load_green(path):
    """Half-resolution green image (float64, raw DN incl. black level) and a
    boolean map of cells where either green photosite is clipped."""
    with rawpy.imread(str(path)) as raw:
        data = raw.raw_image_visible.astype(np.float64)
        colors = raw.raw_colors_visible
        green_ids = [i for i, c in enumerate(raw.color_desc.decode()) if c == "G"]
        cam_white = raw.camera_white_level_per_channel
        white = min(cam_white[i] for i in green_ids) if cam_white else raw.white_level
    h, w = (data.shape[0] // 2) * 2, (data.shape[1] // 2) * 2
    data, colors = data[:h, :w], colors[:h, :w]
    is_green = np.isin(colors, green_ids)
    cells = lambda a: a.reshape(h // 2, 2, w // 2, 2)
    green = cells(data * is_green).sum(axis=(1, 3)) / 2     # exactly 2 greens per cell
    clipped = cells((data >= white) & is_green).any(axis=(1, 3))
    return green, clipped


def parse_distances(path=DISTANCES_FILE):
    """{psf index: distance mm} from lines like 'psf1 = 350mm'. Tolerates
    '=' or ':' and typos such as 'pfs4'; other lines are ignored."""
    pattern = re.compile(r"^\s*p[a-z]*?(\d+)\s*[=:]\s*([\d.]+)\s*mm", re.IGNORECASE)
    distances = {}
    for line in Path(path).read_text().splitlines():
        m = pattern.match(line)
        if m:
            distances[int(m.group(1))] = float(m.group(2))
    if not distances:
        raise ValueError(f"No 'psfN = XXXmm' lines found in {path}")
    return dict(sorted(distances.items()))


def downsample(img, factor):
    """Block-average by an integer factor (crops to a multiple of it)."""
    if factor == 1:
        return img
    h, w = (img.shape[0] // factor) * factor, (img.shape[1] // factor) * factor
    return img[:h, :w].reshape(h // factor, factor, w // factor, factor).mean(axis=(1, 3))


def to_display(img, pct=99.5, gamma=1 / 2.2):
    """Linear image -> 0..1 with a percentile white point and display gamma."""
    hi = np.percentile(img, pct)
    return np.clip(img / hi, 0, 1) ** gamma if hi > 0 else np.zeros_like(img)


def save_comparison(before, after, path):
    """Save the mask 1 photo and its reconstruction side by side at 2340 x 900 px.
    Both reconstruction scripts call this, so both methods draw the same figure."""
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(13, 5), layout="constrained")
    for ax, img, title in zip(axes, (before, after),
                              ("Before reconstruction", "After reconstruction")):
        ax.imshow(img, cmap="gray", vmin=0, vmax=1)
        ax.set_title(title, fontsize=14)
        ax.axis("off")
    fig.savefig(path, dpi=180)
    plt.close(fig)
