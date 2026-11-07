<div align="center">

# Dynamic Aperture Control with a Transmissive Liquid Crystal Display

**A 1.8 inch LCD panel and an Arduino Uno give a Canon EOS 60D a programmable aperture and a
coded shutter.**

MECH5720 Computational Imaging · The University of Sydney · 2026

[![Python 3](https://img.shields.io/badge/Python-3-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Arduino Uno R3](https://img.shields.io/badge/Arduino-Uno%20R3-00878F?style=for-the-badge)](App/Capturing/Ubuntu-System/arduino/aperture_panel)
[![Ubuntu](https://img.shields.io/badge/Ubuntu-E95420?style=for-the-badge&logo=ubuntu&logoColor=white)](#laptop-setup)
[![Canon EOS 60D](https://img.shields.io/badge/Canon-EOS%2060D-CC0000?style=for-the-badge)](#camera-setup)
[![gphoto2](https://img.shields.io/badge/gphoto2-tethered-4B8BBE?style=for-the-badge)](http://www.gphoto.org/)
[![Licence: MIT](https://img.shields.io/badge/Licence-MIT-F7DF1E?style=for-the-badge)](LICENSE)

[![NumPy](https://img.shields.io/badge/NumPy-013243?style=flat-square&logo=numpy&logoColor=white)](https://numpy.org/)
[![SciPy](https://img.shields.io/badge/SciPy-8CAAE6?style=flat-square&logo=scipy&logoColor=white)](https://scipy.org/)
[![OpenCV](https://img.shields.io/badge/OpenCV-5C3EE8?style=flat-square&logo=opencv&logoColor=white)](https://opencv.org/)
[![Matplotlib](https://img.shields.io/badge/Matplotlib-11557C?style=flat-square)](https://matplotlib.org/)
[![Flask](https://img.shields.io/badge/Flask-000000?style=flat-square&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![Last commit](https://img.shields.io/github/last-commit/j-passmore/mech5720-2026-Dynamic-Aperture-Using-LCD?style=flat-square)](https://github.com/j-passmore/mech5720-2026-Dynamic-Aperture-Using-LCD/commits/main)

[Layout](#repository-layout) · [Parts](#parts-list) · [Build](#build) · [Setup](#laptop-setup) ·
[Capture](#capture-procedure) · [Figures](#regenerating-the-figures) · [Pitfalls](#known-pitfalls)

<table>
  <tr>
    <td align="center" width="50%">
      <b><a href="#depth-estimation">Depth estimation</a></b><br><br>
      <img src="Out/Depth_Estimation/mask1.jpg" height="240" alt="A defocused desk scene photographed through coded mask 1"><br>
      <sub>The camera takes one photo through each coded mask. It took this one through mask 1.</sub>
    </td>
    <td align="center" width="50%">
      <b><a href="#post-capture-refocus">Post-capture refocus</a></b><br><br>
      <img src="Out/Post_Capture_Reconstruction/all_in_focus.png" height="240" alt="The desk scene rebuilt sharp from the two coded photos"><br>
      <sub><code>reconstruct.py</code> rebuilds a sharp image from the two coded photos and the depth map.</sub>
    </td>
  </tr>
  <tr>
    <td align="center" width="50%">
      <b><a href="#custom-bokeh">Custom bokeh</a></b><br><br>
      <img src="Out/Custom_Bokeh/mario_outside_lens.gif" height="240" alt="Out-of-focus lights shaped like a walking sprite"><br>
      <sub>Every out-of-focus light takes the shape of the frame on the panel.</sub>
    </td>
    <td align="center" width="50%">
      <b><a href="#flutter-shutter">Flutter shutter</a></b><br><br>
      <img src="Out/Flutter_Shutter/flutter_front_95_f11.png" height="240" alt="The coded, deblurred and reference photos of the toy car at f/11"><br>
      <sub>The panel chops one 5 s exposure in a binary code. The script deblurs the car with 40 Richardson-Lucy iterations.</sub>
    </td>
  </tr>
</table>

</div>

## Overview

A small liquid crystal display (LCD) sits in the light path of a Canon EOS 60D and acts as a
programmable aperture. An Arduino draws black and clear patterns on the panel. Each pattern
sets which parts of the lens pass light. The panel can also flicker in a binary code during
one exposure and become the shutter.

One Ubuntu laptop runs the panel and the camera. The group used the rig for four experiments:
depth estimation, post-capture refocus, custom bokeh and the flutter shutter. This page is the
build guide. The folder READMEs hold the detail: the capture app's manual and each experiment's
processing.

| Experiment | Panel role | Status |
| --- | --- | --- |
| [Depth estimation](#depth-estimation) | The panel shows the coded aperture pair of Zhou, Lin and Nayar. | ![Complete](https://img.shields.io/badge/complete-2EA44F?style=flat-square) |
| [Post-capture refocus](#post-capture-refocus) | The panel opens one tile of the aperture per photo in a 3x3 or 5x5 scan. | ![Complete](https://img.shields.io/badge/complete-2EA44F?style=flat-square) |
| [Custom bokeh](#custom-bokeh) | The panel draws the shape every out-of-focus light takes. | ![Complete](https://img.shields.io/badge/complete-2EA44F?style=flat-square) |
| [Flutter shutter](#flutter-shutter) | The panel plays a 32-chop binary code inside one exposure. | ![Complete](https://img.shields.io/badge/complete-2EA44F?style=flat-square) |

## Repository layout

| Folder | Contents |
| --- | --- |
| [App/Capturing/Ubuntu-System](App/Capturing/Ubuntu-System) | The folder holds the capture app: the server, the window, the command line client, the Arduino sketch, the masks and the sprites. [Its README](App/Capturing/Ubuntu-System/README.md) is the app manual. |
| [App/Capturing/Windows-System](App/Capturing/Windows-System) | The folder holds the Windows tools that took the depth photos: the camera trigger, the mask sender and its Arduino sketch. [Its README](App/Capturing/Windows-System/README.md) lists them. |
| [App/Processing/I-Depth_Estimation](App/Processing/I-Depth_Estimation) | The folder holds the calibration and the two depth methods, pixel by pixel and vertical strip, with [their README](App/Processing/I-Depth_Estimation/README.md). |
| [App/Processing/II-Post_Capture_Reconstruction](App/Processing/II-Post_Capture_Reconstruction) | The folder holds the scripts that recover an all-in-focus image with each depth method, with [their README](App/Processing/II-Post_Capture_Reconstruction/README.md). |
| [App/Processing/III-Custom_Bokeh](App/Processing/III-Custom_Bokeh) | The folder holds the script that draws the bokeh figures and GIFs, with [its README](App/Processing/III-Custom_Bokeh/README.md). |
| [App/Processing/IV-Flutter_Shutter](App/Processing/IV-Flutter_Shutter) | The folder holds the scripts that deblur and score the flutter photos and draw the key figures, with [their README](App/Processing/IV-Flutter_Shutter/README.md). |
| [Captures](Captures) | The folder holds the raw photos in one subfolder per experiment. The bokeh and flutter subfolders hold photos. The depth and reconstruction scripts share `Captures/Depth_Estimation_and_Reconstruction/`. It holds the scene pair so far. The group has yet to add the dark frames and PSF photos. |
| [Out](Out) | The folder holds what the scripts write in one subfolder per experiment. |
| [Hardware-Modifications](Hardware-Modifications) | The folder holds photos of the parts. |

## Parts list

| Part | Use | Link |
| --- | --- | --- |
| Adafruit 1.8 inch TFT LCD, 128 x 160, ST7735R, product 358 | The panel is the aperture and the shutter. Its backlight comes off. | [adafruit.com/product/358](https://www.adafruit.com/product/358) |
| Arduino Uno Rev3 | The board draws each pattern on the panel. | [store.arduino.cc](https://store.arduino.cc/products/arduino-uno-rev3) |
| JJC AET-C25 automatic extension tube, 25 mm, Canon EF and EF-S | The tube holds the panel between the lens and the body through a slot cut in its side. | [jjc.cc](https://jjc.cc/index/goods/detail.html?id=631) (bought on [eBay](https://www.ebay.com.au/itm/402972099293)) |
| Canon EOS 60D | The camera takes every photo over USB. | |
| Canon EF-S 18-55 mm lens | The lens forms the image. The panel sits in front of it or behind it in the tube. | |
| Seven jumper wires and two USB cables | The wires link the panel to the board. One cable links the camera to the laptop. The other links the board to the laptop. | |
| Laptop running Ubuntu | The laptop runs the server and the window. | |
| Desk lamp on a direct current supply | The lamp lights the target. Mains lamps flicker at 100 Hz. | |
| Toy car with "95" on its side | The car is the moving target for the flutter shutter. | |
| String of small lights | The lights are the out-of-focus highlights for the custom bokeh. | |

<table>
  <tr>
    <td align="center" width="50%"><img src="Hardware-Modifications/images/extension_tube_jjc_aet_c25.jpg" alt="The JJC AET-C25 extension tube in its box"></td>
    <td align="center" width="50%"><img src="Hardware-Modifications/images/panel_adafruit_358.jpg" alt="The Adafruit 358 panel beside its bag"></td>
  </tr>
  <tr>
    <td align="center"><sub>The JJC AET-C25 tube is 25 mm long and fits Canon EF and EF-S lenses.</sub></td>
    <td align="center"><sub>The Adafruit 358 panel measures 1.8 inch and has 128 x 160 pixels.</sub></td>
  </tr>
</table>

## Build

1. Take the backlight off the panel. Light then passes through the glass. The LITE pin stays
   unconnected.
2. Wire the panel to the Uno with seven jumper wires. The breakout has its own regulator and
   level shifter. It takes 5 V on Vin and on the logic pins. SCK and MOSI are the Uno's
   hardware SPI pins. CS, D/C and RST are defines at the top of the sketch. Any output pin will
   do for those three.

   | Panel pin | Uno pin |
   | --- | --- |
   | Vin | 5V |
   | GND | GND |
   | SCK | 13 |
   | MOSI | 11 |
   | TFT_CS | 10 |
   | D/C | 8 |
   | RST | 9 |
   | LITE | not connected |

3. Install Adafruit GFX Library and Adafruit ST7735 and ST7789 Library from the Library Manager
   in the Arduino IDE. Upload
   [aperture_panel.ino](App/Capturing/Ubuntu-System/arduino/aperture_panel/aperture_panel.ino)
   from the IDE. You can do the same with `arduino-cli` from a terminal:

   ```bash
   cd App/Capturing/Ubuntu-System
   arduino-cli lib install "Adafruit GFX Library" "Adafruit ST7735 and ST7789 Library"
   arduino-cli core install arduino:avr
   arduino-cli compile --fqbn arduino:avr:uno arduino/aperture_panel
   arduino-cli upload -p /dev/ttyACM0 --fqbn arduino:avr:uno arduino/aperture_panel
   ```

   The sketch prints `aperture 4 128 160` at 500000 baud on reset. The 4 is the protocol
   version. The server rejects any other. Upload the sketch again after every pull that changes
   it.
4. Mount the panel in one of two places. In front of the lens, tape the panel flat against the
   front of the lens with the glass across the beam. Inside the tube, cut a slot through the side
   of the extension tube, fit the tube between the lens and the body and slide the panel in
   through the slot.
5. Check the panel through the lens once the laptop is set up.
   [Running the rig](#running-the-rig) lists the three checks.

## Laptop setup

Run these commands once.

```bash
cd App/Capturing/Ubuntu-System
./setup_laptop.sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
mkdir -p ~/.local/bin
curl -fL -o ~/.local/bin/dnglab https://github.com/dnglab/dnglab/releases/download/v0.8.0/dnglab_linux_x64
chmod +x ~/.local/bin/dnglab
```

[setup_laptop.sh](App/Capturing/Ubuntu-System/setup_laptop.sh) installs gphoto2, adds you to
`dialout` and removes three services that lock the rig's devices.
[Known pitfalls](#known-pitfalls) lists them. `dnglab` converts each CR2 to a lossless DNG for
the Lab 3 MATLAB scripts. `SAVE_DNG = False` in `config.py` turns the DNGs off.

> [!NOTE]
> Log out and back in after setup so the shell joins the `dialout` group. Run the server under
> the group until you log in again:
>
> ```bash
> sg dialout -c ".venv/bin/python server.py --display arduino --camera gphoto"
> ```

## Camera setup

Put the 60D's mode dial on M and switch the lens to MF. Open the iris all the way so the panel is
the stop. Set the quality to RAW+JPEG on the body. Turn off auto power off and long exposure noise
reduction in the menu. Plug the USB cable into the laptop and check that the laptop detects the
camera:

```bash
gphoto2 --auto-detect
gphoto2 --capture-image-and-download
```

## Running the rig

The rig runs in two terminals, both in `App/Capturing/Ubuntu-System/` with the venv active.
Start the server first:

```bash
cd App/Capturing/Ubuntu-System
source .venv/bin/activate
python server.py --display arduino --camera gphoto
```

The server prints `display=arduino camera=gphoto pupil 27.8 mm = 126.8 px` once the panel and
the camera are both up. Check the panel from the second terminal before the first run:

```bash
python show.py white --backend arduino
python show.py scan0 --backend arduino
```

1. `white` should fill the panel edge to edge. A strip of noise two pixels wide along one edge
   means the panel needs `INITR_GREENTAB` in the sketch.
2. `scan0` should light one corner tile. Write down which corner of the glass lights.
3. Look through the lens at `white` and `black`. A stripped panel may pass light where the image
   is black. Set `PANEL_INVERT = True` in `config.py` if it does and restart the server.

Start the window in the second terminal:

```bash
python camview_capture.py --outdir captures
```

The window shows the camera's live view, the image on the panel, the controls and one tab per
experiment. [The app manual](App/Capturing/Ubuntu-System/README.md) describes every control,
pattern and file.

> [!TIP]
> Tick Live view to frame the scene and untick it before a run, because it drains the camera
> battery.

## Capture procedure

Place the target and type its distance into Target distance mm in the Experiments window. Set
Repeats to 5 for the error bars. Press the button for the capture and follow the prompts. The
photos land in `captures/<experiment>/` with a manifest beside them.

### Depth estimation

Use a point source at each distance for PSF set. Use a textured target at each distance for
the rest.

- **PSF set** takes open, pattern A, pattern B, Levin and black.
- **Pair** takes open, A, B and open.
- **Singles** takes each coded pattern twice. One pattern then gets the exposure of the pair.
- **Card pair** takes the same four photos through hand-fitted cards with the panel white. The
  cards give the baseline for what the panel costs.

Patterns A and B start as `zhou_a` and `zhou_b`, the coded pair of Zhou, Lin and Nayar.

### Post-capture refocus

- **Scan 3x3** and **Scan 5x5** take open, every tile, black and open.
- **f/5.6 frame** takes one photo through an open disc 8.9 mm wide as the one-photo baseline.
- **Lens focus** pauses for you to focus the lens on the target by hand. It then takes the
  in-focus reference.

### Custom bokeh

An out-of-focus point of light takes the shape of the aperture. Every light behind the subject
becomes the shape the panel draws. A walk cycle on the panel gives one photo per frame. You load
each shape as an image pattern since the app has no bokeh tab.
[sprites/](App/Capturing/Ubuntu-System/sprites) holds the Link, Mario and Knight frames the
group used. Each frame is a transparent character on black.

1. Stand a string of small lights behind the subject and focus the lens on the subject.
   The lights must blur.
2. Open the iris. Set ISO 100 and 5 s on M.
3. Set Pupil mm to the stop the panel makes: 9.5 mm in front of the lens or 5.5 mm inside the
   tube.
4. Pick a sprite frame or GIF with Browse... or type a mask name. Press Capture and save.
   `capture_series.py` takes a list of patterns from a terminal:

   ```bash
   python capture_series.py --patterns open sprites/binary/mario/mario_binary_walk.gif open --label mario --outdir captures/bokeh --diameter 9.5
   python capture_series.py --patterns open levin nayar zhou_a zhou_b open --label masks --outdir captures/bokeh --diameter 9.5
   ```

5. Move the panel into the tube and repeat with `--diameter 5.5`.

### Flutter shutter

The flutter shutter of Raskar, Agrawal and Tumblin opens and closes the shutter in a binary code
during one exposure. The blur of a moving target then stays invertible. On this rig the panel is
the shutter inside one 5 s photo on M. The panel is black when the camera's shutter opens. The
board then plays a 32-chop code of 100 ms chops from its own clock and holds the panel black
until the shutter closes.

1. Light the scene with lamps on a direct current supply.
2. On the Flutter tab leave the designed code. Set Chop ms to 100, pick Invert and press LCD
   only flutter shutter. Check that the panel reaches full clear and full dark in the code's
   pattern. Switch to Frame write if it never reaches full clear.
3. Set 5 s and ISO 100 on M. Set the aperture for the light level: f/5.6, f/11 or f/22.
4. Tick reference, impulse, coded and box. Set Repeats to 1 and press Run.
5. Follow the pop-ups. Stand the car still for the reference. Drive it left at about 100 px/s
   for the other photos and start each run with the "95" near the right edge.
6. Repeat at the other two apertures with the lamps, focus, zoom and track unchanged. Move the
   panel into the tube and repeat all three.

`capture_series.py` takes one coded photo at a time at the shutter speed set on M:

```bash
python capture_series.py --code designed --chop 100 --no-capture --label switch --outdir captures/flutter
python capture_series.py --code designed --chop 100 --label coded --outdir captures/flutter
```

## Regenerating the figures

Each experiment has a processing folder that turns its raw photos in `Captures/` into its main
results in `Out/`. Set up the venv of each folder once:

```bash
cd App/Processing/<folder>
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Each block below starts from the repository root. Every script finds `Captures/` and `Out/` from
its own location. The folder READMEs hold the detail of each method.

### I. Depth estimation

The scripts read the dark frames, the PSFs and the scene pairs in
[Captures/Depth_Estimation_and_Reconstruction](Captures/Depth_Estimation_and_Reconstruction).
`calibrate.py` runs first since both methods use its PSF pairs.

```bash
cd App/Processing/I-Depth_Estimation
.venv/bin/python calibrate.py
.venv/bin/python psf_fourier.py
.venv/bin/python pixel_by_pixel_method/estimate_depth.py
.venv/bin/python vertical_strip_method/estimate_depth.py
```

| Result | File in `Out/Depth_Estimation/` |
| --- | --- |
| The PSF pair at each distance | `calibration/psf_pairs.png` |
| The spectra of each PSF pair | `calibration/psf_fourier.png` |
| The pixel by pixel key figure: the photo, the depth map, the confident pixels and the all-in-focus image | `pixel_by_pixel_method/depth_heatmap.png` |
| The pixel by pixel depth map on its own | `pixel_by_pixel_method/depth_map.png` |
| The confident pixels on their own | `pixel_by_pixel_method/depth_map_confident.png` |
| The mask 1 photo on its own | `pixel_by_pixel_method/captured_mask1.png` |
| The vertical strip depth map | `vertical_strip_method/depth_steps.png` |

![The photo through mask 1, the distance the pixel by pixel method picked for each pixel, the
pixels it trusts and the all-in-focus image](Out/Depth_Estimation/pixel_by_pixel_method/depth_heatmap.png)

*The pixel by pixel method on the scene pair with the LCD in front of the lens. The top row shows
the photo through mask 1 and the distance the method picked for each pixel, from 350 to 903 mm.
The bottom row keeps only the pixels the method trusts and shows the all-in-focus image from the
same deblur.*

### II. Post-capture reconstruction

The scripts read the same photos as depth estimation. They also read the depth map of each method.
Run the depth estimation block first.

```bash
cd App/Processing/II-Post_Capture_Reconstruction
.venv/bin/python pixel_by_pixel_method/reconstruct.py
.venv/bin/python vertical_strip_method/reconstruct.py
```

| Result | File in `Out/Post_Capture_Reconstruction/` |
| --- | --- |
| The key figure: the vertical strip photo before and after reconstruction | `vertical_strip_method/reconstruction_comparison.png` |
| The all-in-focus image from the vertical strip depth map | `vertical_strip_method/all_in_focus.png` |
| The pixel by pixel photo before and after reconstruction | `pixel_by_pixel_method/reconstruction_comparison.png` |
| The all-in-focus image from the pixel by pixel depth map | `pixel_by_pixel_method/all_in_focus.png` |

![A barcode scene through mask 1 before reconstruction and after the vertical strip
reconstruction](Out/Post_Capture_Reconstruction/vertical_strip_method/reconstruction_comparison.png)

*The vertical strip method on a barcode scene. The left half shows the photo through mask 1. The
right half shows the same photo after the script deblurs each strip at the distance it picked for
that strip. The bars and digits of the barcode come out sharp. Ringing lines run down the bright
object on the right.*

The folder holds the scene pair so far. The group has yet to add the dark frames and PSF photos
that `calibrate.py` needs. The depth and reconstruction blocks fail until they arrive.

### III. Custom bokeh

The script reads the raw photos in [Captures/Custom_Bokeh](Captures/Custom_Bokeh). It takes about
half a minute.

```bash
cd App/Processing/III-Custom_Bokeh
.venv/bin/python bokeh_figure.py
```

| Result | File in `Out/Custom_Bokeh/` |
| --- | --- |
| The sprite frames and the lights they shaped | `bokeh_sprites.png` |
| The masks and the lights they shaped | `bokeh_masks.png` |
| The walk cycle as the lights show it | `<character>_outside_lens.gif` and `<character>_inside_lens.gif` |
| The mesh pitch in each photo | `highlights.csv` |

![Seven sprite frames on the panel and the lights they shaped, with the panel in front of the
lens and behind the lens](Out/Custom_Bokeh/bokeh_sprites.png)

*Each column holds one sprite frame. The top two rows show the pattern at a 9.5 mm pupil and
the lights it shaped with the panel in front of the lens. The bottom two rows show the same at
5.5 mm with the panel behind the lens. The mesh in every light is the panel's pixel grid.*

![The Levin, Nayar and Zhou masks on the panel and the lights they
shaped](Out/Custom_Bokeh/bokeh_masks.png)

*The four masks follow the same layout.*

### IV. Flutter shutter

The script reads the reference and coded photos of six runs in
[Captures/Flutter_Shutter](Captures/Flutter_Shutter). It takes about two minutes. It prints the MSE
of each deblur. All six match the scores the group saved.

```bash
cd App/Processing/IV-Flutter_Shutter
.venv/bin/python flutter_figure.py
```

| Result | File in `Out/Flutter_Shutter/` |
| --- | --- |
| The key figure with the LCD in front of the lens | `flutter_front_95.png` |
| The same with the LCD inside the extension tube | `flutter_inside_95.png` |

![The "95" on the toy car, coded, deblurred and reference, at f/5.6, f/11 and f/22 with the LCD
in front of the lens](Out/Flutter_Shutter/flutter_front_95.png)

*In the key figure each column holds the coded photo, its deblur and the still reference at one
light level. The LCD sits in front of the lens. The deblur at f/11 scores MSE 0.00122 against
the reference.*

![The same at f/5.6, f/11 and f/22 with the LCD inside the extension
tube](Out/Flutter_Shutter/flutter_inside_95.png)

*The second flutter figure repeats the three light levels with the LCD inside the extension
tube.*

## Known pitfalls

- **gphoto2 cannot claim the camera** when the desktop has mounted it as a drive.
  `setup_laptop.sh` masks the gvfs camera monitor and `server.py` kills it at start. If gphoto2
  still fails, run `pkill -f gvfs-gphoto2-volume-monitor` and `pkill -f gvfsd-gphoto2`.
- **ModemManager** probes a new serial device for a few seconds after it appears. The first
  connection to the board can fail. `setup_laptop.sh` removes ModemManager.
- **The brltty screen reader** claims CH340 bridges, the chip on Uno clones. The port
  disappears a moment after it appears. `setup_laptop.sh` removes brltty.
- **The shell stays out of `dialout`** until the next login after setup. Use `sg dialout` until
  then.
- **A stripped panel** may pass light where the image is black. Set `PANEL_INVERT` in
  `config.py` to match what you see through the lens.
- **The panel takes 15 to 35 ms to switch.** The flutter runs needed 100 ms chops and a 5 s
  exposure as a result.
- **Invert** may not take every panel to full clear. Watch LCD only flutter shutter before the
  first run.
- **Mains lighting** flickers at 100 Hz and adds its own code to every flutter photo. Use lamps
  on a direct current supply.
- **The panel's pixel grid** prints as a mesh in every bokeh highlight. A laser-cut card has no
  grid.
- **The LCD costs light.** The bokeh lights needed 5 s at ISO 100 through the panel.
- **The group could not hold the car** at a steady speed for the whole 3.2 s code. Its speed wandered
  by 20 to 35 percent, which left most coded and box photos with unequal blur.
- **The score depends on where the car stands.** Its reflections change along the track. A
  photo taken 1,000 px from the reference spot scores worse however sharp it is.
- **LibRaw 0.22** reads the DNGs with a black level 40 to 100 counts too high, which darkens a
  photo by about 5 percent. The scripts read the CR2 instead.
- **The server** rejects a board on another protocol version. Upload the sketch again after
  every pull that changes it.

## References

1. R. Raskar, A. Agrawal and J. Tumblin, "Coded exposure photography: motion deblurring using
   fluttered shutter," *ACM Trans. Graph.*, vol. 25, no. 3, pp. 795-804, 2006.
   [doi:10.1145/1141911.1141957](https://doi.org/10.1145/1141911.1141957)
2. C. Zhou, S. Lin and S. K. Nayar, "Coded aperture pairs for depth from defocus," in *Proc.
   IEEE ICCV*, 2009, pp. 325-332.
   [doi:10.1109/ICCV.2009.5459268](https://doi.org/10.1109/ICCV.2009.5459268)
3. A. Levin, R. Fergus, F. Durand and W. T. Freeman, "Image and depth from a conventional camera
   with a coded aperture," *ACM Trans. Graph.*, vol. 26, no. 3, art. 70, 2007.
   [doi:10.1145/1276377.1276464](https://doi.org/10.1145/1276377.1276464)
4. H. Nagahara, C. Zhou, T. Watanabe, H. Ishiguro and S. K. Nayar, "Programmable aperture
   camera using LCoS," in *Proc. ECCV*, LNCS vol. 6316, 2010, pp. 337-350.
   [doi:10.1007/978-3-642-15567-3_25](https://doi.org/10.1007/978-3-642-15567-3_25)

## Licence

The [MIT Licence](LICENSE) covers this repository.
