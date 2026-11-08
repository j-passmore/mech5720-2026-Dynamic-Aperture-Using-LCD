"""Figures for the custom bokeh section: the principle, the results and the appendix montage.

Reads bokeh_summary.json and Y_all.npz from the out folder, and the raw photos for the colour
crops of the lights. Writes to the out folder:
  bokeh_principle.png   (a) the aperture stamps its shape onto every out-of-focus light, (b) a simulation
  bokeh_results.png     (a) four patterns and the light that showed them best at each panel position,
                        (b) NCC against field angle per light, (c) NCC by pattern group with the controls
  bokeh_ncc.png         panels (b) and (c) of bokeh_results.png on their own, as (a) and (b)
  bokeh_montage.png     every pattern and the light that showed it, for the appendix

Run from this folder:
  python3 make_bokeh_figures.py
  python3 make_bokeh_figures.py --captures ../../../../Captures/Custom_Bokeh --out ../../../../Out/Custom_Bokeh/ncc
"""
import json
from pathlib import Path

import cv2
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import Polygon  # noqa: E402

from bokeh_ncc import STAGE_MM, STAGES, develop, parse_args, pattern_mask, photos  # noqa: E402

plt.rcParams.update({"font.size": 7, "font.family": "serif", "axes.linewidth": 0.6, "xtick.major.width": 0.6, "ytick.major.width": 0.6})
SHORT = {"mario_binary_walk_1": "Mario 1", "mario_binary_walk_2": "Mario 2", "mario_binary_walk_3": "Mario 3",
         "knight_binary_walk_1": "Knight 1", "knight_binary_walk_2": "Knight 2",
         "link_binary_attack_1": "Link attack 1", "link_binary_attack_2": "Link attack 2",
         "zhou_a": "Zhou A", "zhou_b": "Zhou B", "nayar": "Nayar", "levin": "Levin"}
POS = {"outside": "LCD in front", "inside": "LCD in tube"}
C_OUT, C_IN = "#1f77b4", "#d95f02"
ROWS = ["mario_binary_walk_1", "knight_binary_walk_1", "link_binary_attack_1", "zhou_a"]   # the patterns in the results figure
GROUPS = [("mario", "Mario"), ("knight", "Knight"), ("link", "Link\nattack"), ("zhou", "Zhou\nA, B"), ("nayar_levin", "Nayar,\nLevin")]
GAMMA = 1 / 2.2                      # display gamma for the colour crops, which come from the linear raw frames
# where panels (b) and (c) sit in the results figure, and where their labels go
PANEL_B, PANEL_C = [0.45, 0.17, 0.255, 0.72], [0.775, 0.17, 0.215, 0.72]
LABEL_B, LABEL_C = 0.41, 0.735
FIG_W, FIG_H = 7.16, 2.75


def displayed(pattern, stage):
    return pattern_mask(pattern, STAGE_MM[stage])


def best_light(S, Y, stage, pats):
    """the light with the best worst-case contrast over the patterns shown (decided from frames only)"""
    best, bl = -1, None
    yy, xx = np.indices(Y[f"{stage}|zhou_a"].shape)
    for lid, L in S[stage]["lights"].items():
        rad = np.hypot(xx - L["cx"], yy - L["cy"])
        c = min(float(Y[f"{stage}|{p}"][rad < 0.6 * L["r"]].mean() / Y[f"{stage}|{p}"][(rad > 1.15 * L["r"]) & (rad < 1.6 * L["r"])].mean()) for p in pats)
        if c > best:
            best, bl = c, lid
    return bl


def light_crop(rgb, L, scale=1.0):
    """a colour crop about a light from the half-size linear frame, display-referred with a per-crop gain"""
    cx, cy, d0 = L["cx"], L["cy"], L["d0"]
    half = int(0.85 * d0 * scale)
    x0, y0 = max(cx - half, 0), max(cy - half, 0)
    crop = rgb[y0:cy + half, x0:cx + half]
    crop = cv2.resize(crop, (240, int(240 * crop.shape[0] / crop.shape[1])), interpolation=cv2.INTER_AREA)
    g = crop / max(float(np.percentile(crop, 99.7)), 1e-6)
    return np.clip(g, 0, 1) ** GAMMA


def colour_crops(S, captures, wanted):
    """{(stage, pattern, light): crop} for every triple in wanted, developing each raw photo once"""
    crops = {}
    for stage, folder in STAGES.items():
        found, _ = photos(captures / folder)
        for p in sorted({q for st, q, _ in wanted if st == stage}):
            rgb = develop(found[p]).astype(np.float32) / 65535.0
            for st, q, light in wanted:
                if st == stage and q == p:
                    crops[(stage, p, light)] = light_crop(rgb, S[stage]["lights"][str(light)])
            print("developed", found[p].name, flush=True)
    return crops


# ------------------------------------------------------------------ principle figure (literature review)
def principle(out):
    fig = plt.figure(figsize=(3.45, 2.15))
    ax = fig.add_axes([0.0, 0.0, 0.64, 1.0])
    ax.set_xlim(-1.55, 2.35); ax.set_ylim(-1.5, 1.6); ax.axis("off")
    xl, xs, xi = 0.0, 1.9, 1.15            # lens, sensor, image plane of the far light
    ax.plot([-1.3, xs], [0, 0], color="0.7", lw=0.5, ls=":")
    ax.plot([xl, xl], [-1.15, 1.15], color="k", lw=1.0)
    ax.annotate("", xy=(xl, 1.15), xytext=(xl, 1.0), arrowprops=dict(arrowstyle="-|>", lw=0.7, color="k"))
    ax.annotate("", xy=(xl, -1.15), xytext=(xl, -1.0), arrowprops=dict(arrowstyle="-|>", lw=0.7, color="k"))
    ax.plot([xs, xs], [-1.1, 1.1], color="k", lw=1.4)
    # aperture A(x): closed bars drawn thick, open gaps left clear
    openings = [(-0.9, -0.45), (-0.15, 0.3), (0.55, 0.85)]
    edges = [-1.0] + [v for o in openings for v in o] + [1.0]
    for a, b in zip(edges[0::2], edges[1::2]):
        ax.plot([xl - 0.12, xl - 0.12], [a, b], color="k", lw=3.2, solid_capstyle="butt")
    src = (-1.3, 0.0)
    cols = ["#1b9e77", "#7570b3", "#e7298a"]
    for (a, b), c in zip(openings, cols):
        for y in (a, b):
            ax.plot([src[0], xl - 0.12], [src[1], y], color=c, lw=0.4)
        ya, yb = a * (1 - xs / xi), b * (1 - xs / xi)            # position on the sensor, inverted because xs > xi
        poly = Polygon([[xl - 0.12, a], [xl - 0.12, b], [xs, yb], [xs, ya]], closed=True, alpha=0.22, color=c, lw=0)
        ax.add_patch(poly)
        for y, yy in ((a, ya), (b, yb)):
            ax.plot([xl - 0.12, xi, xs], [y, 0, yy], color=c, lw=0.4)
        ax.plot([xs, xs], [ya, yb], color=c, lw=3.0, solid_capstyle="butt")
    ax.plot(*src, "o", color="#b8860b", ms=3.5)
    ax.text(src[0], -0.16, "light", ha="center", va="top", fontsize=6)
    ax.text(xl - 0.12, 1.3, "aperture", ha="center", fontsize=6)
    ax.text(xs, 1.28, "sensor", ha="center", fontsize=6)
    ax.text(xi, -0.2, "image\nplane", ha="center", va="top", fontsize=5.5, color="0.35")
    ax.plot([xi, xi], [-0.08, 0.08], color="0.35", lw=0.6)
    ax.text(-1.5, 1.55, "(a)", ha="left", va="top", fontsize=7)
    ax.text(xl - 0.12, -1.42, "aperture $A(\\mathbf{x})$ at the lens", ha="center", fontsize=5.5, color="0.35")
    # simulation (b)
    bx = fig.add_axes([0.66, 0.06, 0.34, 0.88]); bx.axis("off")
    mask = pattern_mask("mario_binary_walk_1", 9.5)
    size = 36
    canvas = np.zeros((190, 120), np.float32)
    lights = [(34, 24, 0.62), (96, 70, 0.0), (36, 145, -0.95)]
    for (x, y, s) in lights:
        if abs(s) < 0.05:
            canvas[y - 1:y + 2, x - 1:x + 2] += 1.0
            continue
        d = int(round(size * abs(s) * 1.4))
        t = cv2.resize(mask if s > 0 else mask[::-1, ::-1], (d, d), interpolation=cv2.INTER_NEAREST)
        t = cv2.GaussianBlur(t, (0, 0), 0.6)
        y0, x0 = y - d // 2, x - d // 2
        canvas[max(y0, 0):y0 + d, max(x0, 0):x0 + d] += t[max(-y0, 0):, max(-x0, 0):][:canvas.shape[0] - max(y0, 0), :canvas.shape[1] - max(x0, 0)]
    bx.imshow(np.clip(canvas, 0, 1) ** 0.8, cmap="gray", interpolation="bilinear")
    bx.text(2, 6, "(b)", ha="left", va="top", fontsize=7, color="w")
    bx.text(34, 62, "$s_u>0$", color="w", fontsize=6, ha="center"); bx.text(96, 84, "$s_u\\approx0$", color="w", fontsize=6, ha="center"); bx.text(36, 186, "$s_u<0$", color="w", fontsize=6, ha="center")
    fig.savefig(out / "bokeh_principle.png", dpi=400, facecolor="white")
    plt.close(fig)


# ------------------------------------------------------------------ results figure
def angle_panel(ax, S):
    """NCC against field angle, lights are the replicates"""
    for st, c, mk in (("outside", C_OUT, "o"), ("inside", C_IN, "s")):
        pl = S[st]["per_light"]; th = np.array(pl["theta"]); cm = np.array(pl["correct"]); dm = np.array(pl["other_mean"])
        ax.scatter(th, cm, s=16, color=c, marker=mk, zorder=3, label=f"{POS[st]}, displayed pattern")
        ax.scatter(th, dm, s=16, facecolors="none", edgecolors=c, marker=mk, zorder=3, label=f"{POS[st]}, other ten patterns")
        f = S[st]["angle_fit"]; xs = np.linspace(th.min(), th.max(), 20); ax.plot(xs, f["slope_per_deg"] * xs + f["intercept"], color=c, lw=0.7)
    ax.set_xlabel("field angle (deg)"); ax.set_ylabel("mean NCC over 11 patterns"); ax.set_ylim(0.4, 0.95)
    ax.grid(alpha=0.25, lw=0.4); ax.legend(fontsize=5.2, frameon=False, loc="lower left", handletextpad=0.2, borderpad=0.1)


def group_panel(ax, S):
    """NCC by pattern group, with the other-ten mean (black) and the open disc (grey) as ticks"""
    for k, (st, c) in enumerate((("outside", C_OUT), ("inside", C_IN))):
        for i, (g, _) in enumerate(GROUPS):
            gs_ = S[st]["group_stats"][g]; x = i + (-0.19 if k == 0 else 0.19)
            ax.bar(x, gs_["correct_mean"], width=0.34, color=c, alpha=0.85, zorder=2, label=f"{POS[st]}, displayed pattern" if i == 0 else None)
            if gs_["n"] > 2:
                ax.errorbar(x, gs_["correct_mean"], yerr=gs_["correct_sd"], color="k", lw=0.6, capsize=1.5, zorder=3)
            ax.plot([x - 0.17, x + 0.17], [gs_["disc_mean"]] * 2, color="0.55", lw=1.1, zorder=4, label="open disc" if (i == 0 and k == 0) else None)
            ax.plot([x - 0.17, x + 0.17], [gs_["other_mean"]] * 2, color="k", lw=1.1, zorder=4, label="other ten patterns" if (i == 0 and k == 0) else None)
            ax.text(x, 0.505, f"{gs_['n']}", ha="center", fontsize=4.8, color="w", zorder=5)
    ax.set_xticks(range(len(GROUPS))); ax.set_xticklabels([n for _, n in GROUPS], fontsize=5.4)
    ax.set_ylim(0.5, 1.14); ax.set_yticks([0.5, 0.6, 0.7, 0.8, 0.9, 1.0]); ax.set_ylabel("NCC"); ax.grid(axis="y", alpha=0.25, lw=0.4, zorder=0)
    ax.legend(fontsize=5.2, frameon=False, loc="upper right", handletextpad=0.3, borderpad=0.1, ncol=1)


def results_fig(S, crops, light, out):
    fig = plt.figure(figsize=(FIG_W, FIG_H))
    gs = fig.add_gridspec(len(ROWS), 3, left=0.075, right=0.375, top=0.90, bottom=0.01, wspace=0.03, hspace=0.04)
    for r, p in enumerate(ROWS):
        ax = fig.add_subplot(gs[r, 0]); ax.imshow(displayed(p, "outside"), cmap="gray", interpolation="nearest"); ax.set_xticks([]); ax.set_yticks([])
        ax.set_ylabel(SHORT[p], fontsize=6, rotation=0, ha="right", va="center", labelpad=2)
        for sp in ax.spines.values(): sp.set_linewidth(0.4)
        for c, st in ((1, "outside"), (2, "inside")):
            ax = fig.add_subplot(gs[r, c]); ax.imshow(crops[(st, p, light[st])]); ax.set_xticks([]); ax.set_yticks([])
            for sp in ax.spines.values(): sp.set_linewidth(0.4)
    for c, t in enumerate(("displayed", "LCD in front", "LCD in tube")):
        fig.text(0.075 + (0.30 / 3) * (c + 0.5), 0.93, t, ha="center", fontsize=6.2)
    fig.text(0.005, 0.985, "(a)", fontsize=7, va="top")
    angle_panel(fig.add_axes(PANEL_B), S)
    fig.text(LABEL_B, 0.985, "(b)", fontsize=7, va="top")
    group_panel(fig.add_axes(PANEL_C), S)
    fig.text(LABEL_C, 0.985, "(c)", fontsize=7, va="top")
    fig.savefig(out / "bokeh_results.png", dpi=400, facecolor="white")
    plt.close(fig)


def ncc_fig(S, out):
    """panels (b) and (c) of the results figure on their own, as (a) and (b), at the same size"""
    x0 = LABEL_B - 0.005
    w = 1 - x0
    fig = plt.figure(figsize=(FIG_W * w, FIG_H))

    def shifted(box):
        return [(box[0] - x0) / w, box[1], box[2] / w, box[3]]

    angle_panel(fig.add_axes(shifted(PANEL_B)), S)
    fig.text((LABEL_B - x0) / w, 0.985, "(a)", fontsize=7, va="top")
    group_panel(fig.add_axes(shifted(PANEL_C)), S)
    fig.text((LABEL_C - x0) / w, 0.985, "(b)", fontsize=7, va="top")
    fig.savefig(out / "bokeh_ncc.png", dpi=400, facecolor="white")
    plt.close(fig)


# ------------------------------------------------------------------ appendix montage
def appendix_fig(S, crops, light, out):
    pats = list(SHORT)
    fig, axes = plt.subplots(len(pats), 3, figsize=(FIG_W, 0.62 * len(pats) + 0.15),
                             gridspec_kw=dict(wspace=0.02, hspace=0.03, left=0.095, right=0.995, top=0.975, bottom=0.005))
    for r, p in enumerate(pats):
        axes[r, 0].imshow(displayed(p, "outside"), cmap="gray", interpolation="nearest")
        axes[r, 0].set_ylabel(SHORT[p], fontsize=6.2, rotation=0, ha="right", va="center", labelpad=2)
        for c, st in ((1, "outside"), (2, "inside")):
            axes[r, c].imshow(crops[(st, p, light[st])])
        for c in range(3):
            axes[r, c].set_xticks([]); axes[r, c].set_yticks([])
            for sp in axes[r, c].spines.values(): sp.set_linewidth(0.4)
    for c, t in enumerate(("displayed, clipped to the iris", f"LCD in front of the lens, light {light['outside']}", f"LCD in the extension tube, light {light['inside']}")):
        axes[0, c].set_title(t, fontsize=6.2, pad=2)
    fig.savefig(out / "bokeh_montage.png", dpi=300, facecolor="white")
    plt.close(fig)


def main():
    a = parse_args(__doc__, captures=True)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    S = json.load(open(out / "bokeh_summary.json"))
    Y = dict(np.load(out / "Y_all.npz"))
    pats = list(SHORT)
    light_rows = {st: best_light(S, Y, st, ROWS) for st in STAGES}
    light_all = {st: best_light(S, Y, st, pats) for st in STAGES}
    wanted = {(st, p, light_rows[st]) for st in STAGES for p in ROWS} | {(st, p, light_all[st]) for st in STAGES for p in pats}
    crops = colour_crops(S, Path(a.captures), wanted)
    principle(out)
    results_fig(S, crops, light_rows, out)
    ncc_fig(S, out)
    appendix_fig(S, crops, light_all, out)
    print("figures written to", out, "| lights shown: results", light_rows, "montage", light_all)


if __name__ == "__main__":
    main()
