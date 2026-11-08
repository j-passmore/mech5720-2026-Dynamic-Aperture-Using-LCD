# Depth estimation processing

These scripts turn the coded aperture photos in
[Captures/Depth_Estimation_and_Reconstruction](../../../Captures/Depth_Estimation_and_Reconstruction) into depth maps in
[Out/Depth_Estimation](../../../Out/Depth_Estimation). The [root README](../../../README.md) has the
capture procedure. Set up the venv once:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

The group tried two methods on the same photos. Emma wrote the pixel by pixel method after Zhou,
Lin and Nayar. Jayden wrote the vertical strip method. Both read the calibration that
`calibrate.py` builds.

| Script | What it does |
| --- | --- |
| [calibrate.py](calibrate.py) | It averages the dark frames into a master dark. It cuts a PSF pair out of the point source photos at each distance in `distances.yaml`. |
| [psf_fourier.py](psf_fourier.py) | It draws the spectrum of each PSF pair. The two masks lose detail at different frequencies. |
| [pixel_by_pixel_method/estimate_depth.py](pixel_by_pixel_method/estimate_depth.py) | It picks a distance for every pixel. |
| [vertical_strip_method/estimate_depth.py](vertical_strip_method/estimate_depth.py) | It picks one distance for each vertical strip of the photo. |
| [common.py](common.py) | It holds the folder paths and the loader that reads the green channel of a CR2. |
| [dfd.py](dfd.py) | It holds the deblur that the depth and reconstruction scripts share. |

The scripts in [II-Post_Capture_Reconstruction](../II-Post_Capture_Reconstruction) import
`common.py` and `dfd.py` from this folder.

## Running the scripts

Run the calibration once and then either method. Each script finds its folders from its own
location. You can run it from any folder:

```bash
.venv/bin/python calibrate.py --allow-saturated
.venv/bin/python psf_fourier.py
.venv/bin/python pixel_by_pixel_method/estimate_depth.py
.venv/bin/python vertical_strip_method/estimate_depth.py
```

| Script | Writes to `Out/Depth_Estimation/` |
| --- | --- |
| `calibrate.py` | `calibration/master_dark.npy`, `calibration/calibration.npz` and `calibration/psf_pairs.png` |
| `psf_fourier.py` | `calibration/psf_fourier.png` |
| Pixel by pixel | `pixel_by_pixel_method/depth_heatmap.png`, `depth_map.png`, `depth_map_confident.png`, `captured_mask1.png`, `depth_mm.npy`, `confidence.npy` and `settings.json` |
| Vertical strip | `vertical_strip_method/depth_map.png`, `depth_steps.png` and `depth_mm.npy` |

## The photos

`Captures/Depth_Estimation_and_Reconstruction/` keeps the folder layout of the capture laptop:

| Path | Photos |
| --- | --- |
| `fpn/d1.CR2` to `d10.CR2` | Ten lens cap dark frames, which `calibrate.py` averages into the master dark |
| `Scale_1/psfs_v2/m{1,2}_psf{1..5}.CR2` | A torch at each distance through mask 1 and mask 2, the set the report used |
| `Scale_1/psfs/mask{1,2}_psf{1..5}.CR2` | The first PSF set. Every photo in it clips, so the group shot the second set |
| `Scale_1/mask{1,2}.CR2` | The scene pair both methods read |
| `ambient/amb*.CR2` | Ten ambient frames at the scene settings. They average within 0.1 DN of the dark frames, so the room light adds nothing |
| `black_lvl.CR2` | One frame for the black level of the sensor, 2049 DN |
| `distances.yaml` | The distance from the panel to the torch for each PSF |

`distances.yaml` records the settings: 2 s, ISO 200 and f/5 with the lens at 35 mm. `--scene-dir` picks
another scene pair for the pixel by pixel method. `SCENE` at the top of the vertical strip script
does the same for that method.

## How the methods work

Both methods start from one model. Each photo is the sharp scene blurred by the PSF of its mask
at the distance of the scene.

The pixel by pixel method follows Zhou, Lin and Nayar. For each distance it deblurs the two
photos together with the PSF pair of that distance. It blurs the result again with the same pair
and measures how far it lands from the photos. Each pixel takes the distance with the smallest
error over a 31 px window. The script marks a pixel low confidence when the pixel is dark or the
second best distance comes close.

The vertical strip method compares spectra and skips the deblur. In each 448 px window it
compares the ratio of the two spectra with the ratio each PSF pair predicts. Each vertical strip
takes the most common distance of its windows. The script then moves each boundary to the nearest
strong vertical edge in the photo. The method assumes the objects stand side by side.

## Pitfalls

- **Saturated PSFs.** A clipped torch flattens the core of the PSF, where the coded pattern sits.
  `calibrate.py` refuses clipped PSFs unless you pass `--allow-saturated`. In the report run 14%
  of the energy of the 350 mm mask 1 PSF sat in clipped pixels. The figures carry "TEST:
  saturated PSFs" in their titles for that reason.
- **Locked focus.** The PSFs hold only at the zoom, focus and f-number of the scene photos. Keep
  the lens on MF and leave the focus ring alone between the PSF photos and the scene photos.
- **Two PSF sets.** `calibrate.py` reads `Scale_1/psfs_v2/` by default, the set the report used.
  `calibrate.py --psf-dir Scale_1/psfs --psf-name "mask{mask}_psf{index}.CR2"` builds the
  calibration from the first set instead.
