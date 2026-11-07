"""
psf_fourier.py
--------------
Show the calibrated PSF pairs in the Fourier domain (their OTF magnitudes).

For the coded-aperture pair method the useful property is that the two masks'
spectra have zeros in DIFFERENT places, so together they cover all
frequencies. The figure shows, per depth:

    row 1   |K1(f)|               mask-1 OTF magnitude
    row 2   |K2(f)|               mask-2 OTF magnitude
    row 3   sqrt(|K1|^2 + |K2|^2) combined pair coverage (dark = lost in both)
    row 4   radially averaged profiles of all three

All spectra are log10 magnitude, relative to the mask-1 DC term (= 1 because
the mask-1 PSF sums to 1), on one shared colour scale.

Reads Out/Depth_Estimation/calibration/calibration.npz, so run calibrate.py
on the v2 PSFs first. Run from this folder (App/Processing/I-Depth_Estimation/):
    python calibrate.py --psf-dir Scale_1/psfs_v2 --psf-name "m{mask}_psf{index}.CR2"
    python psf_fourier.py
    python psf_fourier.py --fmax 0.5 --floor -5
"""

import argparse
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from common import CALIBRATION_FILE, OUTPUT


def otf_mag(kernel):
    """Centred |FFT| of a PSF, with the PSF centre moved to the origin so the
    phase ramp from the crop offset does not matter (magnitude is unchanged
    anyway, but this keeps the convention the same as dfd.psf2otf)."""
    return np.abs(np.fft.fftshift(np.fft.fft2(np.fft.ifftshift(kernel))))


def radial_mean(img, freqs):
    """Mean of img in rings of radial frequency, returned at bin centres."""
    fy, fx = np.meshgrid(freqs, freqs, indexing="ij")
    fr = np.hypot(fy, fx).ravel()
    bins = np.linspace(0, 0.5, 101)
    idx = np.digitize(fr, bins) - 1
    ok = (idx >= 0) & (idx < len(bins) - 1)
    sums = np.bincount(idx[ok], img.ravel()[ok], len(bins) - 1)
    counts = np.bincount(idx[ok], minlength=len(bins) - 1)
    return 0.5 * (bins[1:] + bins[:-1]), sums / np.maximum(counts, 1)


def main():
    ap = argparse.ArgumentParser(description="Plot calibrated PSF pairs in the Fourier domain.")
    ap.add_argument("--fmax", type=float, default=0.25,
                    help="Show frequencies up to this many cycles/pixel (Nyquist = 0.5, default 0.25)")
    ap.add_argument("--floor", type=float, default=-4,
                    help="Bottom of the log10 colour scale (default -4)")
    ap.add_argument("--out", default=str(OUTPUT / "psf_fourier.png"), help="Output figure path")
    args = ap.parse_args()

    if not CALIBRATION_FILE.exists():
        sys.exit(f"Missing {CALIBRATION_FILE} - run calibrate.py first")
    cal = np.load(CALIBRATION_FILE)
    kernels, depths = cal["kernels"], cal["depths_mm"]
    psf_dir = str(cal["psf_dir"])
    if "v2" not in psf_dir:
        print(f"Warning: calibration.npz was built from {psf_dir}, not the v2 PSFs")

    size = kernels.shape[-1]
    freqs = np.fft.fftshift(np.fft.fftfreq(size))          # cycles / half-res pixel
    keep = np.abs(freqs) <= args.fmax
    extent = [freqs[keep][0], freqs[keep][-1], freqs[keep][-1], freqs[keep][0]]

    n = len(depths)
    fig = plt.figure(figsize=(3 * n, 12.5))
    gs = fig.add_gridspec(4, n + 1, height_ratios=[1, 1, 1, 1.1], width_ratios=[1] * n + [0.06],
                          hspace=0.35, wspace=0.08)
    row_names = ["|K1|  mask 1", "|K2|  mask 2", "pair  √(|K1|²+|K2|²)"]
    colours = ["tab:blue", "tab:orange", "k"]

    for j, (k1, k2) in enumerate(kernels):
        mags = [otf_mag(k1), otf_mag(k2)]
        mags.append(np.hypot(*mags))
        for r, mag in enumerate(mags):
            ax = fig.add_subplot(gs[r, j])
            im = ax.imshow(np.log10(np.maximum(mag[np.ix_(keep, keep)], 1e-12)),
                           cmap="magma", vmin=args.floor, vmax=0, extent=extent)
            if r == 0:
                ax.set_title(f"{depths[j]:.0f} mm", fontsize=11)
            if j == 0:
                ax.set_ylabel(f"{row_names[r]}\nfy (cyc/px)", fontsize=9)
            else:
                ax.set_yticklabels([])
            ax.set_xlabel("fx (cyc/px)", fontsize=8)
            ax.tick_params(labelsize=7)

        ax = fig.add_subplot(gs[3, j])
        for mag, c, lab in zip(mags, colours, ["mask 1", "mask 2", "pair"]):
            fr, prof = radial_mean(mag, freqs)
            ax.semilogy(fr, prof, color=c, lw=1.4, label=lab)
        ax.set_xlim(0, args.fmax)
        ax.set_ylim(10 ** args.floor, 2)
        ax.grid(True, which="major", alpha=0.3)
        ax.set_xlabel("radial freq (cyc/px)", fontsize=8)
        ax.tick_params(labelsize=7)
        if j == 0:
            ax.set_ylabel("radial mean |K|", fontsize=9)
            ax.legend(fontsize=8, frameon=False)
        else:
            ax.set_yticklabels([])

    cbar = fig.colorbar(im, cax=fig.add_subplot(gs[:3, n]))
    cbar.set_label("log10 |K|  (rel. mask-1 DC)")
    fig.suptitle(f"PSF pairs in the Fourier domain ({psf_dir}, {size}x{size} px half-res green)",
                 fontsize=13)
    fig.savefig(args.out, dpi=110, bbox_inches="tight")
    print(f"Saved {args.out}")


if __name__ == "__main__":
    main()
