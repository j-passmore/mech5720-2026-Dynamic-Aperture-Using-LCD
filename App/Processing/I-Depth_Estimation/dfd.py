"""
dfd.py
------
Core depth-from-defocus algorithm for a coded aperture pair, after
Zhou, Lin & Nayar, "Coded Aperture Pairs for Depth from Defocus" (ICCV 2009).

Model: the two captured images are the same sharp scene F blurred by the
PSF pair of the (unknown) depth d, plus noise:
    I1 = F * K1(d) + n1,   I2 = F * K2(d) + n2

For each candidate depth d, the sharp image is estimated by the generalised
Wiener deconvolution of BOTH images at once (paper eq. for F0):

            I1 . conj(K1) + I2 . conj(K2)
    F0  =  -------------------------------          (in the Fourier domain)
            |K1|^2 + |K2|^2 + |C|^2

where |C|^2 = sigma^2 / A(xi) is the noise-to-signal ratio from a natural
image prior. With the usual 1/|xi|^2 power spectrum for natural images this
is |C|^2 = lam * |xi|^2, with `lam` the noise-to-signal weight.

F0 is then re-blurred with the same PSF pair and compared with the captures.
The reconstruction error
    W(d) = |F0 * K1 - I1|^2 + |F0 * K2 - I2|^2
is averaged over a local window, and each pixel takes the depth with the
smallest W(d). Only the correct PSF pair explains both images at once, which
is what makes the complementary aperture pair discriminative.
"""

import numpy as np
from scipy import fft as sfft
from scipy import ndimage as ndi

from common import downsample


def prepare_kernels(kernels, factor):
    """Downsample PSF pairs to the processing resolution. Each pair is
    renormalised so mask 1 sums to 1 and mask 2 keeps its relative weight."""
    out = []
    for k1, k2 in kernels:
        d1, d2 = downsample(k1, factor), downsample(k2, factor)
        s = d1.sum()
        out.append((d1 / s, d2 / s))
    return out


def psf2otf(kernel, shape):
    """Zero-pad a centred kernel to `shape` and move its centre to the origin."""
    pad = np.zeros(shape)
    kh, kw = kernel.shape
    pad[:kh, :kw] = kernel
    pad = np.roll(pad, (-(kh // 2), -(kw // 2)), axis=(0, 1))
    return sfft.rfft2(pad)


def estimate(I1, I2, kernels, lam=1e-3, window=31):
    """Run the depth search.

    I1, I2   : dark-subtracted images (same exposure), 2-D float arrays
    kernels  : list of (K1, K2) spatial PSF pairs, one per candidate depth
    lam      : noise-to-signal weight of the 1/f^2 image prior
    window   : side of the square window the error is averaged over (px)

    Returns (errors, latents):
        errors  (n_depths, H, W)  locally averaged reconstruction error
        latents (n_depths, H, W)  deconvolved sharp image for each depth
    """
    H, W = I1.shape
    # Work in units of the mean signal so `lam` doesn't depend on exposure.
    scale = max(float(np.mean(I1 + I2) / 2), 1e-9)
    I1, I2 = I1 / scale, I2 / scale

    # Reflect-pad by the kernel radius (avoids wrap-around at the borders),
    # then up to an FFT-friendly size.
    m = max(max(k1.shape) for k1, _ in kernels) // 2 + 1
    Ht = sfft.next_fast_len(H + 2 * m)
    Wt = sfft.next_fast_len(W + 2 * m, real=True)
    pads = ((m, Ht - H - m), (m, Wt - W - m))
    P1, P2 = np.pad(I1, pads, mode="reflect"), np.pad(I2, pads, mode="reflect")
    F1, F2 = sfft.rfft2(P1), sfft.rfft2(P2)
    inner = (slice(m, m + H), slice(m, m + W))

    fy = sfft.fftfreq(Ht)[:, None]
    fx = sfft.rfftfreq(Wt)[None, :]
    C2 = lam * (fx ** 2 + fy ** 2)

    errors = np.empty((len(kernels), H, W), np.float32)
    latents = np.empty((len(kernels), H, W), np.float32)
    for d, (k1, k2) in enumerate(kernels):
        K1, K2 = psf2otf(k1, (Ht, Wt)), psf2otf(k2, (Ht, Wt))
        F0 = (F1 * np.conj(K1) + F2 * np.conj(K2)) / (np.abs(K1) ** 2 + np.abs(K2) ** 2 + C2)
        r1 = sfft.irfft2(F0 * K1, (Ht, Wt))[inner] - I1
        r2 = sfft.irfft2(F0 * K2, (Ht, Wt))[inner] - I2
        errors[d] = ndi.uniform_filter(r1 ** 2 + r2 ** 2, window)
        latents[d] = sfft.irfft2(F0, (Ht, Wt))[inner] * scale
    return errors, latents


def select_depth(errors):
    """Index of the best depth per pixel, and a confidence margin: how much
    larger the second-best error is than the best, (e2 - e1) / e1."""
    order = np.sort(errors, axis=0)
    best = np.argmin(errors, axis=0)
    margin = (order[1] - order[0]) / np.maximum(order[0], 1e-12)
    return best, margin


def compose(latents, best):
    """All-in-focus image: each pixel from the deconvolution at its depth."""
    return np.take_along_axis(latents, best[None], axis=0)[0]
