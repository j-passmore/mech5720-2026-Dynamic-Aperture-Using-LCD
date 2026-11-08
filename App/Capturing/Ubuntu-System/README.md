# The capture app

The capture app runs the panel and the camera from the Ubuntu laptop. `server.py` owns the
panel and the camera. `camview_capture.py` is the window. `capture_series.py` does the same jobs
from the command line. The [root README](../../../README.md) covers the build, the setup and the
capture procedure for each experiment. This page is the manual for the app itself.

## Running the rig

The rig runs in two terminals. Start both in this folder with the venv active:

```
source .venv/bin/activate
python server.py --display arduino --camera gphoto
```

The server prints `display=arduino camera=gphoto pupil 27.8 mm = 126.8 px` once the panel and the
camera are both up. `--display window --camera dummy` runs everything with nothing plugged in.
`python show.py <pattern> --backend arduino` puts one pattern on the panel from the second
terminal. Start the window there:

```
python camview_capture.py --outdir captures
```

`--host` on either client points at another machine that runs the server. Set the ISO and
shutter speed under Camera in Controls. The window has four panes:

- **Camera View** streams the camera's live view. With live view off it shows the last photo.
- **Aperture Panel** shows the image on the LCD, pixel for pixel.
- **Controls** holds the pattern list, the pupil diameter, the camera settings and the sequence
  runner. Its Preview shot and Capture and save buttons take single photos.
- **Experiments** holds one tab for each experiment the app captures: Depth, Refocus and Flutter.

Live view drains the camera battery faster than anything else. Tick Live view to frame the scene
and untick it before a run. Live view turns itself off when no window has taken a frame for
30 s. It also stops after 10 min in one go. `LIVEVIEW_IDLE_S` and `LIVEVIEW_MAX_S` in `config.py`
set those limits. Closing the window turns it off too. The stream pauses around each capture
because one process owns the USB link.

## Running an experiment

1. Place the target and type its distance into Target distance mm in the Experiments window.
2. Set Repeats to 5 for the error bars.
3. Pick the tab and press the button for the capture. The progress bar at the top of the window
   counts the steps.
4. When the window says Waiting for you, do what the prompt says and press Continue. The flutter
   Run shows each prompt in a pop-up instead. Stop ends the run after the current step.
5. Find the photos in `captures/<experiment>/` once the run ends. The manifest sits beside them.
   The Activity line in Controls says when the download has finished.

Every Experiments button uses the Settle, Pupil mm, Image size, Rotation and Offset set in
Controls. Target distance goes into the file names. Repeats runs the whole list that many times.

## The serial link

The server finds the board on its own. An Uno shows up as `/dev/ttyACM0`. A clone with a CH340
chip shows up as `/dev/ttyUSB0`. Set `ARDUINO_PORT` in `config.py` when the laptop has more than
one serial device. `ARDUINO_BAUD` must match `BAUD` in the sketch.

The sketch writes each run of pixels to the panel as the bytes arrive. It needs no frame buffer
and fits in an Uno's 2 KB of RAM. The laptop sends each frame a few bytes at a time. One byte can
be a run of 128 pixels. The panel takes hundreds of microseconds to draw that run, while the next
bytes arrive every 20 µs. A single burst would overflow the Uno's 64 byte receive buffer. The
sketch sends a `c` for every 16 bytes it takes out of the buffer. The laptop keeps at most
`ARDUINO_WINDOW`, 48 bytes, in flight. `ARDUINO_CREDIT` must match `CREDIT_BYTES` in the sketch.

The `st7735` backend drives the panel from a Raspberry Pi over SPI instead, on the pins in
`config.py`. It needs `adafruit-circuitpython-rgb-display`.

## Patterns

[patterns.py](patterns.py) draws every pattern in millimetres on the lens pupil and converts it
to panel pixels at `PANEL_PITCH_MM`, 0.219 mm per pixel. A 50 mm lens at f/1.8 has a 27.8 mm
pupil. That is 127 pixels, which almost fills the 128 pixel width. Change `FOCAL_MM` and
`F_NUMBER` in `config.py` for another lens. Pupil mm overrides both for one run.

`open` is a clear disc the size of the pupil. `white` clears the whole panel and `black` shuts it.
A name from `masks/` draws that cell grid in the Lab 3 format. `zhou_a` and `zhou_b` are the
13 x 13 coded pair from figure 4 of Zhou, Lin and Nayar (ICCV 2009). `levin` and `nayar` are the
Lab 3 masks. `scan0` to `scan8` light one tile each of a 3 x 3 grid. `scan5_0` to `scan5_24` do
the same for a 5 x 5 grid. `python patterns.py` writes every named pattern to `out/patterns/`.

An image pattern is any PNG or GIF the server can read, given by its path. [sprites/](sprites)
holds the character animations the custom bokeh used. [make_sprites.py](sprites/make_sprites.py)
beside them draws Link, Mario, a Knight and a Terraria miner from character grids as 128 x 160
frames, one PNG per frame and a looping GIF. The characters come from Super Mario Bros., The
Legend of Zelda, Realm of the Mad God and Terraria; [the sprites README](sprites/README.md)
credits them. The `binary` set is a transparent character on
black. The `grey` set shuts some regions at mid grey instead. In an image with transparency, the
transparent pixels are open like clear glass. Every opaque pixel is shut, black and grey alike.
In an image with no transparency, white is open. The image's longest side spans the pupil
diameter times the image size. Image size is 100 percent by default. The Image size slider in
the window and `--image-scale` on the command line set it. At 71 percent a square image fits
inside the round pupil. Above 100 percent the edges are cut. Image size changes images only and
leaves the built-in patterns alone. The manifest records it as `image_scale`.

The Rotation slider turns any pattern anticlockwise about the panel centre, in degrees. The -90
and +90 buttons turn it a quarter at a time. The 0 button puts it back. `--rotate` does the same
on the command line. Steps of 90 degrees are exact because the centre sits between pixels. Other
angles resample to the nearest pixel. The manifest records the angle as `rotation_deg`. Every
photo's `_panel.png` shows the turned pattern. The scan tile positions assume an unturned mask.
Judge rotated sessions with that in mind. Rotation turns `white` as well, which leaves black
corners. Keep it at 0 for the flutter photos.

The Offset arrows under Rotation move the pattern one panel pixel (0.219 mm) at a time. They keep
moving it while held. Offset px takes two typed numbers, right then up. Centre puts the pattern
back. The move comes after the rotation, which keeps up as up at any angle. The window stops the
move when the pattern's centre reaches the panel edge. `--offset RIGHT UP` does the same on the
command line. Whole pixels never resample. Anything moved off the panel is cut. `white` and
`black` never move. The card photos and the transmission sequence keep the full panel as a
result. The flutter codes also fill the whole panel at any offset. The manifest records the move
as `offset_px`, [right, up]. The scan tile positions assume a centred mask. Judge moved sessions
with that in mind.

Changing Pupil mm, Image size, Rotation or Offset redraws the panel 0.4 s after the value stops
changing.

Browse... and Add files... open a file chooser that needs zenity, which Ubuntu ships. Browse...
fills the Image field. Show image puts the file on the panel. A GIF shows its first frame. Play
GIF loops a GIF on the panel at its own frame delays divided by the GIF speed, from 0.25x to 4x.
Moving the slider during playback changes the speed without a restart. Stop ends playback. A new
pattern, a capture or a sequence ends it too, which holds the panel still for every exposure.
The panel cannot change faster than one frame per draw, about 95 ms on an Uno. Shorter delays
stretch to that.

## Sequences

[config.py](config.py) names three sequences in `SEQUENCES`:

- `pair` takes open, coded A, coded B and open. The two open photos show whether anything moved
  during the pair. The coded pair feeds depth estimation.
- `scan` takes open, the nine sub-aperture tiles and open again, for post-capture refocus.
- `transmission` takes white, black and open, which gives the stops lost to the panel.

The `images` sequence runs a list built with Add files... and Add pattern. Add files... takes
several files at once. Add pattern adds the pattern selected above, which suits `open` as a
control photo between shapes. Up, Down, Remove and Clear edit the list. The line under the list
counts the photos, with one photo for each GIF frame. The server opens each file by its path.
Keep the files on the machine that runs the server.

A sequence entry can be a step object in place of a name. This step pauses the job with its
prompt on show:

```
{"pattern": "white", "tag": "card_open", "prompt": "Fit the open card"}
```

Continue in the window or `--go` on the command line ends the pause. The server then shows the
pattern and fires. `"camera": {"shutterspeed": "1/250"}` sets the camera first.
`"diameter_mm": 8.9` sizes that one photo. `"capture": false` shows the pattern and takes no
photo. A step of only `{"prompt": "Take the lens cap off"}` pauses and takes nothing. A step
with `"code"` and `"chop_ms"` plays a flutter shutter code, as The Flutter tab describes. Stop
ends the job after its current step. A job that stops or fails still writes its manifest with
the photos it took.

## Command line

[capture_series.py](capture_series.py) does the same jobs from the command line:

```
python capture_series.py --status
python capture_series.py --set iso=100 --set shutterspeed=1/30
python capture_series.py --pattern levin
python capture_series.py --sequence pair --label 700mm --outdir captures/depth
python capture_series.py --sequence scan --label 1000mm --outdir captures/refocus
python capture_series.py --patterns open star.png walk.gif open --label shapes
python capture_series.py --play walk.gif --speed 2
python capture_series.py --stop
python capture_series.py --code designed --chop 100 --label flutter      # one coded photo on M
python capture_series.py --code 1011001 --chop 50 --no-capture           # play it and record the trace
python capture_series.py --go                                            # a paused job carries on
python capture_series.py --abort                                         # stop the running job
```

## Files and manifests

Photos land in `<outdir>/<label>_<index>_<pattern>` as `.cr2`, `.jpg` and `.dng`. A
`<label>_manifest.json` sits beside them. The manifest records when each pattern went up and when
the shutter fired. It also keeps the pupil diameter, the pixel pitch and the panel image for
every photo. The CR2 files open in rawpy the same way the Lab 3 DNGs did. The DNGs open in the Lab
3 MATLAB scripts. The server makes the DNGs after the last photo of a sequence, at about a second
each. They never delay a shutter. Without dnglab the CR2 files still save. The window says
why the DNGs are missing.

An image file takes the name of its stem, `star` for `~/Pictures/star.png`. Frame 3 of
`walk.gif` is `walk_f03`. The manifest keeps the full path in `pattern`, `walk.gif#3` for a GIF
frame. It keeps the file name part in `tag`.

## Panel timing

The manifest's `shown_s` is when the sketch's acknowledgement arrived. That comes about a
millisecond after the SPI write to the panel ends. The sketch writes each run as it arrives. The
serial transfer and the SPI write overlap. The write sets the frame time. A CH340 Uno takes
95 ms for the open disc, white, black and the scan tiles. It takes 105 ms for the Zhou pair and
130 ms for the Lab 3 masks. Random noise takes 0.8 s. A one pixel checkerboard takes 1.5 s, the
worst case. `python display.py` prints the serial cost of every pattern. The open disc costs 8 ms
at 500 kbaud. Every named pattern costs under 15 ms.

The liquid crystal then takes its own response time to settle, which sets the shortest useful
flutter chop. The datasheet gives 15 to 35 ms. The comment on `FLUTTER_CHOP_MS` in `config.py`
says 30 to 70 ms. Nobody has measured this panel to settle which figure is right.

## The Depth tab

Use a point source at each distance for PSF set. Use a textured target at each distance for
Pair, Singles and Card pair.

- **PSF set** takes open, pattern A, pattern B, Levin and black.
- **Pair** takes open, A, B and open.
- **Singles** takes each coded pattern twice. One pattern then gets the exposure of the pair.
- **Card pair** takes the same four photos through hand-fitted cards with the panel white. It
  pauses before each card. The cards give the baseline for what the panel costs.

Patterns A and B start as `zhou_a` and `zhou_b`. Type another mask name from `masks/` or pick a
PNG or GIF with Browse A... and Browse B.... Image size in Controls sizes an image. The file
names read `depth1000mm_pair`, which keeps the distance with the photos. A pair other than the
Zhou pair adds its names, as in `depth1000mm_pair_star_heart`. It never overwrites the Zhou files.

## The Refocus tab

- **Scan 3x3** and **Scan 5x5** take open, every tile, black and open. The 5 x 5 scan takes 28
  photos.
- **f/5.6 frame** takes one open disc 8.9 mm wide. That matches the depth of field the 3 x 3
  refocus reaches. It is the one-photo baseline.
- **Lens focus** pauses for you to focus the lens on the target by hand. It then takes the
  in-focus reference for SSIM.

## The Flutter tab

On this rig the panel is the shutter. The camera takes one photo on M at its own shutter speed.
The panel is black when the shutter opens. The board then plays the code on the panel from its
own clock. The panel stays black until the shutter closes. The curtains move in the dark, which
means every row of the sensor sees the same code. The 60D's 1/250 s curtain travel does not
matter.

### Switching the panel

The board switches the panel in one of two ways. Invert sends the controller's one-byte invert
command. That flips every pixel in the time the liquid crystal takes, 15 to 35 ms by the
datasheet. Frame write rewrites every pixel, which takes 41 ms at the Uno's 8 MHz SPI clock.
Chops under about 130 ms slip with Frame write. Invert is the better method. Frame write is the
fallback for a panel that Invert does not take fully clear. The sketch holds the whole run to a
16 bit millisecond clock. Lead, code and tail together must fit `FLUTTER_MAX_S`, 60 s.

[flutter.py](flutter.py) designs the code. It searches random 32-chop codes with 16 chops open,
first and last open. It keeps the code with the highest minimum in the padded spectrum. The
search is seeded. Every machine designs the same code, `10001101101001011000001111010101`. The
manifest records the code by its text. A box exposure of the same length scores 0. The designed
code scores 0.075. The Custom field takes any code of up to 64 chops.

### The controls

Chop ms sets the chop length. Lead ms is how long the panel stays black before the code. The
shutter must have opened by then. The default of 1 s is a guess at how long gphoto2 takes to
fire. Check the first real coded photo for every chop. A small bright dot on the target streaks
in the code's on and off pattern. A missing start means Lead is too short. A missing end means
the shutter speed is too short. Tail ms is how long the panel stays black after the code, 200 ms
by default. Blur px gives the target speed for that much blur over the code.

The shutter opens during Lead. The shutter speed therefore has to cover Lead + code. That is
4.2 s for a 1 s Lead and 32 chops of 100 ms, which means 5 s on the 60D. The panel stays black
for the rest of the exposure, which adds only leakage. Run does not start on a shorter shutter
speed. The table lists the captures Run can take.

| Capture | Panel | Camera | Target |
| --- | --- | --- | --- |
| reference | open for the code's length | the shutter speed under Photo | still |
| impulse | open | the Impulse shutter speed | moving |
| coded | plays the code | the shutter speed under Photo | moving |
| box | open for the code's length | the shutter speed under Photo | moving |
| leakage | black for the code's length | the shutter speed under Photo | moving |
| dark | black for the code's length | the shutter speed under Photo with the lens cap on | any |

Run takes them in that order, Repeats times each. A pop-up stops the run three times: before the
reference, before the moving photos and before the darks. Each pop-up says what to change at the
rig and what the photos are for. The impulse, coded, box and leakage photos then run straight
through with their repeats. The target never has to stop. Box and leakage keep the timing of the
coded photo. All three collect the same stray light.

The car keeps moving between photos. Each 5 s photo takes about 7.5 s in all. The pop-up says how
far the car travels. Start it near the edge of the frame it moves away from. With all six ticked
at 62.5 px/s, the car travels about 1,600 px with Repeats 1. It travels 3,200 px with Repeats 2.

LCD only flutter shutter plays the code on the panel Repeats times with no camera. Use it to
watch the panel switch. Check Invert with it before anything else.

Capture takes a plain photo Repeats times with the panel white. Photo sets the camera for both
Capture and Run. **Camera as it is** takes the camera's settings when you press the button. Run
reads them from the camera first. **These settings** sends the ISO, shutter speed and aperture
picked on the tab. The camera keeps them afterwards. Controls shows the old values until Refresh
settings. Run's impulse photos take the Impulse shutter in place of the shutter speed under
Photo. With **These settings**, the impulse photos also take the ISO and aperture picked on the
tab.

Name starts the file names. Run writes `fast_target_100ms_invert_00_coded.cr2`. LCD only flutter
shutter writes `fast_target_100ms_invert_00_switch.json`. Capture writes
`fast_target_00_photo.cr2`. Spaces and other symbols become `_`. An empty Name gives `flutter_`,
`flutter_switch_` and `flutter_photo`. A name already in the folder gets `_2`, `_3` and so on, as
in `fast_target_2_100ms_invert`. A download never replaces an earlier one.

Each coded, box, leakage, reference and dark photo comes with a trace, `<label>_<index>_<tag>.json`.
The trace holds the code, chop, lead and tail. It also holds `start_ms` and `end_ms` for every
switch, including the final black. These count from the start of the board's clock. They record
when the board sent each switch. Nothing records what the glass did. `play_s` and `fired_s` in
the trace use the laptop's clock. `fired_s` minus `play_s` is how long after the board started
its clock the laptop launched gphoto2. It leaves out gphoto2's own start-up. `shutter_s` is the
shutter speed the camera read, in seconds.

The server reads the camera's shutter speed before the first of these photos and again after each
pop-up, impulse photo or setting it sends. It stops the run in two cases. The dial may be on B,
where the 60D has no shutter speed. The shutter speed may be shorter than Lead + code.

### Target speed

The window gives the target speed in pixels per second on the sensor. Converting that to
millimetres per second needs the size of one pixel on the target. A 60D pixel is 4.3 µm.
Dividing that by the magnification gives its size on the target. With a bare 50 mm lens and the
target 1000 mm from the sensor, one pixel covers 82 µm. With the extension tube fitted and the
target 270 mm from the sensor, the magnification is about 0.33. One pixel then covers about
13 µm. The whole frame shows only about 69 by 46 mm of the scene.

That 13 µm comes from the thin lens formula and can be 8 percent out either way. Measure it.
Photograph a ruler where the target will be and count the pixels in 1 mm. The speed in mm/s is
the window's px/s divided by that count. Halving the chop doubles the speed. Doubling Blur px
doubles it too.

Speeds that differ from photo to photo are fine if each photo holds a steady speed. Measure each
photo's blur from the photo itself. A small bright dot on the target leaves a streak that shows
it.

### Light levels

The results compare the coded photo with the box and the impulse at three light levels. The
aperture sets the light, which makes the steps exact. The runs used f/5.6, f/11 and f/22 at 5 s
and ISO 100, a factor of 4 apart. The lamps, focus, zoom and track stay where they are. Each run
ticks reference, impulse, coded and box. It uses the designed code with Chop 100, Lead 1000, Tail
200, Invert and an Impulse shutter of 1/10. One leakage and one dark photo per aperture are
enough.

Drive the car left at about 100 px/s, which gives about 320 px of blur over the code. Start it
with the "95" near the right edge. The impulse, coded and box photos take about 18 s. In that time
the car travels about 1,800 px and stays in view.

## Pitfalls

- **The window** saves where you left the panes in `imgui.ini`. A file saved by an older version
  can stack the panes on top of each other. Close the window, delete `imgui.ini` and start it
  again.
- **A short Lead** cuts chops off the start of the code. A short shutter speed cuts them off the
  end.
- **The laptop** cannot open the shutter on the board's clock. Lead covers the delay before the
  shutter opens. The 60D's remote jack is the 2.5 mm E3 type. An Arduino pin could drive it
  through an optocoupler and take the guesswork out of Lead.
- **The zoom** moved from 51 mm to 55 mm during the f/22 runs. At 55 mm the car is 8 percent
  bigger. Its blur in px grows by the same amount. Tape the zoom ring.
