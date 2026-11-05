"""The key flutter shutter figures: the "95" coded, deblurred and reference at f/5.6, f/11 and
f/22, once with the LCD in front of the lens and once with it inside the extension tube, made
from the photos in Captures/Flutter_Shutter/.

Each column is one run: its still reference photo and its coded photo, with the code read from
the coded photo's trace. The coded photo is deblurred by 40 Richardson-Lucy iterations at the
blur length flutter_score.py found for it, with the car moving left. Every panel is fitted to its
reference by a gain and an offset and drawn with the reference's black and white points, then
cut around the "95" as flutter_score.py cuts 95_compare.png. The MSE of each deblur against its
reference prints as it goes. A figure whose photos are not all in Captures/Flutter_Shutter/ is
skipped, with the missing files named.

Run from this folder:
  .venv/bin/python flutter_figure.py                  writes Out/Flutter_Shutter/flutter_front_95.png
                                                      and Out/Flutter_Shutter/flutter_inside_95.png
  .venv/bin/python flutter_figure.py --out ../../../Out/Flutter_Shutter
"""
import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

import flutter_deblur as fd  # noqa: E402
import flutter_score as fs  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DATA = ROOT / "Captures" / "Flutter_Shutter"
OUT = ROOT / "Out" / "Flutter_Shutter"
# one figure per panel position: the file name, the position and its three columns. Each column
# is the column title, the run's file prefix in Captures/Flutter_Shutter/, the coded photo's index
# and the blur length in px that flutter_score.py's sweep found for it
FIGURES = [
    ("flutter_front_95.png", "in front of the lens",
     [("f/5.6", "Run2_f5_6_100ms_invert", "02", 375),
      ("f/11", "Run19_100ms_invert", "01", 475),
      ("f/22", "Run2_f22_100ms_invert", "02", 325)]),
    ("flutter_inside_95.png", "inside the extension tube",
     [("f/5.6", "f56_run1_lcd_inside_100ms_invert", "02", 500),
      ("f/11", "f11_run1_lcd_inside_2_100ms_invert", "02", 375),
      ("f/22", "f22_inside_lcd_run2_100ms_invert", "02", 400)]),
]
ROWS = ("Coded", "Deblurred", "Reference")


def files(prefix, index):
    """the reference photo, the coded photo and its trace for one run"""
    return (DATA / f"{prefix}_00_reference.cr2", DATA / f"{prefix}_{index}_coded.cr2",
            DATA / f"{prefix}_{index}_coded.json")


def column(prefix, index, blur):
    """the coded, deblurred and reference close-ups of one run, and the deblur's score"""
    reference, coded, _ = files(prefix, index)
    R = fd.load(str(reference), fs.B)
    S = fs.Score(R)
    lo, hi = np.percentile(R, 0.5), np.percentile(R, 99.5)
    code, _ = fs.code_of(coded.with_suffix(""))
    C = fd.load(str(coded), fs.B)
    D = fs.rl(C, fs.kern(code, blur, True))
    panels = []
    for img in (C, D):
        s = S(img)
        panels.append((fs.u8(S.fitted(img, s["dy"], s["dx"]), lo, hi), s["dy"], s["dx"]))
    cy, cx, _ = fs.find_95(R)
    return fs.close_ups(R, panels + [(fs.u8(R, lo, hi), 0, 0)], cy, cx), s


def figure(name, position, runs, out_dir):
    missing = [f.name for _, prefix, index, _ in runs for f in files(prefix, index) if not f.exists()]
    if missing:
        print(f"skipped {name}: {DATA} lacks " + ", ".join(missing))
        return
    plt.rcParams.update({"font.family": "serif", "font.size": 22})
    fig, axes = plt.subplots(len(ROWS), len(runs), figsize=(9.9, 6.6), dpi=200,
                             gridspec_kw={"wspace": 0.02, "hspace": 0.04})
    for j, (title, prefix, index, blur) in enumerate(runs):
        crops, s = column(prefix, index, blur)
        print(f"{position}, {title}: {prefix} coded, RL40 at {blur} px, MSE {s['mse']:.5f}", flush=True)
        for i, crop in enumerate(crops):
            ax = axes[i, j]
            ax.imshow(crop, cmap="gray", vmin=0, vmax=255)
            ax.set_xticks([])
            ax.set_yticks([])
            for side in ax.spines.values():
                side.set_visible(False)
            if i == 0:
                ax.set_title(title)
            if j == 0:
                ax.set_ylabel(ROWS[i])
    out = out_dir / name
    fig.savefig(out, bbox_inches="tight", pad_inches=0.05)
    plt.close(fig)
    print("wrote", out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(OUT), help="the folder the figures go in")
    a = ap.parse_args()
    out_dir = Path(a.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, position, runs in FIGURES:
        figure(name, position, runs, out_dir)


if __name__ == "__main__":
    main()
