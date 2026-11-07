# Post-capture reconstruction processing

These scripts recover an all-in-focus image from the photo pair the depth scripts read. They write
to [Out/Post_Capture_Reconstruction](../../../Out/Post_Capture_Reconstruction). Set up the venv
once and run either method:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python pixel_by_pixel_method/reconstruct.py
.venv/bin/python vertical_strip_method/reconstruct.py
```

Run `calibrate.py` in [I-Depth_Estimation](../I-Depth_Estimation) once before either script. Both
scripts import `common.py` and `dfd.py` from that folder. Each script reads the depth map of its
method from `Out/Depth_Estimation/`. It runs the depth script of that method first when the depth
map is missing. The photos sit in [Captures/Depth_Estimation_and_Reconstruction](../../../Captures/Depth_Estimation_and_Reconstruction).
[The depth README](../I-Depth_Estimation/README.md) lists them.

| Script | Reads from `Out/Depth_Estimation/` | Writes to `Out/Post_Capture_Reconstruction/` |
| --- | --- | --- |
| [pixel_by_pixel_method/reconstruct.py](pixel_by_pixel_method/reconstruct.py) | `pixel_by_pixel_method/depth_mm.npy` and `settings.json` | `pixel_by_pixel_method/all_in_focus.png` |
| [vertical_strip_method/reconstruct.py](vertical_strip_method/reconstruct.py) | `vertical_strip_method/depth_mm.npy` | `vertical_strip_method/all_in_focus.png` |

## How the reconstruction works

Each photo is the sharp scene blurred by the PSF of its mask at the distance of the scene. At one
distance the two PSFs lose detail at different frequencies. The scripts deblur both photos together
with a joint Wiener filter. Each mask then fills the gaps of the other. The scripts run this deblur
at every calibrated distance. Each pixel or strip takes its value from the deblur at its own
distance.

The pixel by pixel script takes the noise weight `lam` from the depth run's `settings.json`. The
default is 0.3. The vertical strip script uses `LAM` 0.5. It adds `RIDGE` 0.003 to the denominator
to keep the division bounded where both PSFs lose a frequency. Set `SCENE` and `DOWNSAMPLE` at the
top of the vertical strip script to match its depth script.

## Pitfalls

- **Depth errors.** A pixel or strip at the wrong distance gets the wrong deblur. Look for ringing
  or leftover blur in the all-in-focus image. Both mark a mistake in the depth map.
- **Stale depth maps.** The scripts reuse a depth map that already exists. Rerun the depth script
  of the method after you change the photos or the calibration.
