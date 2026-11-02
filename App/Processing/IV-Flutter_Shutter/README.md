# Flutter shutter processing

The flutter shutter of Raskar, Agrawal and Tumblin opens and closes the shutter in a binary
code during one exposure, so the blur of a moving target stays invertible. On this rig the
LCD panel is the shutter. The capture app in
[Capturing/Ubuntu-System](../../Capturing/Ubuntu-System/README.md) takes the photos and
`flutter.py` there designs the code. Its Flutter shutter section says how to set up and run
a capture. The scripts here deblur the coded photo and score it, with the box and impulse
photos, against a sharp reference.

Run every command below from this folder.

## Files

| File | Purpose |
| --- | --- |
| [flutter_deblur.py](flutter_deblur.py) | Deblurs a flutter run's coded frame with the code from its trace and scores it against the reference frames |
| [flutter_score.py](flutter_score.py) | Checks a flutter run and scores its coded, box and impulse photos against the reference, with the close-up pictures. Uses `flutter_95_template.npy` to find the "95" |
| [rawframe.py](rawframe.py) | Loads a CR2 or DNG as a green-channel float image, with its ISO and exposure time. `flutter_deblur.py` uses it |
| `flutter_95_template.npy` | The "95" on the target car, cut from a reference photo and binned 4 x 4. `flutter_score.py` finds it in each run's reference to centre the close-ups |
| [requirements.txt](requirements.txt) | The Python packages, for `pip install -r requirements.txt` |

## Setup

```
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

The usage lines in the scripts run them as `.venv/bin/python`. Where they say the code
folder, they mean this folder.

## The photos

A Run on the Flutter tab downloads `<Name>_<chop>ms_<method>_manifest.json` and, for each
photo, `<Name>_<chop>ms_<method>_<index>_<tag>.cr2` and `.dng`. The coded, box, leakage,
reference and dark photos also get a `.json` trace with the code, chop, lead and tail.
With the window started from the capture folder with `--outdir captures`, they land in
`Capturing/Ubuntu-System/captures/flutter/`. The raw photos stay out of git.

## Deblurring one run

[flutter_deblur.py](flutter_deblur.py) deblurs the coded frame. It stretches the code from
the trace over a blur length along the rows and removes it row by row with a Wiener
filter. It then aligns the result to the averaged reference frames and scores it by MSE,
PSNR and NCC. `--sweep` tries a range of blur lengths in both directions and keeps the
lowest MSE. Give it the run's prefix:

```
python flutter_deblur.py ../../Capturing/Ubuntu-System/captures/flutter/Run1actual_100ms_invert --blur 100
python flutter_deblur.py ../../Capturing/Ubuntu-System/captures/flutter/Run1actual_100ms_invert --sweep 100:5200:100
```

The results land in `out/flutter/<run>/`: `compare.png` holds the coded, deblurred and
reference frames one above the other, and `scores.csv` holds every blur length tried. The
alignment searches up to half the frame width, so check the shift column. A deblurred frame
that lands hundreds of pixels from where the coded frame did has matched the wrong part of
the scene, and its MSE does not count.

## Scoring a run

[flutter_score.py](flutter_score.py) checks and scores a run that took reference, impulse,
coded and box photos. Give it the run's Name from the Flutter tab. It adds `_100ms_invert`,
the Chop and method of the light-level runs, so it only takes runs at Chop 100 with Invert.
`--dir` is the folder that holds the photos, taken from this folder whatever folder you run
it from. Its default is `captures/flutter` in this folder, for photos copied here.

```
python flutter_score.py Run2_f22 --dir ../../Capturing/Ubuntu-System/captures/flutter
python flutter_score.py Run2_f22 --dir ../../Capturing/Ubuntu-System/captures/flutter --pictures-only     # redraw the pictures from the saved scores
```

It checks the manifest and traces, reads each photo's raw level, clipping and EXIF, sweeps
the coded and box photos over blur lengths from 200 to 1200 px with the car moving left, and
scores every photo against the run's reference: MSE, NCC and detail, the correlation of the
8 to 32 px features that make up the strokes of the "95". Each photo is scored with the f/11
settings, lam 0.05 and 40 Richardson-Lucy iterations, and again at its best setting. The
scores and pictures land in `out/flutter/<run>/` in this folder. It uses `flutter_deblur.py`
for loading, deblurring and the first alignment, and `flutter_95_template.npy` to centre the
close-ups. The EXIF comes from each photo's DNG, so the run needs the DNGs the server makes
with dnglab.

## Results

The scored runs behind the report are in the `code/captures/flutter_5s_ISO100_*` folders of
[ethandoddo/MECH5720_MajorProject](https://github.com/ethandoddo/MECH5720_MajorProject/tree/main/code/captures),
one folder for each aperture, f/5.6, f/11 and f/22, with the LCD outside and inside the
lens. Each holds `data.md` with the settings, the results and why those photos, `data.csv`
and the pictures. The outside-lens folders also hold `results.json` and the `score.py` that
made them. The .cr2 and .dng photos stay on the lab laptop.
