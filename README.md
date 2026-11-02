# MECH5720 2026: Dynamic Aperture Control with a Transmissive Liquid Crystal Display

A small liquid crystal display (LCD) sits in the light path of a Canon EOS 60D and acts as a
programmable aperture. An Arduino draws black and clear patterns on the panel. Each pattern
decides which parts of the lens pass light. The panel can also flicker in a binary code during
one exposure and become the shutter.

One Ubuntu laptop runs the panel and the camera. The group used the rig for four experiments:
depth estimation, post-capture refocus, custom bokeh and the flutter shutter. The first half of
this guide covers the whole rig. Each experiment then has a section of its own.

## Repository layout

| Folder | Contents |
| --- | --- |
| [App/Capturing/Ubuntu-System](App/Capturing/Ubuntu-System) | The capture app drives the panel and the camera from the laptop. |
| [App/Capturing/Windows-System](App/Capturing/Windows-System) and [App/Capturing/MacOs-System](App/Capturing/MacOs-System) | These folders are empty. The capture app runs on Ubuntu only. |
| [App/Processing/I-Depth_Estimation](App/Processing/I-Depth_Estimation) | The depth estimation code goes here. |
| [App/Processing/II-Post_Capture_Reconstruction](App/Processing/II-Post_Capture_Reconstruction) | The post-capture refocus code goes here. |
| [App/Processing/III-Custom_Bokeh](App/Processing/III-Custom_Bokeh) | The custom bokeh code goes here. |
| [App/Processing/IV-Flutter_Shutter](App/Processing/IV-Flutter_Shutter) | The flutter shutter scripts deblur and score the coded photos. They also redraw the key figure from the photos in `data/`. |
| [Hardware-Modifications](Hardware-Modifications) | `Method.md` describes the panel build. |

## Parts list

| Part | Use | Link |
| --- | --- | --- |
| Adafruit 1.8 inch TFT LCD, 128 x 160, ST7735R | The panel is the aperture and the shutter. Its backlight comes off. | [adafruit.com/product/358](https://www.adafruit.com/product/358) |
| Arduino Uno | The board draws each pattern on the panel. An ESP32 works too. | |
| Jumper wires | Seven wires connect the panel to the board. | |
| Canon EF and EF-S macro extension tube set, three pieces | One tube carries a slot that holds the panel between the lens and the camera. | [ebay.com.au/itm/402972099293](https://www.ebay.com.au/itm/402972099293) |
| Canon EOS 60D | The camera takes every photo over USB. | |
| Canon EF-S 18-55 mm lens | The lens forms the image. The panel sits in front of it or behind it in the tube. | |
| USB cables | One cable links the camera to the laptop. A second links the board. | |
| Laptop running Ubuntu | The laptop runs the server and the window. | |
| Desk lamp | The lamp lights the target. | |
| Toy car with "95" on its side | The car is the moving target for the flutter shutter. | |

## Build

[Hardware-Modifications/Method.md](Hardware-Modifications/Method.md) describes the panel build.
It covers stripping the backlight and mounting the panel. The panel goes in front of the lens or
in the slotted extension tube.

### Wiring

Any Arduino or ESP32 board runs the sketch. The sketch writes each run of pixels to the panel as
the bytes arrive. It needs no frame buffer and fits in an Uno's 2 KB of RAM. The panel breakout
has its own regulator and level shifter. It takes 5 V from an Uno or 3.3 V from an ESP32, on Vin
and on the logic pins.

SCK and MOSI go to the board's hardware SPI pins, which the library picks on its own. CS, D/C and
RST are defines at the top of the sketch, with one block for each board family. Any output pin
will do. The table gives the sketch's defaults, with ESP32 pins as GPIO numbers.

| Panel pin | Uno | ESP32 | ESP32-C3 | ESP32-S2 | ESP32-S3 |
| --- | --- | --- | --- | --- | --- |
| Vin | 5V | 3V3 | 3V3 | 3V3 | 3V3 |
| GND | GND | GND | GND | GND | GND |
| SCK | 13 | 18 | 4 | 36 | 12 |
| MOSI | 11 | 23 | 6 | 35 | 11 |
| TFT_CS | 10 | 5 | 7 | 34 | 10 |
| D/C | 8 | 21 | 10 | 33 | 8 |
| RST | 9 | 22 | 3 | 38 | 9 |
| LITE | not connected | not connected | not connected | not connected | not connected |

The ESP32 column covers the D1 mini ESP32 and the DevKit boards. A Mega's hardware SPI is on pins
50 to 52.

### Uploading the sketch

Install Adafruit GFX Library and the Adafruit ST7735 and ST7789 Library from the Library Manager
in the Arduino IDE before you upload
[aperture_panel.ino](App/Capturing/Ubuntu-System/arduino/aperture_panel/aperture_panel.ino). An
ESP32 needs the esp32 core from the Boards Manager first. Add
`https://espressif.github.io/arduino-esp32/package_esp32_index.json` under additional boards
manager URLs to get it. A C3, S2 or S3 mini with no USB bridge chip needs USB CDC On Boot set to
Enabled in the Tools menu. `Serial` is then the USB port.

These commands do the same from the command line:

```
cd App/Capturing/Ubuntu-System
arduino-cli lib install "Adafruit GFX Library" "Adafruit ST7735 and ST7789 Library"

# Uno on /dev/ttyACM0 (a clone with a CH340 chip shows up as /dev/ttyUSB0)
arduino-cli core install arduino:avr
arduino-cli compile --fqbn arduino:avr:uno arduino/aperture_panel
arduino-cli upload -p /dev/ttyACM0 --fqbn arduino:avr:uno arduino/aperture_panel

# ESP32
URL=https://espressif.github.io/arduino-esp32/package_esp32_index.json
arduino-cli core update-index --additional-urls $URL
arduino-cli core install esp32:esp32 --additional-urls $URL
arduino-cli compile --fqbn esp32:esp32:esp32 arduino/aperture_panel                                 # classic ESP32
arduino-cli compile --fqbn esp32:esp32:esp32c3 --board-options CDCOnBoot=cdc arduino/aperture_panel  # C3 mini
arduino-cli compile --fqbn esp32:esp32:esp32s3 --board-options CDCOnBoot=cdc arduino/aperture_panel  # S3 mini
arduino-cli upload -p /dev/ttyUSB0 --fqbn esp32:esp32:esp32 arduino/aperture_panel
```

The sketch prints `aperture 4 128 160` at 500000 baud on reset. The 4 is the protocol version.
The server refuses a board that reports any other version. Upload the sketch again after every
pull that changes it. Version 4 dropped the photodiode. A board still on version 3 will not
connect until it gets the new sketch.

The server finds the board on its own. An Uno shows up as `/dev/ttyACM0`. A clone with a CH340 chip
shows up as `/dev/ttyUSB0`. An ESP32 shows up as `/dev/ttyUSB0` or `/dev/ttyACM0`. Set
`ARDUINO_PORT` in `config.py` when the laptop has more than one serial device. `ARDUINO_BAUD` must
match `BAUD` in the sketch. A board with native USB ignores the baud.

The laptop sends each frame a few bytes at a time. One byte can be a run of 128 pixels. The panel
takes hundreds of microseconds to draw that run, while the next bytes arrive every 20 µs. A single
burst would overflow the Uno's 64 byte receive buffer. The sketch sends a `c` for every 16 bytes
it takes out of the buffer. The laptop keeps at most `ARDUINO_WINDOW`, 48 bytes, in flight.
`ARDUINO_CREDIT` must match `CREDIT_BYTES` in the sketch.

The `st7735` backend drives the panel from a Raspberry Pi over SPI instead, on the pins in
`config.py`. It needs `adafruit-circuitpython-rgb-display`.

## Laptop setup

The laptop runs Ubuntu. Run these commands once from the repository root. Log out and back in
afterwards so the `dialout` group takes effect.

```
cd App/Capturing/Ubuntu-System
./setup_laptop.sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
mkdir -p ~/.local/bin
curl -fL -o ~/.local/bin/dnglab https://github.com/dnglab/dnglab/releases/download/v0.8.0/dnglab_linux_x64
chmod +x ~/.local/bin/dnglab
```

[setup_laptop.sh](App/Capturing/Ubuntu-System/setup_laptop.sh) does the part that needs root. It
installs gphoto2 and adds you to `dialout` so the server can open the serial port. It also masks
the desktop's camera monitor and removes ModemManager and brltty, three services that fight the
rig for its devices. Known pitfalls says why.

dnglab turns each CR2 into a DNG for the Lab 3 MATLAB scripts. Adobe's DNG Converter has no Linux
build. The conversion is lossless. The raw pixels match the CR2. The BlackLevel tag that MATLAB
reads matches too, at 2048 against the 2048 to 2049 that the 60D's masked border pixels measure.
`SAVE_DNG = False` in `config.py` turns the DNGs off. Without dnglab the CR2 files still save. The
window then says why the DNGs are missing.

Until the next login after setup, the shell is not in `dialout`. Run the upload and the server
under the group in the meantime, from `App/Capturing/Ubuntu-System/`:

```
sg dialout -c ".venv/bin/python server.py --display arduino --camera gphoto"
```

## Camera setup

Put the 60D's mode dial on M and switch the lens to MF. Open the iris fully so the panel is the
stop. Set the quality to RAW+JPEG on the body. RAW+JPEG gives a CR2 for processing and a JPEG
that the window shows at once. Turn off auto power off and long exposure noise reduction in the
menu. Plug the USB cable into the laptop and check that the laptop sees the camera:

```
gphoto2 --auto-detect
gphoto2 --summary
gphoto2 --capture-image-and-download
gphoto2 --stdout --capture-movie | head -c 100000 > /dev/null    # live view stream
```

## Running the rig

The rig runs in two terminals. Start both in `App/Capturing/Ubuntu-System/` with the venv active:

```
cd App/Capturing/Ubuntu-System
source .venv/bin/activate
python server.py --display arduino --camera gphoto
```

The server prints `display=arduino camera=gphoto pupil 27.8 mm = 126.8 px` once the panel and the
camera are both up. `--display window --camera dummy` runs everything with nothing plugged in.
Check the panel from the second terminal before the first run:

```
python show.py white --backend arduino
python show.py scan0 --backend arduino
```

1. `white` should fill the panel edge to edge. A strip of noise two pixels wide along one edge
   means the panel wants `INITR_GREENTAB` in the sketch.
2. `scan0` should light one corner tile. Write down which corner of the glass lights. The refocus
   code takes each tile's position from the pattern image.
3. Look through the lens at `white` and `black`. A stripped panel may pass light where the image
   is black. Set `PANEL_INVERT = True` in `config.py` if it does. Restart the server afterwards.

Start the window in the second terminal:

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

### Running an experiment

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

### Patterns

[patterns.py](App/Capturing/Ubuntu-System/patterns.py) draws every pattern in millimetres on the
lens pupil and converts it to panel pixels at `PANEL_PITCH_MM`, 0.219 mm per pixel. A 50 mm lens
at f/1.8 has a 27.8 mm pupil. That is 127 pixels, which almost fills the 128 pixel width. Change
`FOCAL_MM` and `F_NUMBER` in `config.py` for another lens. Pupil mm overrides both for one run.

`open` is a clear disc the size of the pupil. `white` clears the whole panel and `black` shuts it.
A name from `masks/` draws that cell grid in the Lab 3 format. `zhou_a` and `zhou_b` are the
13 x 13 coded pair from figure 4 of Zhou, Lin and Nayar (ICCV 2009). `levin` and `nayar` are the
Lab 3 masks. `scan0` to `scan8` light one tile each of a 3 x 3 grid. `scan5_0` to `scan5_24` do
the same for a 5 x 5 grid. `python patterns.py` writes every named pattern to `out/patterns/`.

An image pattern is any PNG or GIF the server can read, given by its path. In an image with
transparency, the transparent pixels are open like clear glass. Every opaque pixel is shut, black
and grey alike. In an image with no transparency, white is open. The image's longest side spans
the pupil diameter times the image size. Image size is 100 percent by default. The Image size
slider in the window and `--image-scale` on the command line set it. At 71 percent a square image
fits inside the round pupil. Above 100 percent the edges are cut. Image size changes images only
and leaves the built-in patterns alone. The manifest records it as `image_scale`.

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

### Sequences

[config.py](App/Capturing/Ubuntu-System/config.py) names three sequences in `SEQUENCES`:

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
with `"code"` and `"chop_ms"` plays a flutter shutter code, as the Flutter shutter section
describes. Stop ends the job after its current step. A job that stops or fails still writes its
manifest with the photos it took.

### Command line

[capture_series.py](App/Capturing/Ubuntu-System/capture_series.py) does the same jobs from the
command line:

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

### Files and manifests

Photos land in `<outdir>/<label>_<index>_<pattern>` as `.cr2`, `.jpg` and `.dng`. A
`<label>_manifest.json` sits beside them. The manifest records when each pattern went up and when
the shutter fired. It also keeps the pupil diameter, the pixel pitch and the panel image for
every photo. The CR2 files open in rawpy the same way the Lab 3 DNGs did. The DNGs open in the Lab
3 MATLAB scripts. The server makes the DNGs after the last photo of a sequence, at about a second
each. They never delay a shutter.

An image file takes the name of its stem, `star` for `~/Pictures/star.png`. Frame 3 of
`walk.gif` is `walk_f03`. The manifest keeps the full path in `pattern`, `walk.gif#3` for a GIF
frame. It keeps the file name part in `tag`.

### Panel timing

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

## Depth estimation

The Depth tab captures the depth photos. Use a point source at each distance for PSF set. Use a
textured target at each distance for Pair, Singles and Card pair.

- **PSF set** takes open, pattern A, pattern B, Levin and black.
- **Pair** takes open, A, B and open.
- **Singles** takes each coded pattern twice. One pattern then gets the exposure of the pair.
- **Card pair** takes the same four photos through hand-fitted cards with the panel white. It
  pauses before each card. The cards give the baseline for what the panel costs.

Patterns A and B start as `zhou_a` and `zhou_b`. Type another mask name from `masks/` or pick a
PNG or GIF with Browse A... and Browse B.... Image size in Controls sizes an image. The file
names read `depth1000mm_pair`, which keeps the distance with the photos. A pair other than the
Zhou pair adds its names, as in `depth1000mm_pair_star_heart`. It never overwrites the Zhou files.

The depth estimation code goes in
[App/Processing/I-Depth_Estimation](App/Processing/I-Depth_Estimation).

## Post-capture refocus

The Refocus tab captures the refocus photos with the target at each distance.

- **Scan 3x3** and **Scan 5x5** take open, every tile, black and open. The 5 x 5 scan takes 28
  photos.
- **f/5.6 frame** takes one open disc 8.9 mm wide. That matches the depth of field the 3 x 3
  refocus reaches. It is the one-photo baseline.
- **Lens focus** pauses for you to focus the lens on the target by hand. It then takes the
  in-focus reference for SSIM.

The refocus code goes in
[App/Processing/II-Post_Capture_Reconstruction](App/Processing/II-Post_Capture_Reconstruction).

## Custom bokeh

The capture app here has no bokeh tab. Image patterns in Controls and
`capture_series.py --patterns` still put any shape on the panel. The custom bokeh code goes in
[App/Processing/III-Custom_Bokeh](App/Processing/III-Custom_Bokeh).

## Flutter shutter

The flutter shutter of Raskar, Agrawal and Tumblin opens and closes the shutter in a binary code
during one exposure. The blur of a moving target then stays invertible. On this rig the panel is
the shutter. The camera takes one photo on M at its own shutter speed. The panel is black when the
shutter opens. The board then plays the code on the panel from its own clock. The panel stays
black until the shutter closes. The curtains move in the dark, which means every row of the
sensor sees the same code. The 60D's 1/250 s curtain travel does not matter.

![The flutter shutter rig on a table: the laptop, the 60D with the LCD taped to the front of the
lens, the Arduino, a desk lamp and the toy car](App/Processing/IV-Flutter_Shutter/images/flutter_shutter_setup.jpeg)

*The photo shows the flutter shutter setup with the LCD on the front of the lens.*

![Diagram of the setup: the code on the LCD in front of the lens or inside the extension tube,
the 60D, the lens, the moving toy car and the desk lamp](App/Processing/IV-Flutter_Shutter/images/flutter_setup.png)

*The LCD plays a 32-chop code of 100 ms chops during one 5 s exposure. It sits either in front
of the lens or inside the extension tube.*

### Switching the panel

The board switches the panel in one of two ways. Invert sends the controller's one-byte invert
command. That flips every pixel in the time the liquid crystal takes, 15 to 35 ms by the
datasheet. Frame write rewrites every pixel, which takes 41 ms at the Uno's 8 MHz SPI clock.
Chops under about 130 ms slip with Frame write. Invert is the better method. Frame write is the
fallback for a panel that Invert does not take fully clear. The sketch holds the whole run to a
16 bit millisecond clock. Lead, code and tail together must fit `FLUTTER_MAX_S`, 60 s.

[flutter.py](App/Capturing/Ubuntu-System/flutter.py) designs the code. It searches random 32-chop
codes with 16 chops open, first and last open. It keeps the code with the highest minimum in the
padded spectrum. The search is seeded. Every machine designs the same code,
`10001101101001011000001111010101`. The manifest records the code by its text. A box exposure of
the same length scores 0. The designed code scores 0.075. The Custom field takes any code of up
to 64 chops.

### Capture procedure

1. Light the scene with lamps on a direct current supply. Mains lighting flickers at 100 Hz.
2. Leave the designed code on the Flutter tab. Set Chop ms to 100, pick Invert and press LCD only
   flutter shutter. The panel flutters on its own with no camera.
3. Watch the panel. It should go fully clear and fully dark in the code's pattern. Switch to
   Frame write if it never goes fully clear.
4. Set Blur px to 100. The line under it gives the target speed in px/s for the chop. Target
   speed below turns that into mm/s or rpm.
5. Set the shutter speed on M to at least Lead + code. That is 5 s for the defaults. The tab
   turns the warning red when the shutter speed is too short.
6. Tick all six captures. The light-level runs of step 10 tick reference, impulse, coded and box
   only. Set Repeats to 1 or 2 and press Run. Press Run again for more.
7. Follow the pop-ups. The first asks for the target standing still for the reference. The next
   asks for it moving for the impulse, coded, box and leakage photos. The third asks for the lens
   cap for the darks. The last asks you to take the cap off again. The dial stays on M throughout.
8. Repeat steps 4 to 7 with Frame write at 100 ms and at 200 ms.
9. Repeat steps 4 to 7 with Invert at 25, 50 and 200 ms. Reset the target speed each time.
10. Repeat steps 4 to 7 at 100 ms at the other light levels. Light levels below gives the
    settings.

The same works from the command line, one coded photo at a time at the shutter speed set on M:

```
python capture_series.py --code designed --chop 100 --no-capture --label switch --outdir captures/flutter
python capture_series.py --code designed --chop 100 --label coded --outdir captures/flutter
python capture_series.py --go        # from another terminal when a job is waiting
```

### The Flutter tab

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

The window gives the target speed in pixels per second on the sensor. A motor wants millimetres
per second or rpm. Converting needs the size of one pixel on the target.

A 60D pixel is 4.3 µm. Dividing that by the magnification gives its size on the target. With
a bare 50 mm lens and the target 1000 mm from the sensor, one pixel covers 82 µm. With the
extension tube fitted and the target 270 mm from the sensor, the magnification is about 0.33.
One pixel then covers about 13 µm. The whole frame shows only about 69 by 46 mm of the scene.

That 13 µm comes from the thin lens formula and can be 8 percent out either way. Measure it.
Photograph a ruler where the target will be and count the pixels in 1 mm. The speed in mm/s is
the window's px/s divided by that count.

The table gives the speeds for a 100 px blur over the designed 32-chop code, with the target at
270 mm.

| Chop | Code lasts | Speed | rpm, 5 mm shaft | rpm, 10 mm spool | rpm, 20 mm wheel |
| --- | --- | --- | --- | --- | --- |
| 25 ms | 0.8 s | 1.65 mm/s | 6.3 | 3.2 | 1.6 |
| 50 ms | 1.6 s | 0.83 mm/s | 3.2 | 1.6 | 0.8 |
| 100 ms | 3.2 s | 0.41 mm/s | 1.6 | 0.8 | 0.4 |
| 200 ms | 6.4 s | 0.21 mm/s | 0.8 | 0.4 | 0.2 |

For any other diameter, rpm = mm/s × 60 ÷ (π × diameter in mm). Measure a spool with the string
wound on, because the string adds to the diameter. Halving the chop doubles the speed. Doubling
Blur px doubles it too.

These speeds are far too slow for a toy car under its own power. A stepper motor such as the
28BYJ-48 can wind string onto a spool at these speeds. It holds the same speed every run. Give it
its own Arduino, because the panel's board is busy for the whole code.

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

### Processing the photos

The flutter scripts live in
[App/Processing/IV-Flutter_Shutter](App/Processing/IV-Flutter_Shutter). Where their usage lines
say the code folder, they mean that folder. Set up their own venv once:

```
cd App/Processing/IV-Flutter_Shutter
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

| Script | What it does |
| --- | --- |
| [flutter_deblur.py](App/Processing/IV-Flutter_Shutter/flutter_deblur.py) | It deblurs one coded photo with the code from its trace and scores the result against the reference. |
| [flutter_score.py](App/Processing/IV-Flutter_Shutter/flutter_score.py) | It checks a whole run and scores its coded, box and impulse photos against the reference. It also draws the close-ups of the "95". |
| [flutter_figure.py](App/Processing/IV-Flutter_Shutter/flutter_figure.py) | It redraws the key figure from the photos in `data/`. |
| [rawframe.py](App/Processing/IV-Flutter_Shutter/rawframe.py) | It loads a CR2 or DNG as a green channel image with its ISO and exposure time. |

`flutter_95_template.npy` holds the "95" cut from a reference photo. `flutter_score.py` finds it
in each reference to centre the close-ups.

The window downloads the photos of a Run to `App/Capturing/Ubuntu-System/captures/flutter/`.
Each photo arrives as a `.cr2`, a `.jpg` and a `.dng`. The run's
`<Name>_<chop>ms_<method>_manifest.json` sits beside them. Git ignores these folders, because the
raw photos of one run come to hundreds of megabytes.

[flutter_deblur.py](App/Processing/IV-Flutter_Shutter/flutter_deblur.py) stretches the code from
the trace over a blur length along the rows. It removes that blur row by row with a Wiener
filter. It then aligns the result to the averaged reference photos. It scores the result by MSE,
PSNR and NCC. `--sweep` tries a range of blur lengths in both directions and keeps the lowest MSE.
Give it the run's prefix:

```
.venv/bin/python flutter_deblur.py ../../Capturing/Ubuntu-System/captures/flutter/Run1actual_100ms_invert --blur 100
.venv/bin/python flutter_deblur.py ../../Capturing/Ubuntu-System/captures/flutter/Run1actual_100ms_invert --sweep 100:5200:100
```

The results land in `out/flutter/<run>/`. `compare.png` holds the coded, deblurred and reference
photos one above the other. `scores.csv` holds every blur length tried. The alignment searches up
to half the frame width. Check the shift column. A deblurred photo that lands hundreds of pixels
from the coded photo has matched the wrong part of the scene. Its MSE does not count.

[flutter_score.py](App/Processing/IV-Flutter_Shutter/flutter_score.py) scores a run by its Name.
It adds `_100ms_invert` to the Name, which means it takes only runs at Chop 100 with Invert.
`--dir` names the folder that holds the photos. The script resolves that folder from its own
location, whatever folder you run it from.

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

### Regenerating the key figure

[flutter_figure.py](App/Processing/IV-Flutter_Shutter/flutter_figure.py) redraws the report's
flutter figure from the photos in [data/](App/Processing/IV-Flutter_Shutter/data). It takes about
40 s:

```
cd App/Processing/IV-Flutter_Shutter
.venv/bin/python flutter_figure.py
```

![The "95" on the toy car, coded, deblurred and reference, at f/5.6, f/11 and f/22 with the LCD
in front of the lens](App/Processing/IV-Flutter_Shutter/images/flutter_front_95.png)

*The figure shows the coded, deblurred and reference images with the LCD in front of the lens.*

Each column is one run with the LCD in front of the lens. `data/` holds each run's still reference
and its coded photo as CR2 files, 114 MB in all. The coded photo's trace sits beside them.

| Column | Run | Coded photo | Blur |
| --- | --- | --- | --- |
| f/5.6 | Run2_f5_6 | `Run2_f5_6_100ms_invert_02_coded.cr2` | 375 px |
| f/11 | Run19 | `Run19_100ms_invert_01_coded.cr2` | 475 px |
| f/22 | Run2_f22 | `Run2_f22_100ms_invert_02_coded.cr2` | 325 px |

The script deblurs each coded photo with 40 Richardson-Lucy iterations at the blur length that
`flutter_score.py` found. It fits each panel to its reference by a gain and an offset. It cuts
every panel around the "95" the way `flutter_score.py` does. It writes
`images/flutter_front_95.png` and prints the MSE of each deblur against its reference. The run
gives MSE 0.00285 at f/5.6, 0.00122 at f/11 and 0.00470 at f/22. Those match the scores that
`flutter_score.py` saved. The report quotes the f/11 one.

### Flutter pitfalls

- **Mains lighting** flickers at 100 Hz and adds its own code to every photo. Use
  lamps on a direct current supply.
- **Invert** may not take every panel fully clear. Watch LCD only flutter
  shutter before the first run.
- **A short Lead** cuts chops off the start of the code. A short shutter speed cuts them off the
  end.
- **The panel** takes 15 to 35 ms to switch. The runs needed 100 ms chops and a
  5 s exposure as a result.
- **Nobody could hold the car** at 80 to 160 px/s for the whole 3.2 s code. Its speed wandered
  by 20 to 35 percent over the 8 s of moving photos.
- **The coded and box photos** of one run seldom got the same blur. A box photo
  with less blur has the easier job. Only the f/22 coded and box photos in front of the lens
  came within 8 percent of each other.
- **The car's reflections** and the lamp light on it change along the track.
  The score fits one brightness and contrast to the whole picture. A photo taken 1,000 px from the
  reference spot scores several times worse however sharp it is. Stand the car for the reference
  where it will be during the coded photo.
- **The zoom** moved from 51 mm to 55 mm during the f/22 runs. At 55 mm the car is 8 percent
  bigger. Its blur in px grows by the same amount.
- **The laptop** cannot open the shutter on the board's clock. Lead covers the
  delay before the shutter opens. The 60D's remote jack is the 2.5 mm E3 type. An Arduino pin
  could drive it through an optocoupler and take the guesswork out of Lead.

## Known pitfalls

- **gphoto2 cannot claim the camera** when the desktop has mounted it as a drive.
  `setup_laptop.sh` masks the gvfs camera monitor to stop that. `server.py` also kills the
  monitor at start. Run the two commands below by hand if it happens anyway. The mount,
  `gvfsd-gphoto2`, is the process that holds the camera.

  ```
  pkill -f gvfs-gphoto2-volume-monitor
  pkill -f gvfsd-gphoto2
  ```

- **ModemManager** probes a new serial device for a few seconds after it
  appears. The first connection after plugging in the board can fail. `setup_laptop.sh` removes
  ModemManager.
- **The brltty screen reader** claims CH340 bridges, the chip on most ESP32 minis.
  The port disappears a moment after it appears. `setup_laptop.sh` removes brltty.
- **The shell joins `dialout`** only at the next login after setup. Use `sg dialout` until then.
- **LibRaw 0.22** reads these DNGs with a black level of 2088 to 2151. That darkens a
  photo by about 5 percent and clips the faint edge of a point spread function. The flutter
  scripts read the CR2 through rawpy for that reason. They pick it over a DNG of the same photo.
- **The window** saves where you left the panes in `imgui.ini`. A file saved by an older version
  can stack the panes on top of each other. Close the window, delete `imgui.ini` and start it
  again.
- **Live view** drains the camera battery faster than anything else. Untick it
  before a run.
- **A stripped panel** may pass light where the image is black.
  Set `PANEL_INVERT` in `config.py` to match what the lens shows.
- **The server** refuses a board on another protocol version. Upload the sketch again
  after every pull that changes it.
