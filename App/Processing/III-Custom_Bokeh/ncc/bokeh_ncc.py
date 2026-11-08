"""What the custom bokeh NCC scripts share: where things are, the pattern list and the template matching.

Each photo shows out-of-focus fairy lights. The blur of each light is a scaled copy of the pattern
on the panel, clipped by the lens iris. For one light and one pattern the scripts
  1. cut a window around the light from the linear luminance of the raw frame,
  2. rebuild the displayed pattern with the capture app's own pattern code, cut to the iris footprint,
  3. slide the pattern over the window at a sweep of sizes and keep the best normalised
     cross-correlation (NCC),
  4. repeat with an open disc (the baseline) and with every other pattern (identification).
The orientation of the templates, one of the eight flips and quarter turns, is chosen once per panel
position over every scored light and frame, and then held fixed.

Every script finds Captures/, Out/ and the capture app from its own place in the repository.
--captures and --out override the first two. The out folder holds the intermediate files as well as
the results, so each script reads what the one before it wrote from there.
"""
import argparse
import re
import sys
from collections import Counter
from pathlib import Path

import cv2
import numpy as np
import rawpy

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]                                   # the repository root
CAPTURES = ROOT / "Captures" / "Custom_Bokeh"
OUT = ROOT / "Out" / "Custom_Bokeh" / "ncc"
CAPTURE_APP = ROOT / "App" / "Capturing" / "Ubuntu-System"
SPRITES = CAPTURE_APP / "sprites" / "binary"
sys.path.insert(0, str(CAPTURE_APP))
import patterns as P  # noqa: E402

cfg = P.cfg

PATTERNS = ["mario_binary_walk_1", "mario_binary_walk_2", "mario_binary_walk_3",
            "knight_binary_walk_1", "knight_binary_walk_2",
            "link_binary_attack_1", "link_binary_attack_2",
            "zhou_a", "zhou_b", "nayar", "levin"]
# panel position: the folder under Captures/Custom_Bokeh
STAGES = {"outside": "outside_lens", "inside": "inside_lens"}
STAGE_MM = {"outside": 9.5, "inside": 5.5}           # iris footprint on the panel, from the capture file names
FOCAL_MM = {"outside": 55.0, "inside": 53.0}         # EXIF focal length
SENSOR_PITCH_MM = 22.3 / 5184                        # EOS 60D, 4.30 um
HALF = 2                                             # raw frames are read at half resolution
# <stem>_<pupil mm>mm_offset_<offset>mm, as the team named the photos
NAME = re.compile(r"^(?P<stem>.+?)_(?P<pupil>\d+(?:\.\d+)?)mm_offset_(?P<offset>[\d-]+)mm$")


def parse_args(doc, captures=False):
    """--out, and --captures when the script reads the raw photos"""
    ap = argparse.ArgumentParser(description=doc, formatter_class=argparse.RawDescriptionHelpFormatter)
    if captures:
        ap.add_argument("--captures", default=str(CAPTURES), help="the folder with inside_lens/ and outside_lens/")
    ap.add_argument("--out", default=str(OUT), help="where the results go, and where the earlier scripts' files are read from")
    return ap.parse_args()


def photos(folder):
    """{stem: path} for the folder's CR2 files at the folder's usual pupil, and that pupil in mm.
    A photo at another pupil is left out and named"""
    found = []
    for path in sorted(folder.glob("*.cr2")):
        m = NAME.match(path.stem)
        if m:
            found.append((m["stem"], path, float(m["pupil"])))
        else:
            print(f"left out {path.name}: the name does not read <pattern>_<pupil>mm_offset_<offset>mm")
    if not found:
        raise SystemExit(f"no CR2 photos in {folder}")
    usual = Counter(p for _, _, p in found).most_common(1)[0][0]
    out = {}
    for stem, path, pupil in found:
        if pupil == usual:
            out[stem] = path
        else:
            print(f"left out {path.name}: {pupil:g} mm pupil, the folder's usual pupil is {usual:g} mm")
    return out, usual


def develop(path):
    """linear RGB at half size with the camera's white balance, as a 16 bit array"""
    with rawpy.imread(str(path)) as raw:
        return raw.postprocess(use_camera_wb=True, no_auto_bright=True, gamma=(1, 1), output_bps=16,
                               half_size=True, user_flip=0)


def luminance(rgb16):
    """the mean of the three channels in [0, 1], float32"""
    return rgb16.astype(np.float32).mean(axis=2) / 65535.0


def pattern_mask(name, diameter_mm):
    """float32, 1 where light passes, cut to the square that bounds the iris disc; also clipped by the disc"""
    if name.startswith(("mario", "knight", "link")):
        full = P.build(str(SPRITES / name.split("_")[0] / f"{name}.png"), diameter_mm=diameter_mm)
    elif name == "disc":
        full = P.disc(diameter_mm)
    else:
        full = P.build(name, diameter_mm=diameter_mm)
    full = full & P.disc(diameter_mm)
    d = P.pupil_px(diameter_mm)
    cy, cx = (cfg.PANEL_H - 1) / 2, (cfg.PANEL_W - 1) / 2
    y0, y1 = int(round(cy - d / 2)), int(round(cy + d / 2)) + 1
    x0, x1 = int(round(cx - d / 2)), int(round(cx + d / 2)) + 1
    return full[y0:y1, x0:x1].astype(np.float32)


def transforms():
    """the eight symmetries of a square, as functions on a 2-D array"""
    out = {}
    for k in range(4):
        out[f"rot{90 * k}"] = lambda a, k=k: np.rot90(a, k)
        out[f"rot{90 * k}+mirror"] = lambda a, k=k: np.rot90(a[:, ::-1], k)
    return out


def template(mask, size_px, blur_frac):
    """mask resampled to size_px square (nearest neighbour) and softened by blur_frac * size"""
    big = cv2.resize(mask, (size_px, size_px), interpolation=cv2.INTER_NEAREST)
    sig = max(0.1, blur_frac * size_px)
    return cv2.GaussianBlur(big, (0, 0), sig)


def best_ncc(window, mask, d0, scales, blur_frac):
    """best NCC of mask over a window, sweeping the template size around d0; returns ncc, scale, (dx, dy), size"""
    best = (-1.0, None, None, None)
    for s in scales:
        size = int(round(d0 * s))
        if size < 20 or size >= min(window.shape) - 4:
            continue
        t = template(mask, size, blur_frac)
        r = cv2.matchTemplate(window, t, cv2.TM_CCOEFF_NORMED)
        _, mx, _, loc = cv2.minMaxLoc(r)
        if mx > best[0]:
            best = (float(mx), float(s), loc, size)
    return best
