"""The key flutter shutter figure: the "95" coded, deblurred and reference at f/5.6, f/11 and f/22,
with the LCD in front of the lens, made from the photos in data/.

Each column is one run: its still reference photo and its coded photo, with the code read from
the coded photo's trace. The coded photo is deblurred by 40 Richardson-Lucy iterations at the
blur length flutter_score.py found for it, with the car moving left. Every panel is fitted to its
reference by a gain and an offset and drawn with the reference's black and white points, then
cut around the "95" as flutter_score.py cuts 95_compare.png. The MSE of each deblur against its
reference prints as it goes.

Run from this folder:
  .venv/bin/python flutter_figure.py                  writes images/flutter_front_95.png
  .venv/bin/python flutter_figure.py --out fig.png
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
DATA = HERE / "data"
# column title, the run's file prefix in data/, the coded photo's index and the blur length in px
# that flutter_score.py's sweep found for it
RUNS = [("f/5.6", "Run2_f5_6_100ms_invert", "02", 375),
        ("f/11", "Run19_100ms_invert", "01", 475),
        ("f/22", "Run2_f22_100ms_invert", "02", 325)]
ROWS = ("Coded", "Deblurred", "Reference")


def column(prefix, index, blur):
    """the coded, deblurred and reference close-ups of one run, and the deblur's score"""
    R = fd.load(str(DATA / f"{prefix}_00_reference.cr2"), fs.B)
    S = fs.Score(R)
    lo, hi = np.percentile(R, 0.5), np.percentile(R, 99.5)
    stem = DATA / f"{prefix}_{index}_coded"
    code, _ = fs.code_of(stem)
    C = fd.load(str(stem.with_suffix(".cr2")), fs.B)
    D = fs.rl(C, fs.kern(code, blur, True))
    panels = []
    for img in (C, D):
        s = S(img)
        panels.append((fs.u8(S.fitted(img, s["dy"], s["dx"]), lo, hi), s["dy"], s["dx"]))
    cy, cx, _ = fs.find_95(R)
    return fs.close_ups(R, panels + [(fs.u8(R, lo, hi), 0, 0)], cy, cx), s


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(HERE / "images" / "flutter_front_95.png"))
    a = ap.parse_args()
    plt.rcParams.update({"font.family": "serif", "font.size": 22})
    fig, axes = plt.subplots(len(ROWS), len(RUNS), figsize=(9.9, 6.6), dpi=200,
                             gridspec_kw={"wspace": 0.02, "hspace": 0.04})
    for j, (title, prefix, index, blur) in enumerate(RUNS):
        crops, s = column(prefix, index, blur)
        print(f"{title}: {prefix} coded, RL40 at {blur} px, MSE {s['mse']:.5f}", flush=True)
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
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(a.out, bbox_inches="tight", pad_inches=0.05)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
