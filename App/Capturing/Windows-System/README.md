# Windows capture tools

Emma took the depth estimation photos with these tools on a Windows laptop. One script fires the
camera. A second sends each mask to the panel through an Arduino.

| File | What it does |
| --- | --- |
| [capture_photo.py](capture_photo.py) | It fires the EOS 60D through `CameraControlCmd.exe` from [digiCamControl](https://digicamcontrol.com/download). It saves the CR2 and the JPEG to `captures/`. Set `ISO`, `SHUTTER` and `APERTURE` at the top of the script. |
| [send_pattern.py](send_pattern.py) | It turns an image into pure black and white and sends it to the board over USB serial. It enlarges a 33x33 mask by a whole number so every cell stays square. |
| [tft_pattern/tft_pattern.ino](tft_pattern/tft_pattern.ino) | The sketch runs on an Uno compatible board. It draws each image from `send_pattern.py` on an Adafruit 1.8 inch ST7735 panel. The wiring sits at the top of the sketch. |
| [check_saturation.py](check_saturation.py) | It reports clipped green photosites in every photo of a folder. Reshoot any PSF it flags. |
| [coded_apertures/](coded_apertures) | The folder holds the two 33x33 masks of Zhou, Lin and Nayar as 1-bit PNGs with enlarged previews. |

```bash
pip install -r requirements.txt
python send_pattern.py --list-ports
python send_pattern.py COM10 coded_apertures/depth_1_33x33.png coded_apertures/depth_2_33x33.png
python capture_photo.py --loop
python check_saturation.py captures --raw-only
```

Put the camera on M with RAW + L quality and the lens on MF. Close digiCamControl and EOS Utility
before you run `capture_photo.py`. Only one program can hold the camera at a time. Copy the photos
into [Captures/Depth_Estimation](../../../Captures/Depth_Estimation) in the layout
[the depth README](../../Processing/I-Depth_Estimation/README.md) lists.
