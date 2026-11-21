"""Render 8 deterministic white/grey 3D architectural stills from data/layout_spec.json."""

from __future__ import annotations

import json
import math
import shutil
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np


ROOT_DIR = Path(__file__).resolve().parent.parent
SPEC_PATH = ROOT_DIR / "data" / "layout_spec.json"
OUT_GALLERY_DIR = ROOT_DIR / "outputs" / "gallery_stills"
WEB_GALLERY_DIR = ROOT_DIR / "web" / "src" / "assets" / "gallery"

# Fixed directional light vector (normalized) for studio diffuse shading
LIGHT_DIR = np.array([0.42, -0.38, 0.82])
LIGHT_DIR = LIGHT_DIR / np.linalg.norm(LIGHT_DIR)


def hex_to_rgb(h: str) -> np.ndarray:
    h = h.lstrip("#")
    return np.array([int(h[i : i + 2], 16) / 255.0 for i in (0, 2, 4)], dtype=float)


def shade_color(base_rgb: np.ndarray, normal: np.ndarray, alpha: float = 1.0) -> tuple[float, float, float, float]:
    n = normal / (np.linalg.norm(normal) + 1e-9)
    diff = max(0.0, float(np.dot(n, LIGHT_DIR)))
    intensity = 0.56 + 0.44 * diff
    rgb = np.clip(base_rgb * intensity, 0.0, 1.0)
    return (float(rgb[0]), float(rgb[1]), float(rgb[2]), alpha)


def add_box(
    polys: list[list[tuple[float, float, float]]],
    fcolors: list[tuple[float, float, float, float]],
    ecolors: list[tuple[float, float, float, float]],
    x1: float,
    y1: float,
    z1: float,
    x2: float,
    y2: float,
    z2: float,
    color_hex: str,
    edge_hex: str = "#64748B",
    alpha: float = 1.0,
) -> None:
    """Append 6 faces of an axis-aligned 3D box in architectural meters (Z up, Y flipped so -Y = North)."""
    # Convert mm -> m and flip Y so north (Y=0) is +Y in right-handed 3D view
    ax1, ax2 = min(x1, x2) / 1000.0, max(x1, x2) / 1000.0
    ay1, ay2 = -max(y1, y2) / 1000.0, -min(y1, y2) / 1000.0
    az1, az2 = z1 / 1000.0, z2 / 1000.0

    # Subdivide wide/long boxes into <= 1.2 m chunks so mplot3d painter's sort never occludes smaller equipment
    sx_len = ax2 - ax1
    sy_len = ay2 - ay1
    nx = max(1, int(math.ceil(sx_len / 1.2))) if (sx_len > 1.4 or sy_len > 1.4) else 1
    ny = max(1, int(math.ceil(sy_len / 1.2))) if (sx_len > 1.4 or sy_len > 1.4) else 1
    base_rgb = hex_to_rgb(color_hex)
    er = hex_to_rgb(edge_hex)
    edge_rgba = (float(er[0]), float(er[1]), float(er[2]), min(1.0, alpha * 0.45))
    dx = sx_len / nx
    dy = sy_len / ny

    for ix in range(nx):
        for iy in range(ny):
            bx1 = ax1 + ix * dx
            bx2 = bx1 + dx
            by1 = ay1 + iy * dy
            by2 = by1 + dy
            v = [
                (bx1, by1, az1), (bx2, by1, az1), (bx2, by2, az1), (bx1, by2, az1),
                (bx1, by1, az2), (bx2, by1, az2), (bx2, by2, az2), (bx1, by2, az2),
            ]
            faces = [([v[4], v[5], v[6], v[7]], np.array([0.0, 0.0, 1.0]))]
            if iy == 0:
                faces.append(([v[0], v[1], v[5], v[4]], np.array([0.0, -1.0, 0.0])))
            if iy == ny - 1:
                faces.append(([v[2], v[3], v[7], v[6]], np.array([0.0, 1.0, 0.0])))
            if ix == nx - 1:
                faces.append(([v[1], v[2], v[6], v[5]], np.array([1.0, 0.0, 0.0])))
            if ix == 0:
                faces.append(([v[3], v[0], v[4], v[7]], np.array([-1.0, 0.0, 0.0])))
            for verts, norm in faces:
                polys.append(verts)
                fcolors.append(shade_color(base_rgb, norm, alpha))
                ecolors.append(edge_rgba if (nx == 1 and ny == 1) else (edge_rgba[0], edge_rgba[1], edge_rgba[2], edge_rgba[3] * 0.35))


def split_wall_intervals(wall: dict[str, Any], doors: list[dict[str, Any]]) -> list[tuple[float, float, float, float]]:
    x1, y1, x2, y2 = float(wall["x1"]), float(wall["y1"]), float(wall["x2"]), float(wall["y2"])
    vertical = abs(x1 - x2) < 1e-6
    w_doors = [d for d in doors if d.get("wall_id") == wall["id"]]
    if not w_doors:
        return [(x1, y1, x2, y2)]
    if vertical:
        lo, hi = min(y1, y2), max(y1, y2)
        cuts = sorted((min(d["y1"], d["y2"]), max(d["y1"], d["y2"])) for d in w_doors)
        out, cur = [], lo
        for a, b in cuts:
            if a > cur + 1:
                out.append((x1, cur, x1, a))
            cur = max(cur, b)
        if cur < hi - 1:
            out.append((x1, cur, x1, hi))
        return out
    lo, hi = min(x1, x2), max(x1, x2)
    cuts = sorted((min(d["x1"], d["x2"]), max(d["x1"], d["x2"])) for d in w_doors)
    out, cur = [], lo
    for a, b in cuts:
        if a > cur + 1:
            out.append((cur, y1, a, y1))
        cur = max(cur, b)
    if cur < hi - 1:
        out.append((cur, y1, hi, y1))
    return out


def build_scene_geometry(spec: dict[str, Any]) -> tuple[list[Any], list[Any], list[Any]]:
    """Build all 3D architectural geometry once from layout_spec.json."""
    polys: list[Any] = []
    fcolors: list[Any] = []
    ecolors: list[Any] = []

    mb = spec["shell"]["main_building"]
    fe = spec["shell"]["front_extension"]
    ec = spec["shell"]["external_cold_storage"]

    # Base floor slabs (subtle grey epoxy)
    add_box(polys, fcolors, ecolors, mb["x"], mb["y"], -80, mb["x"] + mb["w"], mb["y"] + mb["h"], 0, "#CBD5E1", "#94A3B8")
    add_box(polys, fcolors, ecolors, fe["x"], fe["y"], -80, fe["x"] + fe["w"], fe["y"] + fe["h"], 0, "#CBD5E1", "#94A3B8")
    add_box(polys, fcolors, ecolors, ec["x"], ec["y"], -60, ec["x"] + ec["w"], ec["y"] + ec["h"], 2600, "#E2E8F0", "#64748B")

    # Floor striping zones
    for zn in spec["zones"]:
        zcol = "#94A3B8" if zn["id"] == "Z-SORTING" else "#B8C4D4"
        add_box(polys, fcolors, ecolors, zn["x"], zn["y"], 2, zn["x"] + zn["w"], zn["y"] + zn["h"], 10, zcol, "#475569")

    # Walls (cutaway height 2,400 mm for clear executive view; glazed partition translucent)
    cut_h = 2350.0
    for wall in spec["walls"]:
        if wall["kind"] == "external_enclosure":
            continue
        t = float(wall["thickness_mm"])
        half = t / 2.0
        is_glass = wall["kind"] == "glazed_partition"
        col = "#E2E8F0" if is_glass else "#F8FAFC"
        alpha = 0.45 if is_glass else 0.94
        wh = min(cut_h, float(wall["height_mm"]))
        for sx1, sy1, sx2, sy2 in split_wall_intervals(wall, spec["doors"]):
            if abs(sx1 - sx2) < 1e-3:
                add_box(polys, fcolors, ecolors, sx1 - half, min(sy1, sy2), 0, sx1 + half, max(sy1, sy2), wh, col, "#94A3B8", alpha)
            else:
                add_box(polys, fcolors, ecolors, min(sx1, sx2), sy1 - half, 0, max(sx1, sx2), sy1 + half, wh, col, "#94A3B8", alpha)

    # Door leaves (open 90 degrees per swing_dir)
    for d in spec["doors"]:
        if not d.get("hinge") or d["swing_dir"] == "open_passage":
            continue
        hx, hy = float(d["hinge"][0]), float(d["hinge"][1])
        w = float(d["width_mm"])
        dh = min(cut_h - 150, float(d["height_mm"]))
        sd = d["swing_dir"]
        if sd == "+X":
            add_box(polys, fcolors, ecolors, hx, hy - 25, 0, hx + w, hy + 25, dh, "#E2E8F0", "#334155")
        elif sd == "-X":
            add_box(polys, fcolors, ecolors, hx - w, hy - 25, 0, hx, hy + 25, dh, "#E2E8F0", "#334155")
        elif sd == "+Y":
            add_box(polys, fcolors, ecolors, hx - 25, hy, 0, hx + 25, hy + w, dh, "#E2E8F0", "#334155")
        elif sd == "-Y":
            add_box(polys, fcolors, ecolors, hx - 25, hy - w, 0, hx + 25, hy, dh, "#E2E8F0", "#334155")

    # Conveyors (stainless frame + rollers + trays)
    for conv in spec["conveyors"]:
        cx, cy, cw, ch = float(conv["x"]), float(conv["y"]), float(conv["w"]), float(conv["h"])
        for deck_idx, deck in enumerate(conv["decks"]):
            z = float(deck["z_mm"])
            add_box(polys, fcolors, ecolors, cx, cy, z - 80, cx + cw, cy + ch, z, "#9CA3AF", "#475569")
            # Sample trays spaced along deck
            tray_col = "#CBD5E1" if deck["stream"] == "soils_dry" else ("#94A3B8" if deck["stream"] == "soils_wet" else "#E2E8F0")
            for ty in range(int(cy + 600), int(cy + ch - 700), 1700):
                add_box(polys, fcolors, ecolors, cx + 110, ty + deck_idx * 450, z, cx + cw - 110, ty + deck_idx * 450 + 420, z + 110, tray_col, "#334155")

    # Stations & Equipment
    for it in spec["stations_and_equipment"]:
        x, y, w, h = float(it["x"]), float(it["y"]), float(it["w"]), float(it["h"])
        z0 = float(it["elev_mm"])
        z1 = z0 + float(it["height_mm"])
        cat = it["category"]

        if cat in ("bench", "island_bench", "waters_station", "soils_station", "logistics_station", "sulphide_scan_pc", "office_desk", "dining_table", "kitchenette", "wash_alcove"):
            # Under-bench white steel cabinet + warm grey worktop
            if z1 - z0 > 120:
                add_box(polys, fcolors, ecolors, x + 20, y + 20, z0, x + w - 20, y + h - 20, z1 - 45, "#F1F5F9", "#94A3B8")
            add_box(polys, fcolors, ecolors, x, y, z1 - 45, x + w, y + h, z1, "#D6D9DF", "#475569")
        elif cat in ("fume_hood", "benchtop_fume_hood"):
            # Lower plinth + frosted glass sash box
            add_box(polys, fcolors, ecolors, x, y, z0, x + w, y + h, z0 + 180, "#E2E8F0", "#334155")
            add_box(polys, fcolors, ecolors, x + 15, y + 15, z0 + 180, x + w - 15, y + h - 15, z1, "#E2E8F0", "#334155", alpha=0.58)
            add_box(polys, fcolors, ecolors, x, y, z1 - 90, x + w, y + h, z1, "#CBD5E1", "#334155")
        elif cat in ("drying_oven", "grinder", "fridge"):
            add_box(polys, fcolors, ecolors, x, y, z0, x + w, y + h, z1, "#D6D9DF", "#334155")
        elif cat == "storage_rack":
            tiers = int(it.get("tiers", 5))
            step = (z1 - 150) / max(1, tiers - 1)
            for t_idx in range(tiers):
                sz = 120 + t_idx * step
                add_box(polys, fcolors, ecolors, x, y, sz, x + w, y + h, sz + 40, "#CBD5E1", "#475569")
        elif cat == "wc_cubicle":
            add_box(polys, fcolors, ecolors, x, y, z0, x + w, y + h, z1, "#F8FAFC", "#64748B", alpha=0.88)
        elif cat in ("shaker", "sink", "toc_station", "sulphide_pc"):
            col = "#9CA3AF" if cat == "sink" else "#CBD5E1"
            add_box(polys, fcolors, ecolors, x + 30, y + 30, z0, x + w - 30, y + h - 30, z0 + 220, col, "#475569")

        # Monitors & Label Printers
        if it["has_pc"]:
            cx, cy = x + w / 2.0, y + h / 2.0
            if it["dual_monitor"]:
                add_box(polys, fcolors, ecolors, cx - 540, cy - 80, z1 + 120, cx - 40, cy - 30, z1 + 440, "#334155", "#0F172A")
                add_box(polys, fcolors, ecolors, cx + 40, cy - 80, z1 + 120, cx + 540, cy - 30, z1 + 440, "#334155", "#0F172A")
            else:
                mw, mh = (60, 420) if h > w and cat == "waters_station" else (420, 60)
                add_box(polys, fcolors, ecolors, cx - mw / 2, cy - mh / 2, z1 + 100, cx + mw / 2, cy + mh / 2, z1 + 400, "#334155", "#0F172A")
        if it["has_label_printer"]:
            add_box(polys, fcolors, ecolors, x + 90, y + 90, z1, x + 280, y + 290, z1 + 180, "#94A3B8", "#334155")

        # Ergonomic Charcoal Chair
        if it.get("seat"):
            sx, sy = float(it["seat"]["x"]), float(it["seat"]["y"])
            add_box(polys, fcolors, ecolors, sx - 190, sy - 190, 420, sx + 190, sy + 190, 480, "#334155", "#0F172A")
            add_box(polys, fcolors, ecolors, sx - 90, sy - 90, 0, sx + 90, sy + 90, 420, "#64748B", "#334155")

    return polys, fcolors, ecolors


def render_all_stills() -> None:
    OUT_GALLERY_DIR.mkdir(parents=True, exist_ok=True)
    WEB_GALLERY_DIR.mkdir(parents=True, exist_ok=True)

    with SPEC_PATH.open("r", encoding="utf-8") as f:
        spec = json.load(f)

    polys, fcolors, ecolors = build_scene_geometry(spec)

    for ch in spec["tour_chapters"]:
        cid = int(ch["id"])
        cam = np.array(ch["camera_mm"], dtype=float) / 1000.0
        tgt = np.array(ch["target_mm"], dtype=float) / 1000.0
        # Flip Y to match add_box right-handed axes
        cam_3d = np.array([cam[0], -cam[1], cam[2]])
        tgt_3d = np.array([tgt[0], -tgt[1], tgt[2]])

        vec = cam_3d - tgt_3d
        horiz = max(0.5, math.hypot(vec[0], vec[1]))
        elev = max(16.0, min(42.0, math.degrees(math.atan2(vec[2], horiz)) + 10.0))
        azim = math.degrees(math.atan2(vec[1], vec[0]))

        fig = plt.figure(figsize=(16, 9), dpi=100, facecolor="#F8FAFC")
        ax = fig.add_axes([-0.14, 0.04, 1.28, 1.02], projection="3d", facecolor="#F8FAFC")
        ax.set_proj_type("persp", focal_length=0.52)
        ax.view_init(elev=elev, azim=azim)
        ax.set_axis_off()
        ax.dist = 7.2

        # Filter polygons near camera target region so full building fill doesn't waste margins
        half_span = 4.9 if cid in (1, 2, 3, 4, 7, 8) else 4.0
        cx, cy = tgt_3d[0], tgt_3d[1]
        keep_p, keep_fc, keep_ec = [], [], []
        pad = half_span + 2.4
        for p, fc, ec in zip(polys, fcolors, ecolors):
            px = sum(v[0] for v in p) / len(p)
            py = sum(v[1] for v in p) / len(p)
            if abs(px - cx) <= pad and abs(py - cy) <= pad:
                keep_p.append(p)
                keep_fc.append(fc)
                keep_ec.append(ec)

        col = Poly3DCollection(keep_p, facecolors=keep_fc, edgecolors=keep_ec, linewidths=0.32)
        ax.add_collection3d(col)

        ax.set_xlim(cx - half_span, cx + half_span)
        ax.set_ylim(cy - half_span, cy + half_span)
        ax.set_zlim(0.0, 3.4)
        ax.set_box_aspect((1.0, 1.0, 0.34))

        # Executive lower caption bar
        ax_bar = fig.add_axes([0.0, 0.0, 1.0, 0.085], facecolor="#0F172A")
        ax_bar.set_xticks([])
        ax_bar.set_yticks([])
        for sp in ax_bar.spines.values():
            sp.set_visible(False)
        ax_bar.text(
            0.025,
            0.62,
            f"VIEW 0{cid}  |  {ch['title'].upper()}",
            color="#FFFFFF",
            fontsize=13,
            fontweight="bold",
            va="center",
        )
        ax_bar.text(
            0.025,
            0.25,
            f"{ch['subtitle']}  •  SomeLab SomewhereintheUK Consolidated Prep Facility (Project Vol)",
            color="#CBD5E1",
            fontsize=9.5,
            va="center",
        )
        ax_bar.text(
            0.975,
            0.44,
            "Strict White & Grey Architectural Concept",
            color="#94A3B8",
            fontsize=9.0,
            ha="right",
            va="center",
        )

        fname = f"view_{cid:02d}.png"
        out_path = OUT_GALLERY_DIR / fname
        fig.savefig(out_path, dpi=100, facecolor="#F8FAFC")
        plt.close(fig)
        shutil.copy2(out_path, WEB_GALLERY_DIR / fname)
        print(f"Rendered 3D still: {out_path} ({out_path.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    render_all_stills()
