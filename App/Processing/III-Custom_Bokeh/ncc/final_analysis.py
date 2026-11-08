"""Score every light in every bokeh photo against the displayed pattern. Every number quoted in the
report comes from this script.

Inclusion is decided from the frames, never from the template match. A light is scored in a frame
when its window lies inside the frame and inside the polygon of roi_polygons.json, its core is at
least 1.5 times brighter than the ring just outside it in that frame, and its seed diameter is
within 1.3 times the median seed of the panel position. Wider seeds are two lights merged.

Each scored light and frame gets the best NCC of the displayed pattern over a sweep of template
sizes, then the same for an open disc and for each of the other ten patterns. The orientation of
the templates is chosen once per panel position. The 95 % intervals are a bootstrap over lights
with a fixed seed, so every run gives the same numbers.

Reads Y_all.npz from the out folder and writes there:
  bokeh_summary.json    the headline numbers, the lights kept, the per-pattern and per-group
                        statistics, the field angle fit, the similarity structure and the flux check
  bokeh_ncc_table.csv   one row per scored light and frame

Run from this folder:
  python3 final_analysis.py
  python3 final_analysis.py --out ../../../../Out/Custom_Bokeh/ncc
"""
import csv
import itertools
import json
import warnings
from pathlib import Path

import cv2
import numpy as np
from scipy.stats import pearsonr, spearmanr

from bokeh_ncc import (FOCAL_MM, HALF, HERE, P, PATTERNS, SENSOR_PITCH_MM, STAGE_MM, STAGES, best_ncc, parse_args,
                       pattern_mask, template, transforms)

BLUR = 0.15                          # template softening, as a fraction of the template size
SCALES = np.linspace(0.8, 1.6, 17)   # template sizes swept, as multiples of the seed diameter
RNG = np.random.default_rng(0)       # the bootstrap draws come from this stream, in a fixed order
SPRITES = [p for p in PATTERNS if p.startswith(("mario", "knight", "link"))]
CODED = [p for p in PATTERNS if p not in SPRITES]
GROUPS = {"mario": [p for p in PATTERNS if p.startswith("mario")], "knight": [p for p in PATTERNS if p.startswith("knight")],
          "link": [p for p in PATTERNS if p.startswith("link")], "zhou": ["zhou_a", "zhou_b"], "nayar_levin": ["nayar", "levin"]}


def window(y, cx, cy, d0):
    """the square about a light, lightly smoothed; None when it runs off the frame"""
    half = int(0.98 * d0)
    H, W = y.shape
    if cx - half < 0 or cy - half < 0 or cx + half > W or cy + half > H:
        return None
    return cv2.GaussianBlur(y[cy - half:cy + half, cx - half:cx + half].astype(np.float32), (0, 0), 0.012 * d0)


def window_in_roi(poly_1800, shape, cx, cy, d0):
    """the whole window must lie above the cake, inside the position's polygon (in coordinates of an
    1800 px wide frame)"""
    H, W = shape
    k = W / 1800.0
    poly = (np.array(poly_1800) * k).astype(np.float32).reshape(-1, 1, 2)
    half = int(0.98 * d0)
    pts = [(cx + sx * half, cy + sy * half) for sx in (-1, 0, 1) for sy in (-1, 0, 1) if (sx, sy) != (0, 0)]
    return all(cv2.pointPolygonTest(poly, (float(x), float(y)), False) >= 0 for x, y in pts)


def contrast(y, cx, cy, r):
    """the core of the light over the ring just outside it"""
    yy, xx = np.indices(y.shape)
    rad = np.hypot(xx - cx, yy - cy)
    return float(y[rad < 0.6 * r].mean() / y[(rad > 1.15 * r) & (rad < 1.6 * r)].mean())


def field_angle(stage, shape, cx, cy):
    H, W = shape
    rr = np.hypot(cx - W / 2, cy - H / 2) * HALF * SENSOR_PITCH_MM
    return float(np.degrees(np.arctan(rr / FOCAL_MM[stage])))


def boot_ci(per_light, stat=np.mean, n=4000):
    """cluster bootstrap over lights: resample lights, recompute the statistic"""
    a = np.asarray(per_light, float)
    if len(a) < 2:
        return (float("nan"), float("nan"))
    s = [stat(a[RNG.integers(0, len(a), len(a))]) for _ in range(n)]
    return (float(np.percentile(s, 2.5)), float(np.percentile(s, 97.5)))


def main():
    a = parse_args(__doc__)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    Y = np.load(out / "Y_all.npz")
    SEEDS = json.load(open(HERE / "seeds_auto.json"))
    POLY = json.load(open(HERE / "roi_polygons.json"))
    T = transforms()

    summary = {}
    table_rows = []
    for stage in STAGES:
        D = STAGE_MM[stage]
        shape = Y[f"{stage}|zhou_a"].shape
        masks = {p: pattern_mask(p, D) for p in PATTERNS + ["disc"]}
        seeds = SEEDS[stage]
        med_d = np.median([2 * r for _, _, r in seeds])
        entries = []   # (light id, pattern, window)
        lights = {}
        for i, (cx, cy, r) in enumerate(seeds):
            d0 = int(2.0 * r)
            if d0 > 1.3 * med_d or window(Y[f"{stage}|zhou_a"], cx, cy, d0) is None or not window_in_roi(POLY[stage], shape, cx, cy, d0):
                continue
            lights[i] = dict(id=i, cx=cx, cy=cy, r=r, d0=d0, theta=field_angle(stage, shape, cx, cy))
            for p in PATTERNS:
                y = Y[f"{stage}|{p}"]
                if contrast(y, cx, cy, r) >= 1.5:
                    entries.append((i, p, window(y, cx, cy, d0)))
        print(stage, "lights kept:", sorted(lights), "scored light-frames:", len(entries), "of", len(lights) * len(PATTERNS), flush=True)

        # orientation, chosen once per panel position over every scored light and frame
        tot = {t: [] for t in T}
        for i, p, w in entries:
            for tn, f in T.items():
                tot[tn].append(best_ncc(w, f(masks[p]), lights[i]["d0"], SCALES, BLUR)[0])
        omean = {t: float(np.mean(v)) for t, v in tot.items()}
        g = max(omean, key=omean.get)

        rows = []
        for i, p, w in entries:
            l = lights[i]
            sc = {q: best_ncc(w, T[g](masks[q]), l["d0"], SCALES, BLUR)[0] for q in PATTERNS + ["disc"]}
            no_disc = {q: v for q, v in sc.items() if q != "disc"}
            others = [v for q, v in no_disc.items() if q != p]
            row = dict(stage=stage, light=i, image=p, theta=l["theta"], correct=sc[p], disc=sc["disc"],
                       other_mean=float(np.mean(others)), top1=bool(max(no_disc, key=no_disc.get) == p),
                       top1_char=bool(max(no_disc, key=no_disc.get).split("_")[0] == p.split("_")[0]))
            rows.append(row)
            table_rows.append(row)

        def arr(key, sel=lambda r: True):
            return np.array([r[key] for r in rows if sel(r)], float)

        ids = sorted({r["light"] for r in rows})
        per_light = {k: [np.mean([r[k] for r in rows if r["light"] == i]) for i in ids] for k in ("correct", "disc", "other_mean")}
        per_light["delta"] = [c - d for c, d in zip(per_light["correct"], per_light["disc"])]
        per_light["delta_other"] = [c - o for c, o in zip(per_light["correct"], per_light["other_mean"])]
        per_light["other_minus_disc"] = [o - d for o, d in zip(per_light["other_mean"], per_light["disc"])]
        per_light["theta"] = [lights[i]["theta"] for i in ids]
        pattern_stats = {}
        for p in PATTERNS:
            c, d = arr("correct", lambda r: r["image"] == p), arr("disc", lambda r: r["image"] == p)
            pattern_stats[p] = dict(n=int(len(c)), correct_mean=float(c.mean()) if len(c) else None,
                                    correct_sd=float(c.std(ddof=1)) if len(c) > 1 else None,
                                    disc_mean=float(d.mean()) if len(d) else None)
        group_stats = {}
        for name, ps in GROUPS.items():
            sel = lambda r, ps=ps: r["image"] in ps
            c, d = arr("correct", sel), arr("disc", sel)
            o_ = arr("other_mean", sel)
            group_stats[name] = dict(n=int(len(c)), other_mean=float(o_.mean()), correct_mean=float(c.mean()), correct_sd=float(c.std(ddof=1)),
                                     disc_mean=float(d.mean()), disc_sd=float(d.std(ddof=1)))

        # NCC against field angle (per-light means, so lights are the replicates)
        th = np.array(per_light["theta"]); cm = np.array(per_light["correct"])
        slope, icpt = np.polyfit(th, cm, 1)
        r_th, p_th = pearsonr(th, cm)

        # similarity structure: blob-to-blob NCC against template-to-template NCC, orientation free
        pairs = list(itertools.combinations(PATTERNS, 2))

        def tsim(a, b, size=120):
            ta, tb = template(masks[a], size, BLUR), template(masks[b], size, BLUR)
            pad = int(0.1 * size)
            return float(cv2.matchTemplate(cv2.copyMakeBorder(ta, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=0), tb, cv2.TM_CCOEFF_NORMED).max())

        pred = np.array([tsim(a, b) for a, b in pairs])
        per_light_meas = []
        for i in ids:
            ws = {}
            for p in PATTERNS:
                w = window(Y[f"{stage}|{p}"], lights[i]["cx"], lights[i]["cy"], lights[i]["d0"])
                if w is not None and contrast(Y[f"{stage}|{p}"], lights[i]["cx"], lights[i]["cy"], lights[i]["r"]) >= 1.5:
                    ws[p] = w
            m = np.full(len(pairs), np.nan)
            for k, (a_, b_) in enumerate(pairs):
                if a_ in ws and b_ in ws:
                    mg = int(0.18 * lights[i]["d0"])
                    m[k] = float(cv2.matchTemplate(ws[a_], ws[b_][mg:-mg, mg:-mg], cv2.TM_CCOEFF_NORMED).max())
            per_light_meas.append(m)
        PLM = np.array(per_light_meas)
        cnt = np.isfinite(PLM).sum(axis=0)
        with np.errstate(all="ignore"), warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)      # a pair no light shows in both frames is all NaN
            meas = np.nanmean(PLM, axis=0)
        valid = cnt >= 2
        meas[~valid] = np.nan

        def spear(idx, vec):
            idx = [k for k in idx if np.isfinite(vec[k])]
            return (float(spearmanr(vec[idx], pred[idx])[0]) if len(idx) > 3 else float("nan")), len(idx)

        all_idx = list(range(len(pairs)))
        sprite_idx = [k for k, (a_, b_) in enumerate(pairs) if a_ in SPRITES and b_ in SPRITES]
        cross_idx = [k for k, (a_, b_) in enumerate(pairs) if (a_ in SPRITES) != (b_ in SPRITES)]
        coded_idx = [k for k, (a_, b_) in enumerate(pairs) if a_ in CODED and b_ in CODED]
        rho_all, n_all = spear(all_idx, meas)
        rho_sprite, n_sprite = spear(sprite_idx, meas)
        rho_cross, n_cross = spear(cross_idx, meas)
        rho_coded, n_coded = spear(coded_idx, meas)
        rho_boot = []
        for _ in range(2000):
            pick = RNG.integers(0, len(PLM), len(PLM))
            with np.errstate(all="ignore"), warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                v = np.nanmean(PLM[pick], axis=0)
            v[np.isfinite(PLM[pick]).sum(axis=0) < 1] = np.nan
            rho_boot.append(spear(all_idx, v)[0])
        rho_boot = [r for r in rho_boot if np.isfinite(r)]
        rho_ci = (float(np.percentile(rho_boot, 2.5)), float(np.percentile(rho_boot, 97.5)))

        # flux in the light region against the open fraction of the iris
        H, W = shape
        k = W / 1800.0
        poly = (np.array(POLY[stage]) * k).astype(np.int32)
        roi = np.zeros((H, W), np.uint8); cv2.fillPoly(roi, [poly], 1); roi = roi.astype(bool)
        flux = {p: float(Y[f"{stage}|{p}"][roi].sum()) for p in PATTERNS}
        area = {p: float(masks[p].sum() / P.disc(D).sum()) for p in PATTERNS}

        def flux_fit(ps):
            a_ = np.array([area[p] for p in ps]); f = np.array([flux[p] for p in ps]); f = f / f.mean()
            r = pearsonr(a_, f)[0]; kk = (a_ * f).sum() / (a_ * a_).sum(); res = f - kk * a_
            r2 = 1 - (res ** 2).sum() / ((f - f.mean()) ** 2).sum()
            return dict(n=len(ps), pearson=float(r), through_origin_k=float(kk), r2_origin=float(r2))

        fluxes = dict(all=flux_fit(PATTERNS), sprites=flux_fit(SPRITES), coded=flux_fit(CODED))

        summary[stage] = dict(
            orientation=g, orientation_means=omean, lights={str(i): lights[i] for i in ids}, n_scored=len(rows),
            n_possible=len(lights) * len(PATTERNS), n_lights=len(ids),
            correct_mean=float(arr("correct").mean()), correct_sd=float(arr("correct").std(ddof=1)),
            disc_mean=float(arr("disc").mean()), disc_sd=float(arr("disc").std(ddof=1)),
            other_mean=float(arr("other_mean").mean()),
            delta_mean=float((arr("correct") - arr("disc")).mean()), delta_ci_lights=boot_ci(per_light["delta"]),
            frac_correct_gt_disc=float(np.mean(arr("correct") > arr("disc"))),
            delta_other_mean=float((arr("correct") - arr("other_mean")).mean()), delta_other_ci_lights=boot_ci(per_light["delta_other"]),
            frac_correct_gt_other=float(np.mean(arr("correct") > arr("other_mean"))),
            other_minus_disc_mean=float((arr("other_mean") - arr("disc")).mean()), other_minus_disc_ci_lights=boot_ci(per_light["other_minus_disc"]),
            top1=float(np.mean([r["top1"] for r in rows])), top1_char=float(np.mean([r["top1_char"] for r in rows])),
            per_light=per_light, angle_fit=dict(slope_per_deg=float(slope), intercept=float(icpt), r=float(r_th), p=float(p_th),
                                                theta_min=float(th.min()), theta_max=float(th.max())),
            plm=[[None if not np.isfinite(v) else float(v) for v in row] for row in PLM],
            pattern_stats=pattern_stats, group_stats=group_stats,
            similarity=dict(rho_all=rho_all, n_all=n_all, rho_ci=rho_ci, rho_sprite=rho_sprite, n_sprite=n_sprite,
                            rho_cross=rho_cross, n_cross=n_cross, rho_coded=rho_coded, n_coded=n_coded,
                            meas=meas.tolist(), pred=pred.tolist(), pairs=[list(p) for p in pairs]),
            flux=dict(fluxes=fluxes, area=area, flux=flux),
        )
        print(f"  {stage}: orientation {g}; NCC {summary[stage]['correct_mean']:.3f} +/- {summary[stage]['correct_sd']:.3f}, disc {summary[stage]['disc_mean']:.3f}, "
              f"delta {summary[stage]['delta_mean']:+.3f} CI {np.round(summary[stage]['delta_ci_lights'], 3).tolist()}, top1 {summary[stage]['top1']:.2f} (chance {1/11:.2f}), "
              f"rho {rho_all:.2f} CI {np.round(rho_ci, 2).tolist()} sprite-only {rho_sprite:.2f}, angle slope {slope:+.3f}/deg r={r_th:.2f}", flush=True)

    with open(out / "bokeh_summary.json", "w") as f:
        json.dump(summary, f, indent=1)
    with open(out / "bokeh_ncc_table.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(table_rows[0]))
        w.writeheader()
        w.writerows(table_rows)
    print("wrote", out / "bokeh_summary.json", "and", out / "bokeh_ncc_table.csv")


if __name__ == "__main__":
    main()
