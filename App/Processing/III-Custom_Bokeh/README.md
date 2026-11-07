# Custom bokeh processing

[bokeh_figure.py](bokeh_figure.py) draws the bokeh figures and GIFs from the raw photos in
[Captures/Custom_Bokeh](../../../Captures/Custom_Bokeh) into
[Out/Custom_Bokeh](../../../Out/Custom_Bokeh). The [root README](../../../README.md) has the
capture procedure. Set up the venv once. The script takes about half a minute:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python bokeh_figure.py
```

## The photos

`Captures/Custom_Bokeh/` holds the raw photos of 28 October 2026 as CR2, 443 MB in all.
`outside_lens/` has the panel in front of the lens at a 9.5 mm pupil. `inside_lens/` has it
behind the lens in the extension tube at 5.5 mm. Each folder holds the four masks and seven
sprite frames: Knight walk 1 and 2, Link attack 1 and 2 and Mario walk 1 to 3. Every photo is 5 s at ISO 100
with the lens at 53 to 55 mm and its iris open. The file names read
`<pattern>_<pupil>mm_offset_<offset>mm`, which the group typed by hand. No manifest sits beside
the photos. `inside_lens/` also holds one Mario photo at a 10 mm pupil.

## What the script does

The script develops each CR2 at half size with the camera's white balance. It cuts the same
square of lights out of every photo of a panel position. A table at the top of the script fixes
each square where the lights have clear gaps between them. The script turns each square 90
degrees anticlockwise so the lights face the same way as the pattern. The lights in front of the
lens came out reversed. The script mirrors those squares left to right as well.

The mesh pitch comes from an 850 px square before the turn. The figures show a 1,100 px square
behind the lens since each light spreads wider there. The pattern rows come from the capture
app's own pattern code at the pupil in the file name and the default image size. The script
scales each photo row to its own brightest light. You can then compare the rows by shape and
size alone.

The script writes `bokeh_sprites.png`, `bokeh_masks.png`, one GIF per character and panel position and
`highlights.csv`. The GIFs play each walk cycle as the lights show it, three frames for Mario and
two each for the Knight and Link.

![The three Mario walk frames as the lights show them, with the panel in front of the
lens](../../../Out/Custom_Bokeh/mario_outside_lens.gif)

*The GIF plays the three Mario walk frames as the lights show them, with the panel in front of
the lens.*

![The same walk with the panel behind the
lens](../../../Out/Custom_Bokeh/mario_inside_lens.gif)

*The GIF plays the same walk with the panel behind the lens.*

## The panel's pixel grid

Every highlight carries a fine mesh. It is the panel's pixel grid, the gaps between its 0.219 mm
pixels, cast onto the sensor with the pattern. The script measures the pitch of the mesh from
the spectrum of the brightest light in each cut and writes it to `highlights.csv`. The pitch
times the pupil in panel pixels gives how far the pupil spreads on the sensor.

| Panel position | Pupil | Mesh pitch | Pupil on the sensor |
| --- | --- | --- | --- |
| In front of the lens | 9.5 mm, 43 panel px | 18.6 to 19.3 px | about 810 px |
| Behind the lens | 5.5 mm, 25 panel px | 42.9 px | about 1,080 px |

The grid sits about 5 degrees off the sensor's rows in front of the lens and square to them
behind the lens. Behind the lens each panel pixel covers 2.3 times as many sensor pixels. The
smaller pupil spreads wider than the larger one in front as a result. Nine of the eleven photos
behind the lens give 42.9 px. Nayar gives 46.2 px and Mario 3 gives 15 px because the script
picked a different peak in those two.

## Pitfalls

- **The mesh** prints in every highlight. A laser-cut card has no pixel grid and gives a clean
  shape. You give up that clean shape for one the panel can change in a frame.
- **Light.** The lights needed 5 s at ISO 100 through the panel. Anything that moves in that time
  blurs.
- **Straight edges.** Behind the lens several highlights end in a straight edge that the pattern
  does not have.
- **No manifest.** The group named the bokeh photos by hand. Take the next set through
  `capture_series.py`. Each photo then gets a manifest with its pupil, image size and offset.
