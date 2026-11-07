"""Draw the custom bokeh figures and GIFs from the raw photos in Captures/Custom_Bokeh/.

An out-of-focus light takes the shape of the aperture. Every fairy light behind the scene
shows the pattern the panel held. The script develops each CR2 at half size and cuts the
same square of lights out of every photo of a panel position. It lays the cuts out under
the pattern the panel showed, with one column per pattern and one row per panel position.
It turns each cut 90 degrees anticlockwise so the lights face the same way as the pattern.
It mirrors the cuts from in front of the lens left to right, where the lights came out
reversed. It also writes a looping GIF per character and panel position from the full
frames. Each GIF plays the walk cycle as the camera recorded it.

Every highlight carries a fine mesh, the panel's pixel grid. The script measures its pitch
from the spectrum of the cut in full-size sensor pixels. It writes the pitch and the tilt of
the grid to highlights.csv. The script scales each panel position to its own brightest light.
You can then compare the two photo rows by shape and size alone.

Run from this folder:
  .venv/bin/python bokeh_figure.py          writes bokeh_sprites.png, bokeh_masks.png,
                                            <character>_<position>.gif and highlights.csv to Out/Custom_Bokeh/
  .venv/bin/python bokeh_figure.py --captures ../../../Captures/Custom_Bokeh --out ../../../Out/Custom_Bokeh
"""
import argparse
import csv
import re
import sys
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import rawpy  # noqa: E402
from PIL import Image  # noqa: E402
from scipy.ndimage import gaussian_filter  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CAPTURES = ROOT / "Captures" / "Custom_Bokeh"
OUT = ROOT / "Out" / "Custom_Bokeh"
CAPTURE_APP = ROOT / "App" / "Capturing" / "Ubuntu-System"
SPRITES = CAPTURE_APP / "sprites" / "binary"
sys.path.insert(0, str(CAPTURE_APP))
import patterns  # noqa: E402

# the folder under Captures/Custom_Bokeh, the row label and the centre of the cut as (x, y) in
# full-size px. The lights never moved within a position. One square serves every photo of that
# position. The group picked each square by eye where the lights have the clearest gaps
POSITIONS = [("outside_lens", "In front\nof the lens", (3800, 900)),
             ("inside_lens", "Behind\nthe lens", (3300, 850))]
# where a figure shows a wider square than the one the script measures the mesh on: the centre as
# (x, y) in full-size px and the side in half-size px. Each light spreads wider behind the lens.
# The figure zooms out there and stays above the blurred foreground at the bottom of the frame
SHOWN = {"inside_lens": ((3400, 1100), 1100)}
# the positions whose cuts the figure mirrors left to right after the turn. The lights there came
# out reversed
MIRRORED = {"outside_lens"}
# the file stem and the column title. A sprite stem names a frame in sprites/binary/<character>/
SPRITES_SHOWN = [("knight_binary_walk_1", "Knight 1"), ("knight_binary_walk_2", "Knight 2"),
                 ("link_binary_attack_1", "Link 1"), ("link_binary_attack_2", "Link 2"),
                 ("mario_binary_walk_1", "Mario 1"), ("mario_binary_walk_2", "Mario 2"),
                 ("mario_binary_walk_3", "Mario 3")]
MASKS_SHOWN = [("levin", "Levin"), ("nayar", "Nayar"), ("zhou_a", "Zhou A"), ("zhou_b", "Zhou B")]
# the GIF name and the stems of its frames, in order
GIFS = {"knight": ["knight_binary_walk_1", "knight_binary_walk_2"],
        "link": ["link_binary_attack_1", "link_binary_attack_2"],
        "mario": ["mario_binary_walk_1", "mario_binary_walk_2", "mario_binary_walk_3"]}
# <stem>_<pupil mm>mm_offset_<offset>mm, as the team named the photos
NAME = re.compile(r"^(?P<stem>.+?)_(?P<pupil>\d+(?:\.\d+)?)mm_offset_(?P<offset>[\d-]+)mm$")
CROP = 850            # the side of the square cut, in half-size px
PITCH_RANGE = (8, 60)  # the mesh pitch is looked for between these, in full-size px
GIF_SIZE = (900, 600)
GIF_MS = 400
GAMMA = 1 / 2.2


def photos(folder):
    """{stem: (path, pupil_mm, offset)} for the folder's CR2 files at the folder's usual pupil.
    A photo at another pupil is left out and named"""
    found = []
    for path in sorted(folder.glob("*.cr2")):
        m = NAME.match(path.stem)
        if m:
            found.append((m["stem"], path, float(m["pupil"]), m["offset"]))
    usual = Counter(p for _, _, p, _ in found).most_common(1)[0][0]
    out = {}
    for stem, path, pupil, offset in found:
        if pupil == usual:
            out[stem] = (path, pupil, offset)
        else:
            print(f"left out {path.name}: {pupil:g} mm pupil, the folder's usual pupil is {usual:g} mm")
    return out, usual


def develop(path):
    """linear RGB in [0, 1] at half size with the camera's white balance, and the fraction of
    sensor pixels at the white level"""
    with rawpy.imread(str(path)) as raw:
        clipped = float(np.mean(raw.raw_image_visible >= raw.white_level))
        rgb = raw.postprocess(half_size=True, use_camera_wb=True, no_auto_bright=True,
                              gamma=(1, 1), output_bps=16)
    return rgb.astype(np.float32) / 65535.0, clipped


def cut(img, centre, side):
    """a side x side square about centre, moved inwards where it would leave the frame"""
    h, w = img.shape[:2]
    y = min(max(0, int(round(centre[0])) - side // 2), h - side)
    x = min(max(0, int(round(centre[1])) - side // 2), w - side)
    return img[y:y + side, x:x + side]


def mesh_pitch(lum):
    """the pitch of the strongest periodic texture in a 300 px square about the brightest light
    of the cut, in full-size px, and the tilt of its grid from the sensor's rows and columns in
    degrees: the panel's pixel grid as the sensor sees it"""
    cy, cx = np.unravel_index(np.argmax(gaussian_filter(lum, 20)), lum.shape)
    lum = cut(lum, (cy, cx), 300)
    side = lum.shape[0]
    flat = lum - gaussian_filter(lum, 3)
    window = np.outer(np.hanning(side), np.hanning(side))
    power = np.abs(np.fft.fftshift(np.fft.fft2(flat * window))) ** 2
    c = side // 2
    yy, xx = np.indices(power.shape)
    cycles = np.hypot(yy - c, xx - c)
    lo, hi = 2 * side / PITCH_RANGE[1], 2 * side / PITCH_RANGE[0]   # half-size px cover 2 full-size px
    power[(cycles < lo) | (cycles > hi) | (yy > c)] = 0          # one half plane: each peak has a mirror
    fy, fx = np.unravel_index(np.argmax(power), power.shape)
    tilt = np.degrees(np.arctan2(fy - c, fx - c)) % 90.0
    return 2 * side / cycles[fy, fx], float(tilt - 90.0 if tilt > 45.0 else tilt)


def to_u8(lin, gain):
    return (np.clip(lin * gain, 0, 1) ** GAMMA * 255 + 0.5).astype(np.uint8)


def panel(name, pupil_mm):
    """the pattern as the panel showed it, cut to the pupil, white where light passes"""
    mask = patterns.build(name, diameter_mm=pupil_mm)
    r = int(np.ceil(patterns.pupil_px(pupil_mm) / 2)) + 2
    cy, cx = patterns.cfg.PANEL_H // 2, patterns.cfg.PANEL_W // 2
    return mask[cy - r:cy + r, cx - r:cx + r]


def pattern_name(stem):
    """what the capture app was given: a mask name, or the path of a sprite frame"""
    if (patterns.cfg.MASK_DIR / f"{stem}.txt").exists():
        return stem
    return str(SPRITES / stem.split("_")[0] / f"{stem}.png")


def measure(captures):
    """develops every photo once: the cut of lights, the GIF frame, the mesh pitch and the
    gains for the cuts and the frames, by position"""
    series = {}
    for folder, _, centre in POSITIONS:
        found, pupil = photos(captures / folder)
        crop_white, frame_white, items = 0.0, 0.0, {}
        for stem in [s for s, _ in SPRITES_SHOWN + MASKS_SHOWN]:
            if stem not in found:
                print(f"no {stem} photo in {folder}")
                continue
            path, _, offset = found[stem]
            rgb, clipped = develop(path)
            crop = cut(rgb, (centre[1] / 2, centre[0] / 2), CROP)     # centre is (x, y) in full-size px
            pitch, angle = mesh_pitch(crop.mean(axis=2))
            shown_centre, side = SHOWN.get(folder, (centre, CROP))
            crop = cut(rgb, (shown_centre[1] / 2, shown_centre[0] / 2), side)
            frame = np.stack([np.asarray(Image.fromarray((rgb[..., k] * 65535).astype(np.uint16)).resize(GIF_SIZE, Image.BOX))
                              for k in range(3)], axis=-1).astype(np.float32) / 65535.0
            crop_white = max(crop_white, float(np.percentile(crop.mean(axis=2), 99.5)))
            frame_white = max(frame_white, float(np.percentile(frame.mean(axis=2), 99.9)))
            items[stem] = dict(file=path.name, pupil=pupil, offset=offset, crop=crop, frame=frame,
                               pitch=pitch, angle=angle, clipped=clipped)
            print(f"{folder}/{path.name}: mesh pitch {pitch:.1f} px, tilted {angle:.1f} deg, "
                  f"{100 * clipped:.2f}% clipped", flush=True)
        series[folder] = dict(items=items, crop_gain=1 / crop_white, frame_gain=1 / frame_white, pupil=pupil)
    return series


def figure(shown, series, out):
    rows = 2 * len(POSITIONS)
    cols = len(shown)
    plt.rcParams.update({"font.family": "serif", "font.size": 11})
    fig, axes = plt.subplots(rows, cols, figsize=(1.6 * cols, 1.6 * rows + 0.3), dpi=200,
                             gridspec_kw={"wspace": 0.03, "hspace": 0.05})
    for j, (stem, title) in enumerate(shown):
        for k, (folder, row_label, _) in enumerate(POSITIONS):
            s = series[folder]
            ax_panel, ax_photo = axes[2 * k, j], axes[2 * k + 1, j]
            ax_panel.imshow(panel(pattern_name(stem), s["pupil"]), cmap="gray", vmin=0, vmax=1,
                            interpolation="nearest")
            if stem in s["items"]:
                # turned 90 degrees anticlockwise so the lights face the same way as the pattern
                img = np.rot90(to_u8(s["items"][stem]["crop"], s["crop_gain"]))
                ax_photo.imshow(img[:, ::-1] if folder in MIRRORED else img)
            if k == 0:
                ax_panel.set_title(title)
            if j == 0:
                ax_panel.set_ylabel(f"Panel\n{s['pupil']:g} mm")
                ax_photo.set_ylabel(row_label)
    for ax in axes.flat:
        ax.set_xticks([])
        ax.set_yticks([])
        for side in ax.spines.values():
            side.set_visible(False)
    fig.savefig(out, bbox_inches="tight", pad_inches=0.05)
    plt.close(fig)
    print("wrote", out)


def gifs(series, out_dir):
    for folder, _, _ in POSITIONS:
        s = series[folder]
        for name, stems in GIFS.items():
            frames = [Image.fromarray(to_u8(s["items"][st]["frame"], s["frame_gain"])) for st in stems if st in s["items"]]
            if len(frames) < 2:
                continue
            path = out_dir / f"{name}_{folder}.gif"
            frames[0].save(path, save_all=True, append_images=frames[1:], duration=GIF_MS, loop=0)
            print("wrote", path)


def table(series, path):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["position", "pattern", "file", "pupil_mm", "offset", "mesh_pitch_px", "mesh_tilt_deg", "clipped"])
        for folder, _, _ in POSITIONS:
            for stem, it in series[folder]["items"].items():
                w.writerow([folder, stem, it["file"], f"{it['pupil']:g}", it["offset"], f"{it['pitch']:.1f}",
                            f"{it['angle']:.1f}", f"{it['clipped']:.5f}"])
    print("wrote", path)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--captures", default=str(CAPTURES), help="the folder with inside_lens/ and outside_lens/")
    ap.add_argument("--out", default=str(OUT), help="where the figures, GIFs and CSV go")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    series = measure(Path(a.captures))
    figure(SPRITES_SHOWN, series, out / "bokeh_sprites.png")
    figure(MASKS_SHOWN, series, out / "bokeh_masks.png")
    gifs(series, out)
    table(series, out / "highlights.csv")


if __name__ == "__main__":
    main()
