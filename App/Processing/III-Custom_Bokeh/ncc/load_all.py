"""Develop every raw bokeh photo to linear luminance at half size.

Writes to Out/Custom_Bokeh/ncc/:
  Y_all.npz          one float32 luminance frame per photo, keyed "<position>|<pattern>"
  mean_outside.npy   the mean of the eleven frames with the panel in front of the lens
  mean_inside.npy    the same with the panel in the extension tube
A photo at another pupil than the folder's usual one is left out and named.

Run from this folder:
  python3 load_all.py
  python3 load_all.py --captures ../../../../Captures/Custom_Bokeh --out ../../../../Out/Custom_Bokeh/ncc
"""
from pathlib import Path

import numpy as np

from bokeh_ncc import STAGE_MM, STAGES, develop, luminance, parse_args, photos


def main():
    a = parse_args(__doc__, captures=True)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    frames = {}
    for stage, folder in STAGES.items():
        found, pupil = photos(Path(a.captures) / folder)
        if pupil != STAGE_MM[stage]:
            print(f"warning: the {folder} photos are at {pupil:g} mm but the scripts rebuild the patterns at {STAGE_MM[stage]:g} mm")
        for stem, path in found.items():
            frames[(stage, stem)] = luminance(develop(path))
            print(stage, stem, path.name, frames[(stage, stem)].shape, flush=True)
    np.savez_compressed(out / "Y_all.npz", **{f"{st}|{p}": y for (st, p), y in frames.items()})
    for stage in STAGES:
        ys = np.stack([y for (st, _), y in frames.items() if st == stage])
        np.save(out / f"mean_{stage}.npy", ys.mean(axis=0))
        print(stage, "n =", len(ys), "mean frame saved")
    print("wrote", out / "Y_all.npz")


if __name__ == "__main__":
    main()
