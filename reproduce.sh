#!/usr/bin/env bash
# Rebuilds every figure in Out/ from the raw photos in Captures/ with one venv.
# Run from anywhere: ./reproduce.sh
set -e
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
  python3 -m venv .venv
  .venv/bin/pip install --quiet -r requirements.txt
fi
P="$PWD/.venv/bin/python"
echo "== I. Depth estimation"
(cd App/Processing/I-Depth_Estimation && "$P" calibrate.py --allow-saturated && "$P" psf_fourier.py && "$P" pixel_by_pixel_method/estimate_depth.py)
echo "== II. Post-capture reconstruction"
(cd App/Processing/II-Post_Capture_Reconstruction && "$P" pixel_by_pixel_method/reconstruct.py && "$P" vertical_strip_method/reconstruct.py)
echo "== III. Custom bokeh"
(cd App/Processing/III-Custom_Bokeh && "$P" bokeh_figure.py)
echo "== IV. Flutter shutter"
(cd App/Processing/IV-Flutter_Shutter && "$P" flutter_figure.py)
echo "Done. The figures are in Out/."
