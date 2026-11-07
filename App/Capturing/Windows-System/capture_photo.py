"""
capture_photo.py
----------------
Trigger the Canon EOS 60D over USB and save the RAW (.CR2) + JPEG to the
laptop. Meant to run in its own terminal alongside send_pattern.py.

Uses digiCamControl's command-line tool (CameraControlCmd.exe), which drives
Canon bodies through Canon's EDSDK. Install it (free) from
https://digicamcontrol.com/download

Exposure is set by the ISO / SHUTTER / APERTURE variables below and applied
on every shot. The shutter fires without autofocus.

Camera setup:
  - Mode dial on M, otherwise the camera ignores the shutter/aperture values.
  - Set image quality to RAW + JPEG (60D menu: Quality -> RAW + L).
  - Lens switch on MF and focus by hand. For depth from defocus the focus must
    not move between shots.
  - Close the digiCamControl GUI and Canon EOS Utility before running: only
    one program can control the camera at a time.

Examples:
    python capture_photo.py                         # captures/20261025_143012.CR2/.JPG
    python capture_photo.py --name mask1            # captures/mask1.CR2/.JPG
    python capture_photo.py --loop                  # type a name + Enter per shot, q = quit

Existing files are never overwritten: a repeated name becomes mask1_2, mask1_3, ...
"""

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

# ---- Camera settings: edit these -----------------------------------------
# Write values as the camera displays them. Set one to None to leave that
# setting as it is on the camera.
ISO = "200"          # e.g. "100", "200", "400", "800", "1600"
SHUTTER = "2"     # e.g. "1/250", "1/60", "1/4", "1", "2"
APERTURE = "5"     # f-number, e.g. "2.8", "4.0", "5.6", "8.0"
# ---------------------------------------------------------------------------

CMD_CANDIDATES = [
    Path(r"C:\Program Files (x86)\digiCamControl\CameraControlCmd.exe"),
    Path(r"C:\Program Files\digiCamControl\CameraControlCmd.exe"),
]
DEFAULT_OUT = Path(__file__).parent / "captures"
SETTLE_S = 5         # extra wait for file writes to finish after digiCamControl exits
WAIT_MS = 6000       # keep digiCamControl alive after the shot so the JPEG downloads too


def find_cmd(override):
    if override:
        return Path(override)
    for p in CMD_CANDIDATES:
        if p.exists():
            return p
    sys.exit("CameraControlCmd.exe not found. Install digiCamControl from "
             "https://digicamcontrol.com/download or pass --cmd <path>.")


def wait_for_files(folder, expect, timeout):
    """After CameraControlCmd has exited, wait until `expect` files are present
    and their sizes have stopped changing (or `timeout` s pass)."""
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        files = sorted(p for p in folder.iterdir() if p.is_file())
        sizes = [p.stat().st_size for p in files]
        if files and len(files) >= expect and sizes == last:
            return files
        last = sizes
        time.sleep(0.5)
    return sorted(p for p in folder.iterdir() if p.is_file())


def unique_stem(out_dir, stem, suffixes):
    """stem, stem_2, stem_3, ... so neither the CR2 nor the JPG overwrites anything."""
    n, candidate = 1, stem
    while any((out_dir / f"{candidate}{s}").exists() for s in suffixes):
        n += 1
        candidate = f"{stem}_{n}"
    return candidate


def capture(cmd, out_dir, name, expect, timeout):
    staging = Path(tempfile.mkdtemp(prefix="capture_"))
    args = [str(cmd), "/folder", str(staging)]
    for flag, value in (("/iso", ISO), ("/shutter", SHUTTER), ("/aperture", APERTURE)):
        if value is not None:
            args += [flag, value]
    # Without /wait, CameraControlCmd exits as soon as the first file (the
    # RAW) is downloaded and the JPEG transfer gets cut off.
    args += ["/capturenoaf", "/wait", str(WAIT_MS)]

    print(f"Triggering camera: ISO {ISO}, {SHUTTER} s, f/{APERTURE} "
          f"(waiting up to {timeout:.0f} s for the image)...", flush=True)
    t0 = time.time()
    proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    # CameraControlCmd exits once it has downloaded every file of the shot
    # (the JPEG can land seconds after the RAW on long exposures). Letting it
    # exit on its own also releases the camera; killing it leaves the 60D
    # stuck showing "busy" until it is power-cycled.
    try:
        log = proc.communicate(timeout=timeout)[0]
    except subprocess.TimeoutExpired:
        proc.kill()
        log = proc.communicate()[0]
        print("Warning: digiCamControl didn't finish in time. If the camera shows "
              "'busy', switch it off and on (or replug USB).")
    files = wait_for_files(staging, expect, SETTLE_S)

    if not files:
        print(log.strip())
        staging.rmdir()
        print("No image came back from the camera (see output above).")
        return
    if len(files) < expect:
        print(f"Note: got {len(files)} file(s), expected {expect}. "
              f"Set the camera to RAW + L for RAW + JPEG, or use --expect 1.")

    out_dir.mkdir(parents=True, exist_ok=True)
    name = re.sub(r'[<>:"/\\|?*]', "_", name) if name else datetime.now().strftime("%Y%m%d_%H%M%S")
    suffixes = [f.suffix.upper() for f in files]
    stem = unique_stem(out_dir, name, suffixes)
    saved = []
    for f, suffix in zip(files, suffixes):
        dest = out_dir / f"{stem}{suffix}"
        shutil.move(str(f), dest)
        saved.append(dest)
    print(f"Saved in {time.time() - t0:.1f} s: " + ", ".join(str(p) for p in saved))
    try:
        staging.rmdir()   # only succeeds if empty, so a late file is never lost
    except OSError:
        print(f"Warning: more files arrived after saving; they are in {staging}")


def main():
    ap = argparse.ArgumentParser(description="Remote-trigger a Canon DSLR via digiCamControl.")
    ap.add_argument("--name", help="File name for the shot, e.g. mask1 (default: timestamp)")
    ap.add_argument("--loop", action="store_true", help="Keep shooting, asking for a name each time")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Output folder (default: ./captures)")
    ap.add_argument("--expect", type=int, default=2, help="Files per shot (2 = RAW + JPEG)")
    ap.add_argument("--timeout", type=float, default=60, help="Seconds to wait per shot")
    ap.add_argument("--cmd", help="Path to CameraControlCmd.exe if not in the default location")
    args = ap.parse_args()

    cmd = find_cmd(args.cmd)
    shoot = lambda name: capture(cmd, args.out, name, args.expect, args.timeout)

    if not args.loop:
        shoot(args.name)
        return

    print(f"Saving to {args.out.resolve()}")
    print("Type a name and press Enter to shoot (Enter alone = timestamp name, q = quit)")
    while True:
        text = input("name> ").strip()
        if text.lower() == "q":
            break
        shoot(text)


if __name__ == "__main__":
    main()
