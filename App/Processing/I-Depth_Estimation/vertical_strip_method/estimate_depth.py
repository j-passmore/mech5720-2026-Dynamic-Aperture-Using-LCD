# How to use:
# 1. Copy common.py and dfd.py from another depth method into this folder.
# 2. Change SCENE below to the capture folder you want to use.
# 3. Run: python estimate_depth.py
# 4. The depth map and two pictures are saved in
#    I-Depth_Estimation/vertical_strip_method/output/.
# 5. Copy output/depth_mm.npy into
#    II-Post_Capture_Reconstruction/vertical_strip_method/, next to reconstruct.py.
#
# Each window picks a depth. Each vertical strip uses its most common window depth.
# Then nearby strong image edges are used to move the boundaries between depths.

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm
import numpy as np
from scipy import fft
from scipy import ndimage as ndi
from scipy.signal import find_peaks

import dfd
from common import (CAPTURES, CALIBRATION_FILE, MASTER_DARK_FILE,
                    SCENE_NAME, downsample, load_green, to_display)

SCENE = "Scale_1/pair2"
DOWNSAMPLE = 2
WINDOW = 448
X_STRIDE = 96
Y_STRIDE = 256
EDGE_RADIUS = 450  # How far a boundary can move toward a strong image edge.
OUTPUT = Path(__file__).resolve().parent / "output"


def window_positions(length, step):
    positions = list(range(0, length - WINDOW + 1, step))
    if positions[-1] != length - WINDOW:
        positions.append(length - WINDOW)
    return np.asarray(positions)


def make_references(psf_pairs):
    vertical = fft.fftfreq(WINDOW)[:, None]
    horizontal = fft.rfftfreq(WINDOW)[None, :]
    frequency = np.hypot(horizontal, vertical)
    references, strengths = [], []

    for psf1, psf2 in psf_pairs:
        power1 = ndi.gaussian_filter(
            abs(fft.rfft2(psf1 / psf1.sum(), s=(WINDOW, WINDOW)))**2, 1.5)
        power2 = ndi.gaussian_filter(
            abs(fft.rfft2(psf2 / psf2.sum(), s=(WINDOW, WINDOW)))**2, 1.5)
        references.append(np.clip(
            np.log(np.maximum(power2, 2e-6)) - np.log(np.maximum(power1, 2e-6)), -7, 7))
        strengths.append((power1 + power2) / 2)

    supported = ((frequency >= 0.007) & (frequency <= 0.22) &
                 (np.median(strengths, axis=0) > 1e-5))
    return np.asarray(references), frequency, supported


def compare_window(image1, image2, reference_data, minimum_texture):
    # Compare this window with each measured depth.
    references, frequency, supported = reference_data
    brightness1 = np.maximum(image1, 0).mean()
    brightness2 = np.maximum(image2, 0).mean()
    if min(brightness1, brightness2) <= 1e-8:
        return -1

    image1 = image1 / brightness1
    image2 = image2 / brightness2
    image1 -= image1.mean()
    image2 -= image2.mean()
    texture = np.sqrt(np.mean(image1**2 + image2**2) / 2)
    if texture < minimum_texture:
        return -1

    fade = np.hanning(WINDOW)
    fade = fade[:, None] * fade[None, :]
    power1 = ndi.gaussian_filter(abs(fft.rfft2(image1 * fade))**2, 1.5)
    power2 = ndi.gaussian_filter(abs(fft.rfft2(image2 * fade))**2, 1.5)

    noise_frequencies = frequency > 0.38
    noise1 = max(float(np.percentile(power1[noise_frequencies], 30)), 1e-15)
    noise2 = max(float(np.percentile(power2[noise_frequencies], 30)), 1e-15)
    minimum1 = max(2 * noise1, 0.001 * np.percentile(power1[supported], 95))
    minimum2 = max(2 * noise2, 0.001 * np.percentile(power2[supported], 95))
    good = supported & (power1 > minimum1) & (power2 > minimum2)
    if good.sum() < 35:
        return -1

    measured = (np.log(np.maximum(power2 - noise2, noise2 * 0.2)) -
                np.log(np.maximum(power1 - noise1, noise1 * 0.2)))[good]
    weights = np.sqrt(
        np.clip(np.log1p(power1[good] / noise1), 0, 25) *
        np.clip(np.log1p(power2[good] / noise2), 0, 25))
    weights = np.maximum(weights, 0.1)

    differences = []
    for expected in references:
        error = measured - expected[good]
        order = np.argsort(error)
        middle = np.searchsorted(np.cumsum(weights[order]), weights.sum() / 2)
        error -= error[order[min(middle, len(order) - 1)]]
        size = abs(error)
        penalty = np.where(size <= 1.5, size**2, 3 * size - 2.25)
        differences.append(np.sqrt(np.average(penalty, weights=weights)))
    return int(np.argmin(differences))


def measure_vertical_edges(image1, image2):
    # Find strong vertical edges that run through much of the image.
    profiles = []
    for image in (image1, image2):
        image = np.maximum(image, 0)
        image = image / max(float(np.percentile(image, 95)), 1e-8)
        smoothed = ndi.gaussian_filter(image, (14, 12), mode="reflect")
        change = np.gradient(smoothed, axis=1)
        change = change[int(0.07 * len(change)):int(0.93 * len(change))]
        profiles.append(0.7 * abs(change.mean(axis=0)) +
                        0.3 * abs(np.median(change, axis=0)))
    return ndi.gaussian_filter1d(np.mean(profiles, axis=0), 2)


def refine_boundaries(rough_boundaries, edge_strength, width):
    # Move depth boundaries to nearby strong edges, as in the original V3.
    corrected = rough_boundaries.copy()
    for index, rough in enumerate(rough_boundaries):
        left = max(int(rough) - EDGE_RADIUS, int(0.08 * width), 1)
        right = min(int(rough) + EDGE_RADIUS, int(0.92 * width), width - 2)
        if index:
            left = max(left, int((rough_boundaries[index - 1] + rough) / 2) + 1)
        if index + 1 < len(rough_boundaries):
            right = min(right, int((rough + rough_boundaries[index + 1]) / 2) - 1)
        if right <= left:
            continue

        nearby = edge_strength[left:right + 1]
        peaks, _ = find_peaks(nearby,
                              prominence=max(nearby.max() * 0.12, 1e-12), distance=12)
        if not len(peaks):
            continue
        candidates = peaks + left
        preference = edge_strength[candidates] * np.exp(
            -0.5 * ((candidates - rough) / EDGE_RADIUS)**2)
        best = int(candidates[np.argmax(preference)])
        if edge_strength[best] >= max(2 * np.median(nearby),
                                      np.percentile(nearby, 85), 0.0006):
            corrected[index] = best
    return corrected


def estimate_depth(image1, image2, psf_pairs, distances):
    height, width = image1.shape
    xs = window_positions(width, X_STRIDE)
    ys = window_positions(height, Y_STRIDE)
    references = make_references(psf_pairs)

    # Work out which windows have enough image detail to measure depth.
    textures = []
    for x in xs:
        for y in ys:
            first = image1[y:y + WINDOW, x:x + WINDOW]
            second = image2[y:y + WINDOW, x:x + WINDOW]
            first = first / max(np.maximum(first, 0).mean(), 1)
            second = second / max(np.maximum(second, 0).mean(), 1)
            textures.append(np.sqrt((first.var() + second.var()) / 2))
    minimum_texture = 0.06 * max(np.percentile(textures, 90), 1e-8)

    window_depths = np.empty((len(ys), len(xs)), dtype=int)
    for col, x in enumerate(xs):
        for row, y in enumerate(ys):
            window_depths[row, col] = compare_window(
                image1[y:y + WINDOW, x:x + WINDOW],
                image2[y:y + WINDOW, x:x + WINDOW],
                references, minimum_texture)

    # Use the most common window depth in each vertical strip.
    strip_depths = []
    for col in range(len(xs)):
        guesses = window_depths[:, col]
        guesses = guesses[guesses >= 0]
        strip_depths.append(np.bincount(guesses, minlength=len(distances)).argmax())

    x_centres = xs + WINDOW / 2
    y_centres = ys + WINDOW / 2
    x_edges = np.r_[0, np.rint((x_centres[:-1] + x_centres[1:]) / 2).astype(int), width]
    y_edges = np.r_[0, (y_centres[:-1] + y_centres[1:]) / 2, height]

    # Find boundaries where the most common depth changes.
    strip_depths = np.asarray(strip_depths)
    before_correction = np.empty(width, dtype=int)
    for col, depth in enumerate(strip_depths):
        before_correction[x_edges[col]:x_edges[col + 1]] = depth

    changes = np.flatnonzero(strip_depths[1:] != strip_depths[:-1])
    rough_boundaries = x_edges[changes + 1]
    edges = measure_vertical_edges(image1, image2)
    boundaries = refine_boundaries(rough_boundaries, edges, width)

    # Use the corrected boundaries to fill in the final depth map.
    positions = np.r_[0, boundaries, width]
    region_depths = strip_depths[np.r_[0, changes + 1]]
    final_depths = np.empty(width, dtype=int)
    for index, depth in enumerate(region_depths):
        final_depths[positions[index]:positions[index + 1]] = depth

    return window_depths, x_edges, y_edges, before_correction, final_depths


def main():
    with np.load(CALIBRATION_FILE) as data:
        distances = np.asarray(data["depths_mm"], dtype=float)
        psf_pairs = np.asarray(data["kernels"])
    order = np.argsort(distances)
    distances, psf_pairs = distances[order], psf_pairs[order]

    dark = np.load(MASTER_DARK_FILE)
    folder = CAPTURES / SCENE
    images = [load_green(folder / SCENE_NAME.format(mask=mask))[0] - dark
              for mask in (1, 2)]
    image1, image2 = [downsample(image, DOWNSAMPLE) for image in images]
    psfs = dfd.prepare_kernels(psf_pairs, DOWNSAMPLE)
    windows, x_edges, y_edges, combined, corrected = estimate_depth(
        image1, image2, psfs, distances)

    OUTPUT.mkdir(exist_ok=True)
    depth_map = np.broadcast_to(distances[corrected][None, :], image1.shape).copy()
    np.save(OUTPUT / "depth_mm.npy", depth_map)

    palette = plt.get_cmap("jet", len(distances)).copy()
    palette.set_bad("black")
    norm = BoundaryNorm(np.arange(len(distances) + 1) - 0.5, len(distances))
    final_ids = np.broadcast_to(corrected[None, :], image1.shape)

    fig, ax = plt.subplots(figsize=(10, 6), layout="constrained")
    plot = ax.imshow(final_ids, cmap=palette, norm=norm, interpolation="nearest")
    ax.axis("off")
    bar = fig.colorbar(plot, ax=ax, ticks=range(len(distances)))
    bar.ax.set_yticklabels([f"{d:g} mm" for d in distances])
    fig.savefig(OUTPUT / "depth_map.png", dpi=150)
    plt.close(fig)

    # Show the window guesses, the majority vote, and the corrected boundaries.
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), layout="constrained")
    axes[0, 0].imshow(to_display(np.maximum(image1, 0)), cmap="gray")
    axes[0, 0].set_title("Original")
    axes[0, 1].pcolormesh(x_edges, y_edges, np.ma.masked_less(windows, 0),
                          cmap=palette, norm=norm, shading="flat")
    axes[0, 1].set_xlim(0, image1.shape[1])
    axes[0, 1].set_ylim(image1.shape[0], 0)
    axes[0, 1].set_title("Window depths")
    axes[1, 0].imshow(np.broadcast_to(combined[None, :], image1.shape),
                      cmap=palette, norm=norm, interpolation="nearest")
    axes[1, 0].set_title("Most common depth per strip")
    plot = axes[1, 1].imshow(final_ids, cmap=palette, norm=norm,
                            interpolation="nearest")
    axes[1, 1].set_title("After edge correction")
    for ax in axes.flat:
        ax.axis("off")
        ax.set_aspect("equal")
    bar = fig.colorbar(plot, ax=axes, ticks=range(len(distances)))
    bar.ax.set_yticklabels([f"{d:g} mm" for d in distances])
    fig.savefig(OUTPUT / "depth_steps.png", dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    main()
