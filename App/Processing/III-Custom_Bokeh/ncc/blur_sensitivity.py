"""How the headline numbers move with the template softening, on the lights and frames the report used.

final_analysis.py softens each template by 0.15 of its size. This script repeats the NCC of the
displayed pattern and of the open disc at seven softening widths, with the orientation chosen
afresh at each width. Reads Y_all.npz, bokeh_summary.json and bokeh_ncc_table.csv from the out
folder and writes blur_sensitivity.json there.

Run from this folder:
  python3 blur_sensitivity.py
  python3 blur_sensitivity.py --out ../../../../Out/Custom_Bokeh/ncc
"""
import csv
import json
from pathlib import Path

import cv2
import numpy as np

from bokeh_ncc import PATTERNS, STAGE_MM, STAGES, best_ncc, parse_args, pattern_mask, transforms

BLURS = (0.01, 0.03, 0.06, 0.10, 0.15, 0.20, 0.30)
SCALES = np.linspace(0.8, 1.6, 17)


def window(y, cx, cy, d0):
    half = int(0.98 * d0)
    return cv2.GaussianBlur(y[cy - half:cy + half, cx - half:cx + half].astype(np.float32), (0, 0), 0.012 * d0)


def main():
    a = parse_args(__doc__)
    out = Path(a.out)
    Y = np.load(out / "Y_all.npz")
    SUM = json.load(open(out / "bokeh_summary.json"))
    T = transforms()
    scored = {}
    with open(out / "bokeh_ncc_table.csv", newline="") as f:
        for r in csv.DictReader(f):
            scored.setdefault(r["stage"], set()).add((int(r["light"]), r["image"]))
    result = {}
    for st in STAGES:
        D = STAGE_MM[st]
        masks = {p: pattern_mask(p, D) for p in PATTERNS + ["disc"]}
        ents = sorted(scored[st])
        res = {}
        for blur in BLURS:
            per = {t: [] for t in T}
            disc = []
            for i, p in ents:
                L = SUM[st]["lights"][str(i)]
                w = window(Y[f"{st}|{p}"], L["cx"], L["cy"], L["d0"])
                for tn, f in T.items():
                    per[tn].append(best_ncc(w, f(masks[p]), L["d0"], SCALES, blur)[0])
                disc.append(best_ncc(w, masks["disc"], L["d0"], SCALES, blur)[0])
            g = max(per, key=lambda t: np.mean(per[t]))
            c = np.array(per[g]); d = np.array(disc)
            res[str(blur)] = dict(ncc=float(c.mean()), disc=float(d.mean()), delta=float((c - d).mean()), frac=float((c > d).mean()), orient=g)
            print(st, f"blur {blur:.2f}: NCC {c.mean():.3f} disc {d.mean():.3f} delta {np.mean(c - d):+.3f} frac {np.mean(c > d):.2f} orient {g}", flush=True)
        result[st] = res
    with open(out / "blur_sensitivity.json", "w") as f:
        json.dump(result, f, indent=1)
    print("wrote", out / "blur_sensitivity.json")


if __name__ == "__main__":
    main()
