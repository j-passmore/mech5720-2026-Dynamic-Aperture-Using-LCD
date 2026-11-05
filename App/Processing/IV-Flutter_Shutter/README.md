# Flutter shutter processing

These scripts deblur and score the flutter photos and draw the two key figures. The
[root README](../../../README.md) has the capture procedure. Set up the venv once:

```
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

| Script | What it does |
| --- | --- |
| [flutter_figure.py](flutter_figure.py) | It redraws the two key figures, in front of the lens and inside the tube, from the photos in `Captures/Flutter_Shutter/` into `Out/Flutter_Shutter/`. |
| [flutter_score.py](flutter_score.py) | It checks a whole run and scores its coded, box and impulse photos against the reference. It also draws the close-ups of the "95". |
| [flutter_deblur.py](flutter_deblur.py) | It deblurs one coded photo with the code from its trace and scores the result against the reference. |
| [rawframe.py](rawframe.py) | It loads a CR2 or DNG as a green channel image with its ISO and exposure time. |

`flutter_95_template.npy` holds the "95" cut from a reference photo. `flutter_score.py` finds it
in each reference to centre the close-ups.

## The key figures

[flutter_figure.py](flutter_figure.py) redraws the report's two flutter figures from the photos
in [Captures/Flutter_Shutter](../../../Captures/Flutter_Shutter) into
[Out/Flutter_Shutter](../../../Out/Flutter_Shutter). Each takes about a minute:

```
.venv/bin/python flutter_figure.py
```

Each column is one run. `Captures/Flutter_Shutter/` holds each run's still reference
and its coded photo as CR2 files, 226 MB in all, with the coded photo's trace beside them. The
reference is `<run>_100ms_invert_00_reference.cr2`. The script skips a figure whose photos are missing and names
the files it wants.

| Figure | Column | Run | Coded photo | Blur |
| --- | --- | --- | --- | --- |
| In front of the lens | f/5.6 | Run2_f5_6 | `Run2_f5_6_100ms_invert_02_coded.cr2` | 375 px |
| In front of the lens | f/11 | Run19 | `Run19_100ms_invert_01_coded.cr2` | 475 px |
| In front of the lens | f/22 | Run2_f22 | `Run2_f22_100ms_invert_02_coded.cr2` | 325 px |
| Inside the tube | f/5.6 | f56_run1_lcd_inside | `f56_run1_lcd_inside_100ms_invert_02_coded.cr2` | 500 px |
| Inside the tube | f/11 | f11_run1_lcd_inside_2 | `f11_run1_lcd_inside_2_100ms_invert_02_coded.cr2` | 375 px |
| Inside the tube | f/22 | f22_inside_lcd_run2 | `f22_inside_lcd_run2_100ms_invert_02_coded.cr2` | 400 px |

The script deblurs each coded photo with 40 Richardson-Lucy iterations at the blur length that
`flutter_score.py` found. It fits each panel to its reference by a gain and an offset. It cuts
every panel around the "95" the way `flutter_score.py` does. It prints the MSE of each deblur
against its reference. In front of the lens the runs give MSE 0.00285 at f/5.6, 0.00122 at f/11
and 0.00470 at f/22. Inside the tube they give 0.00509, 0.00484 and 0.00674. All six match the
RL40 scores that `flutter_score.py` saved. The report quotes the f/11 one in front of the lens.

## Scoring a run

The window downloads the photos of a Run to `App/Capturing/Ubuntu-System/captures/flutter/`.
Each photo arrives as a `.cr2`, a `.jpg` and a `.dng`. The run's
`<Name>_<chop>ms_<method>_manifest.json` sits beside them. Git ignores these folders, because the
raw photos of one run come to hundreds of megabytes.

[flutter_score.py](flutter_score.py) scores a run by its Name. It adds `_100ms_invert` to the
Name, which means it takes only runs at Chop 100 with Invert. `--dir` names the folder that holds
the photos. The script resolves that folder from its own location, whatever folder you run it
from.

```
.venv/bin/python flutter_score.py Run2_f22 --dir ../../Capturing/Ubuntu-System/captures/flutter
.venv/bin/python flutter_score.py Run2_f22 --dir ../../Capturing/Ubuntu-System/captures/flutter --pictures-only
```

`--pictures-only` redraws the pictures from the saved scores. The script checks the manifest and
traces first. It reads each photo's raw level, clipping and EXIF. It sweeps the coded and box
photos over blur lengths from 200 to 1200 px with the car moving left. It scores every photo
against the run's reference by MSE, NCC and detail. Detail is the correlation of the 8 to 32 px
features that make up the strokes of the "95". Each photo gets a score with a Wiener filter at
K = 0.05 and with 40 Richardson-Lucy iterations. It also gets a score at its best setting. The
scores and pictures land in `out/flutter/<run>/`. The EXIF comes from each photo's DNG. A run
without DNGs fails here.

## Deblurring one photo

[flutter_deblur.py](flutter_deblur.py) stretches the code from the trace over a blur length along
the rows. It removes that blur row by row with a Wiener filter. It then aligns the result to the
averaged reference photos. It scores the result by MSE, PSNR and NCC. `--sweep` tries a range of
blur lengths in both directions and keeps the lowest MSE. Give it the run's prefix:

```
.venv/bin/python flutter_deblur.py ../../Capturing/Ubuntu-System/captures/flutter/Run1actual_100ms_invert --blur 100
.venv/bin/python flutter_deblur.py ../../Capturing/Ubuntu-System/captures/flutter/Run1actual_100ms_invert --sweep 100:5200:100
```

The results land in `out/flutter/<run>/`. `compare.png` holds the coded, deblurred and reference
photos one above the other. `scores.csv` holds every blur length tried. The alignment searches up
to half the frame width. Check the shift column. A deblurred photo that lands hundreds of pixels
from the coded photo has matched the wrong part of the scene. Its MSE does not count.

## Pitfalls in the results

- **The coded and box photos** of one run seldom got the same blur. A box photo with less blur
  has the easier job. Only the f/22 coded and box photos in front of the lens came within
  8 percent of each other.
- **The car's reflections** and the lamp light on it change along the track. The score fits one
  brightness and contrast to the whole picture. A photo taken 1,000 px from the reference spot
  scores several times worse however sharp it is. Stand the car for the reference where it will
  be during the coded photo.
- **LibRaw 0.22** reads these DNGs with a black level of 2088 to 2151. That darkens a photo by
  about 5 percent and clips the faint edge of a point spread function. The scripts read the CR2
  through rawpy for that reason.
