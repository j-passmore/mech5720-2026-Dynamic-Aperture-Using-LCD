"""
check_saturation.py
-------------------
Loop through the images in a folder (and its subfolders) and report saturated
green pixels. Saturated pixels flatten the core of a PSF, so any PSF image
that reports saturation should be reshot with a shorter exposure / lower ISO.

RAW files (.CR2 etc.) are checked on the raw Bayer data: only the green
photosites are tested against the camera's white level, before any
demosaicing or tone curve. Images with fewer than --min-pixels saturated
pixels are reported as likely hot pixels rather than flagged. JPEG / PNG / TIFF files are checked on the green
channel against their maximum value (255 for 8-bit).

Install:
    pip install rawpy numpy pillow

Examples:
    python check_saturation.py captures
    python check_saturation.py captures/Scale_1 --raw-only
    python check_saturation.py captures --frac 0.95      # flag pixels within 5% of clipping
"""

import argparse
from pathlib import Path

import numpy as np
import rawpy
from PIL import Image

RAW_EXTS = {".cr2", ".cr3", ".nef", ".arw", ".dng"}
IMG_EXTS = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}


def raw_green(path):
    """Green photosite values of a RAW file, and its saturation level."""
    with rawpy.imread(str(path)) as raw:
        green_ids = [i for i, c in enumerate(raw.color_desc.decode()) if c == "G"]
        values = raw.raw_image_visible
        mask = np.isin(raw.raw_colors_visible, green_ids)
        green = np.where(mask, values, 0)
        # Use the camera's own white level from the file's metadata (15094 on
        # the 60D). LibRaw's raw.white_level reports a lower value (12279) that
        # sits well below where the sensor actually clips (~15300).
        cam_white = raw.camera_white_level_per_channel
        white = min(cam_white[i] for i in green_ids) if cam_white else raw.white_level
        return green, mask, white


def img_green(path):
    """Green channel of an ordinary image, and its saturation level."""
    arr = np.asarray(Image.open(path).convert("RGB") if Image.open(path).mode != "I;16"
                     else Image.open(path))
    green = arr[..., 1] if arr.ndim == 3 else arr
    max_val = 65535 if green.dtype == np.uint16 else 255
    return green, np.ones(green.shape, bool), max_val


def check(path, frac):
    if path.suffix.lower() in RAW_EXTS:
        green, mask, white = raw_green(path)
    else:
        green, mask, white = img_green(path)
    threshold = frac * white
    sat = mask & (green >= threshold)
    n_sat = int(sat.sum())
    result = {
        "file": path,
        "max": int(green[mask].max()),
        "white": int(white),
        "n_sat": n_sat,
        "pct": 100.0 * n_sat / int(mask.sum()),
        "bbox": None,
    }
    if n_sat:
        ys, xs = np.nonzero(sat)
        result["bbox"] = (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))
    return result


def main():
    ap = argparse.ArgumentParser(description="Report saturated green pixels in a folder of images.")
    ap.add_argument("folder", type=Path, help="Folder to scan (subfolders included)")
    ap.add_argument("--frac", type=float, default=1.0,
                    help="Flag pixels >= frac * saturation level (default 1.0 = fully clipped)")
    ap.add_argument("--raw-only", action="store_true", help="Skip JPG/PNG/TIFF files")
    ap.add_argument("--min-pixels", type=int, default=10,
                    help="Only flag an image with at least this many saturated pixels, "
                         "so a few hot pixels don't trigger it (default 10)")
    args = ap.parse_args()

    exts = RAW_EXTS if args.raw_only else RAW_EXTS | IMG_EXTS
    files = sorted(p for p in args.folder.rglob("*") if p.suffix.lower() in exts)
    if not files:
        print(f"No images found in {args.folder}")
        return

    print(f"{'file':40s} {'max green':>10s} {'sat. level':>10s} {'saturated':>10s} {'%':>8s}  bbox (x0,y0,x1,y1)")
    flagged = 0
    for path in files:
        try:
            r = check(path, args.frac)
        except Exception as e:  # unreadable / unsupported file: report and carry on
            print(f"{str(path.relative_to(args.folder)):40s} ERROR: {e}")
            continue
        is_sat = r["n_sat"] >= args.min_pixels
        flag = "  <-- SATURATED" if is_sat else ("  (likely hot pixels)" if r["n_sat"] else "")
        flagged += is_sat
        print(f"{str(path.relative_to(args.folder)):40s} {r['max']:>10d} {r['white']:>10d} "
              f"{r['n_sat']:>10d} {r['pct']:>7.3f}%  {r['bbox'] or ''}{flag}")

    print(f"\n{flagged} of {len(files)} image(s) have saturated green pixels"
          f"{f' (>= {args.frac:.0%} of saturation)' if args.frac < 1 else ''}.")


if __name__ == "__main__":
    main()
