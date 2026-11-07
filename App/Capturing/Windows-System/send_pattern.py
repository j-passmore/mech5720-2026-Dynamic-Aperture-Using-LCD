"""
send_pattern.py
---------------
Convert an image (.jpg/.png/...) or a built-in test pattern to pure black and
white and stream it over USB serial to the HERO board running
tft_pattern/tft_pattern.ino. Wiring is documented at the top of that sketch.

The board reports the display resolution itself (160x128 in landscape,
128x160 in portrait), so images are mapped to it pixel for pixel. For
structured light, design patterns at exactly that resolution and save them
as .png: JPEG compression smears sharp edges, and resizing moves them.

Images smaller than the display (e.g. 33x33 coded-aperture masks) are
enlarged by a whole-number factor (each mask cell becomes an exact NxN block)
and centred on black. Use --scale to choose the factor, and --edge top/bottom
to push the mask flush against one of the panel's two short edges instead.

Give several images to toggle between them without reconnecting:
Enter = next, a number = jump to that image, q = quit.

Install:
    pip install pyserial pillow

Examples:
    python send_pattern.py --list-ports
    python send_pattern.py COM5 pattern.jpg
    python send_pattern.py COM5 pattern.jpg --threshold 100 --invert
    python send_pattern.py COM5 --test vstripes:8      # 8 px wide stripes
    python send_pattern.py COM5 --test checker:16 --preview sent.png
    python send_pattern.py COM10 coded_apertures/depth_1_33x33.png coded_apertures/depth_2_33x33.png
    python send_pattern.py COM10 coded_apertures/depth_1_33x33.png --scale 2

"""

import argparse
import sys
import time

import serial
import serial.tools.list_ports
from PIL import Image

BAUD = 115200


def make_test_pattern(spec, width, height):
    """spec: 'checker:N', 'vstripes:N', 'hstripes:N', 'white' or 'black'."""
    name, _, arg = spec.partition(":")
    n = int(arg) if arg else 8
    tests = {
        "checker": lambda x, y: ((x // n) + (y // n)) % 2,
        "vstripes": lambda x, y: (x // n) % 2,
        "hstripes": lambda x, y: (y // n) % 2,
        "white": lambda x, y: 1,
        "black": lambda x, y: 0,
    }
    if name not in tests:
        sys.exit(f"Unknown test pattern '{name}'. Choose from: {', '.join(tests)}")
    f = tests[name]
    img = Image.new("1", (width, height))
    img.putdata([255 * f(x, y) for y in range(height) for x in range(width)])
    return img


def mask_position(w, h, width, height, edge):
    """Top-left corner for a w x h mask. 'top'/'bottom' push it flush against
    one of the panel's two SHORT edges (top/bottom with the panel held in
    portrait), whichever way the sketch's ROTATION is set; 'center' centres it."""
    cx, cy = (width - w) // 2, (height - h) // 2
    if edge == "center":
        return cx, cy
    first = edge == "top"
    if width > height:   # landscape frame: short edges are left/right
        return (0 if first else width - w), cy
    return cx, (0 if first else height - h)


def load_image(path, width, height, threshold, invert, scale=None, edge="center"):
    img = Image.open(path).convert("L")
    if img.width <= width and img.height <= height and img.size != (width, height):
        # Small mask: integer upscale so every cell stays a crisp square block,
        # then centre on a black canvas.
        fit = min(width // img.width, height // img.height)
        s = scale or fit
        if s > fit:
            sys.exit(f"--scale {s} is too big: {img.width}x{img.height} fits at most x{fit}")
        img = img.resize((img.width * s, img.height * s), Image.NEAREST)
        canvas = Image.new("L", (width, height), 255 if invert else 0)
        canvas.paste(img, mask_position(img.width, img.height, width, height, edge))
        img = canvas
    elif img.size != (width, height):
        print(f"Warning: image is {img.size[0]}x{img.size[1]}, display is "
              f"{width}x{height}; resizing (nearest neighbour). For exact "
              f"patterns, supply an image at the display resolution.")
        img = img.resize((width, height), Image.NEAREST)
    # Hard threshold with no dithering, so every pixel is fully on or off.
    return img.point(lambda p: 255 if (p >= threshold) != invert else 0).convert(
        "1", dither=Image.Dither.NONE)


def connect(port):
    ser = serial.Serial(port, BAUD, timeout=3)
    time.sleep(2.0)            # opening the port resets the Uno; let it boot
    ser.reset_input_buffer()
    ser.write(b"?")
    line = ser.readline().decode(errors="replace").strip()
    parts = line.split()
    if len(parts) != 3 or parts[0] != "READY":
        sys.exit(f"Unexpected reply from board: {line!r}. Is tft_pattern.ino uploaded "
                 f"and the Serial Monitor closed?")
    # The boot-time READY and the reply to '?' can both arrive; drop the extra
    # one so it isn't mistaken for the per-row 'R' handshake later.
    time.sleep(0.2)
    ser.reset_input_buffer()
    return ser, int(parts[1]), int(parts[2])


def send(ser, img):
    width, height = img.size
    data = img.tobytes()       # mode '1': MSB first, 1 = white, width/8 bytes per row
    row_bytes = width // 8
    t0 = time.time()
    ser.write(b"I")
    for y in range(height):
        ack = ser.read(1)
        if ack != b"R":
            rest = ser.readline().decode(errors="replace").strip()
            sys.exit(f"Lost sync at row {y}: board said {(ack.decode(errors='replace') + rest)!r}")
        ser.write(data[y * row_bytes:(y + 1) * row_bytes])
    reply = ser.readline().decode(errors="replace").strip()
    if reply != "DONE":
        sys.exit(f"Board reported: {reply}")
    print(f"Sent {width}x{height} image in {time.time() - t0:.2f} s")


def main():
    ap = argparse.ArgumentParser(description="Send a black/white pattern to the TFT.")
    ap.add_argument("port", nargs="?", help="Serial port, e.g. COM5")
    ap.add_argument("images", nargs="*", help="Image file(s) (.jpg, .png, ...); several = toggle mode")
    ap.add_argument("--test", help="Built-in pattern: checker:N, vstripes:N, hstripes:N, white, black")
    ap.add_argument("--threshold", type=int, default=128, help="0-255; pixels >= this become white")
    ap.add_argument("--invert", action="store_true", help="Swap black and white")
    ap.add_argument("--scale", type=int, help="Whole-number upscale for small masks (default: largest that fits)")
    ap.add_argument("--edge", choices=["center", "top", "bottom"], default="center",
                    help="Push small masks flush against one short edge of the panel")
    ap.add_argument("--preview", help="Also save the exact 1-bit frame sent, e.g. sent.png")
    ap.add_argument("--list-ports", action="store_true", help="List serial ports and exit")
    args = ap.parse_args()

    if args.list_ports:
        for p in serial.tools.list_ports.comports():
            print(f"{p.device:8s} {p.description}")
        return
    if not args.port or not (args.images or args.test):
        ap.error("need a port and either image file(s) or --test")

    ser, width, height = connect(args.port)
    print(f"Connected: display is {width}x{height}")

    if args.test:
        img = make_test_pattern(args.test, width, height)
        if args.preview:
            img.save(args.preview)
        send(ser, img)
        ser.close()
        return

    imgs = [load_image(p, width, height, args.threshold, args.invert, args.scale, args.edge)
            for p in args.images]
    if args.preview:
        imgs[0].save(args.preview)

    i = 0
    while True:
        print(f"[{i + 1}/{len(imgs)}] {args.images[i]}")
        send(ser, imgs[i])
        if len(imgs) == 1:
            break
        cmd = input("Enter = next, 1-%d = jump, q = quit: " % len(imgs)).strip().lower()
        if cmd == "q":
            break
        i = int(cmd) - 1 if cmd.isdigit() and 1 <= int(cmd) <= len(imgs) else (i + 1) % len(imgs)
    ser.close()


if __name__ == "__main__":
    main()
