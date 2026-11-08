# Custom bokeh scores

The scripts here score every out-of-focus light against the pattern the panel showed. They
regenerate every number quoted in the custom bokeh section of the report from the raw photos in
[Captures/Custom_Bokeh](../../../../Captures/Custom_Bokeh) and write to
[Out/Custom_Bokeh/ncc](../../../../Out/Custom_Bokeh/ncc). [bokeh_figure.py](../bokeh_figure.py) in
the folder above draws the figures and GIFs from the same photos, and [its README](../README.md)
describes the photos. The [root README](../../../../README.md) has the capture procedure.

## What the scripts compute

Each fairy light is a point source behind the scene. Out of focus, it takes the shape of the
aperture, so its blur is a scaled copy of the pattern on the panel, clipped by the lens iris. The
scripts cut a window around each light from the linear luminance of the raw frame and rebuild the
pattern the panel showed with the capture app's own pattern code, at the pupil in the file name:
9.5 mm in front of the lens and 5.5 mm in the extension tube. They slide a softened copy of the
pattern over the window at 17 sizes and keep the best normalised cross-correlation (NCC). They
score the same window against an open disc and against each of the other ten patterns.

The lights do not face the way the pattern does. They come out turned or flipped, and
differently at the two positions. The scripts try the eight flips and quarter turns of the
templates and keep the one with the highest mean NCC over every scored light and frame of a panel
position. That orientation is chosen once per position and then held fixed, so no light picks its
own.

Which lights count is decided from the frames, never from the match. `seeds.py` finds the lights
on the mean of the eleven frames of a position. `final_analysis.py` keeps a seed when its window
lies inside the frame and inside the polygon in `roi_polygons.json`, the region above the cake,
and its diameter is within 1.3 times the median seed of the position. Wider seeds are two lights
merged. A light is then scored in a frame when its core is at least 1.5 times brighter than the
ring just outside it. That leaves 5 lights and 39 scored light-frames in front of the lens, and
5 lights and 22 in the tube.

The 95 % intervals are a bootstrap over lights. The script resamples the lights 4,000 times and
recomputes the mean gain each time. Lights are the replicates because the frames of one light
share its position and brightness. The random stream has a fixed seed, so every run gives the
same intervals.

The control for an effect of the displayed pattern is the mean NCC of the other ten patterns
(`other_mean` and `delta_other_*` in `bokeh_summary.json`). The open disc (`disc_*`) is a weaker
control, because the other ten patterns also beat it.

| | Panel in front of the lens | Panel in the tube |
| --- | --- | --- |
| Lights, scored light-frames | 5, 39 of 55 | 5, 22 of 55 |
| NCC of the displayed pattern, mean and SD | 0.809, 0.097 | 0.779, 0.140 |
| NCC of the open disc | 0.717 | 0.727 |
| NCC of the other ten patterns | 0.776 | 0.770 |
| Gain over the other ten, 95 % interval over lights | 0.033 [0.012, 0.058] | 0.009 [-0.073, 0.040] |
| Gain over the disc, 95 % interval over lights | 0.092 [0.058, 0.109] | 0.052 [-0.028, 0.081] |
| Share where the displayed pattern scores best of the eleven | 0.179 (chance 0.091) | 0.091 |

## How to run

The scripts need numpy, scipy, matplotlib, pillow, rawpy, scikit-image and opencv-python.
`requirements.txt` pins the versions the committed numbers were checked with, on Python 3.13.
Set up a venv once if the system Python lacks any of them:

```bash
cd App/Processing/III-Custom_Bokeh/ncc
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Run the scripts in this order from this folder. With a venv, use `.venv/bin/python` in place of
`python3`.

```bash
python3 load_all.py             # raw frames to linear luminance: Y_all.npz, mean_outside.npy, mean_inside.npy
python3 seeds.py                # light seeds on the mean frames: seeds_auto.json in this folder
python3 final_analysis.py       # NCC, the disc and other-ten controls, identification, field angle, flux: bokeh_summary.json, bokeh_ncc_table.csv
python3 blur_sensitivity.py     # the headline numbers against the template softening: blur_sensitivity.json
python3 make_bokeh_figures.py   # bokeh_principle.png, bokeh_results.png, bokeh_ncc.png, bokeh_montage.png
```

`seeds_auto.json` is committed, so `seeds.py` can be skipped. Every script finds `Captures/`,
`Out/` and the capture app from its own location. `--captures` and `--out` override the first two,
as in `bokeh_figure.py`. The out folder holds the intermediate files as well as the results, so
each script reads what the one before it wrote from there.

## What each output holds

Files in `Out/Custom_Bokeh/ncc/`:

| File | Contents |
| --- | --- |
| `Y_all.npz` | One float32 luminance frame per photo at half size, 1732 x 2601, keyed `<position>\|<pattern>`. 22 frames, 270 MB. Not committed. |
| `mean_outside.npy`, `mean_inside.npy` | The mean of the eleven frames of each position. `seeds.py` reads them. Not committed. |
| `bokeh_summary.json` | Per position: the orientation and the mean NCC of each of the eight; the lights kept, with centre, radius, window and field angle; the counts; the mean and SD of the NCC of the displayed pattern, the disc and the other ten; the gains with their 95 % intervals; the share of light-frames where the displayed pattern scores best of the eleven (`top1`) or its character does (`top1_char`); the per-light means; the fit of NCC against field angle; the per-pattern and per-group statistics; the similarity structure (Spearman rho between the NCC of two lights' blobs and the NCC of their two templates, over every pair of patterns); the flux in the light region against the open fraction of the iris. |
| `bokeh_ncc_table.csv` | One row per scored light-frame: position, light, pattern, field angle, NCC of the displayed pattern, of the disc and of the other ten, and the two identification flags. |
| `blur_sensitivity.json` | For each position and softening width from 0.01 to 0.30 of the template size: the mean NCC of the pattern and of the disc, their difference, the share of light-frames where the pattern wins and the orientation chosen. The report uses 0.15. |
| `bokeh_principle.png` | (a) The aperture stamps its shape onto every out-of-focus light. (b) A simulation with Mario 1. |
| `bokeh_results.png` | (a) Four patterns and the light that showed them best at each position. (b) NCC against field angle, one point per light. (c) NCC by pattern group, with the disc and the other ten as ticks. |
| `bokeh_ncc.png` | Panels (b) and (c) of `bokeh_results.png` on their own, as (a) and (b). |
| `bokeh_montage.png` | Every pattern and the light that showed it, for the appendix. |

Files in this folder: `seeds_auto.json` holds the light seeds of each position as `[x, y, r]` in
half-size pixels. `roi_polygons.json` holds the polygon above the cake for each position, in the
coordinates of an 1800 px wide frame.

## Runtime

About ten minutes in all on an Apple M2 with the system Python: `load_all.py` 21 s, `seeds.py`
2 s, `final_analysis.py` 2 min 47 s, `blur_sensitivity.py` 6 min 46 s and `make_bokeh_figures.py`
11 s. The template sweeps take the time. `blur_sensitivity.py` matches nine templates at 17 sizes
and seven widths for each of the 61 light-frames. `final_analysis.py` holds all 22 frames in
memory, about 400 MB.

## Pitfalls

- **The 10 mm photo.** `inside_lens/` holds one Mario photo at a 10 mm pupil. `load_all.py` and
  `make_bokeh_figures.py` keep the photos at the folder's usual pupil and name the one they leave
  out.
- **The seeds.** `seeds.py` rewrites `seeds_auto.json`. The committed file is what it wrote with
  scikit-image 0.26. Check `git diff seeds_auto.json` after running it. A different seed set
  changes which lights are scored and moves every number.
- **The bootstrap.** The intervals come from `numpy.random.default_rng(0)` and the order of the
  draws in `final_analysis.py`. Keep both to get the same intervals.
- **The colour crops.** The figures crop the lights from the raw frames with a plain display
  gamma. The report's figures used the camera's JPEGs, which the repository does not hold, so the
  crops look a little different. No number uses the crops.
- **The mesh.** Every highlight carries the panel's pixel grid. The template softening of 0.15 of
  the size smooths over it. `blur_sensitivity.json` shows what sharper and softer templates give.
- **Hard-coded optics.** `bokeh_ncc.py` holds the focal lengths from the EXIF (55 mm in front,
  53 mm in the tube) and the sensor pitch of the 60D for the field angle. `HALF = 2` is the
  half-size development.
