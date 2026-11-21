"""Generate Project Vol 2D Architectural Plans (SVG, PNG, PDF) and 3-Tab Excel Equipment Schedule (.xlsx)."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import patches
from matplotlib.lines import Line2D
import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter


ROOT_DIR = Path(__file__).resolve().parent.parent
SPEC_PATH = ROOT_DIR / "data" / "layout_spec.json"
OUT_DIR = ROOT_DIR / "outputs"


def load_spec() -> dict[str, Any]:
    with SPEC_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def split_wall_around_doors(wall: dict[str, Any], doors: list[dict[str, Any]]) -> list[tuple[float, float, float, float]]:
    """Split a wall centerline segment by any door openings referencing this wall."""
    x1, y1, x2, y2 = float(wall["x1"]), float(wall["y1"]), float(wall["x2"]), float(wall["y2"])
    vertical = abs(x1 - x2) < 1e-6
    wall_doors = [d for d in doors if d.get("wall_id") == wall["id"]]
    if not wall_doors:
        return [(x1, y1, x2, y2)]

    if vertical:
        lo, hi = min(y1, y2), max(y1, y2)
        cuts = sorted((min(d["y1"], d["y2"]), max(d["y1"], d["y2"])) for d in wall_doors)
        segs: list[tuple[float, float, float, float]] = []
        cur = lo
        for a, b in cuts:
            if a > cur + 1e-3:
                segs.append((x1, cur, x1, a))
            cur = max(cur, b)
        if cur < hi - 1e-3:
            segs.append((x1, cur, x1, hi))
        return segs

    lo, hi = min(x1, x2), max(x1, x2)
    cuts = sorted((min(d["x1"], d["x2"]), max(d["x1"], d["x2"])) for d in wall_doors)
    segs = []
    cur = lo
    for a, b in cuts:
        if a > cur + 1e-3:
            segs.append((cur, y1, a, y1))
        cur = max(cur, b)
    if cur < hi - 1e-3:
        segs.append((cur, y1, hi, y1))
    return segs


def draw_door_symbol(ax: plt.Axes, door: dict[str, Any]) -> None:
    """Draw accurate 90-degree hinged door leaf and dashed swing arc."""
    if not door.get("hinge") or door["swing_dir"] == "open_passage":
        return
    hx, hy = float(door["hinge"][0]), float(door["hinge"][1])
    x1, y1, x2, y2 = float(door["x1"]), float(door["y1"]), float(door["x2"]), float(door["y2"])
    w = float(door["width_mm"])
    sdir = door["swing_dir"]

    # Closed latch tip
    lx = x2 if abs(hx - x1) < 1e-3 else x1
    ly = y2 if abs(hy - y1) < 1e-3 else y1
    if abs(hx - x1) < 1e-3 and abs(hy - y1) < 1e-3:
        lx, ly = x2, y2

    closed_deg = math.degrees(math.atan2(ly - hy, lx - hx))
    open_vecs = {"+X": (w, 0.0), "-X": (-w, 0.0), "+Y": (0.0, w), "-Y": (0.0, -w)}
    open_degs = {"+X": 0.0, "-X": 180.0, "+Y": 90.0, "-Y": -90.0}
    ox, oy = open_vecs[sdir]
    open_deg = open_degs[sdir]

    # Door leaf (thin solid dark charcoal line)
    ax.plot([hx, hx + ox], [hy, hy + oy], color="#1E293B", linewidth=1.35, zorder=15)

    # Quarter-circle arc in data coordinates (note Y axis inverted later, so atan2 angles in data space match Arc theta!)
    delta = (open_deg - closed_deg + 180.0) % 360.0 - 180.0
    t1, t2 = (closed_deg, closed_deg + delta) if delta >= 0 else (closed_deg + delta, closed_deg)
    arc = patches.Arc(
        (hx, hy),
        width=2.0 * w,
        height=2.0 * w,
        angle=0.0,
        theta1=t1,
        theta2=t2,
        edgecolor="#64748B",
        linewidth=0.85,
        linestyle="--",
        zorder=14,
    )
    ax.add_patch(arc)


def draw_chair_symbol(ax: plt.Axes, seat: dict[str, Any]) -> None:
    """Draw a minimal monochrome ergonomic chair oriented toward its desk."""
    cx, cy = float(seat["x"]), float(seat["y"])
    r = 195.0
    circ = patches.Circle((cx, cy), r, facecolor="#E2E8F0", edgecolor="#334155", linewidth=0.9, zorder=12)
    ax.add_patch(circ)
    # Backrest sits on the opposite side of facing direction
    facing = seat["facing"]
    back_angles = {"+X": (125, 235), "-X": (-55, 55), "+Y": (-145, -35), "-Y": (35, 145)}
    t1, t2 = back_angles[facing]
    back = patches.Arc((cx, cy), width=2.25 * r, height=2.25 * r, theta1=t1, theta2=t2, edgecolor="#0F172A", linewidth=2.0, zorder=13)
    ax.add_patch(back)


def draw_dimension_line(ax: plt.Axes, x1: float, y1: float, x2: float, y2: float, label: str, offset_text: tuple[float, float] = (0, 0), fontsize: float = 6.5, vertical: bool = False) -> None:
    """Draw architectural dimension bar with end ticks and centered label."""
    ax.annotate(
        "",
        xy=(x1, y1),
        xytext=(x2, y2),
        arrowprops=dict(arrowstyle="<->", color="#334155", lw=0.85, shrinkA=0, shrinkB=0),
        zorder=20,
    )
    # Extension ticks
    tick = 140.0
    if abs(y1 - y2) < 1e-3:
        ax.plot([x1, x1], [y1 - tick, y1 + tick], color="#334155", lw=0.75, zorder=20)
        ax.plot([x2, x2], [y2 - tick, y2 + tick], color="#334155", lw=0.75, zorder=20)
    else:
        ax.plot([x1 - tick, x1 + tick], [y1, y1], color="#334155", lw=0.75, zorder=20)
        ax.plot([x2 - tick, x2 + tick], [y2, y2], color="#334155", lw=0.75, zorder=20)
    mx, my = (x1 + x2) / 2.0 + offset_text[0], (y1 + y2) / 2.0 + offset_text[1]
    ax.text(
        mx,
        my,
        label,
        ha="center",
        va="center",
        rotation=90 if vertical else 0,
        fontsize=fontsize,
        fontweight="bold",
        color="#0F172A",
        bbox=dict(boxstyle="round,pad=0.18", facecolor="#FFFFFF", edgecolor="none", alpha=0.92),
        zorder=21,
    )


def generate_2d_plans(spec: dict[str, Any]) -> None:
    """Render monochrome white/grey/charcoal 2D floor plan in SVG, PNG (300 DPI), and PDF."""
    fig = plt.figure(figsize=(22, 16), dpi=300, facecolor="#FFFFFF")
    # Main drawing axes + top title banner + right sidebar legend
    ax = fig.add_axes([0.025, 0.04, 0.725, 0.87], facecolor="#FFFFFF")
    ax_title = fig.add_axes([0.025, 0.92, 0.95, 0.062], facecolor="#0F172A")
    ax_leg = fig.add_axes([0.765, 0.04, 0.21, 0.87], facecolor="#F8FAFC")

    # Top Title Block
    ax_title.set_xticks([])
    ax_title.set_yticks([])
    for sp in ax_title.spines.values():
        sp.set_visible(False)
    ax_title.text(
        0.015,
        0.64,
        f"{spec['meta']['project_name'].upper()} — {spec['meta']['facility_title'].upper()}",
        color="#FFFFFF",
        fontsize=15.5,
        fontweight="bold",
        va="center",
        ha="left",
    )
    ax_title.text(
        0.015,
        0.24,
        f"{spec['meta']['address']}  •  Architectural General Arrangement Plan (Single Source of Truth)  •  1 Grid = 1,000 mm",
        color="#CBD5E1",
        fontsize=9.2,
        va="center",
        ha="left",
    )
    ax_title.text(
        0.985,
        0.64,
        "SCALE 1:100  |  ALL DIMENSIONS IN mm",
        color="#FFFFFF",
        fontsize=11.0,
        fontweight="bold",
        va="center",
        ha="right",
    )
    ax_title.text(
        0.985,
        0.24,
        "Waters (10)  •  Soils 3x5 (15) + 2 Double Rollers  •  Sulphide (8+1 PCs)  •  CS Office (8 Dual-Screen)",
        color="#94A3B8",
        fontsize=8.2,
        va="center",
        ha="right",
    )

    # Coordinate extents & 1,000 mm subtle grid
    ax.set_xlim(-3500, 19800)
    ax.set_ylim(23550, -1800)  # Inverted Y (top-to-bottom)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_edgecolor("#E2E8F0")
        sp.set_linewidth(0.8)

    for gx in range(-3000, 20000, 1000):
        ax.axvline(gx, color="#F1F5F9", lw=0.5, zorder=0)
    for gy in range(-1000, 24000, 1000):
        ax.axhline(gy, color="#F1F5F9", lw=0.5, zorder=0)

    # Rooms floor fill
    room_fills = {
        "grinding_room": "#F1F5F9",
        "drying_room": "#F1F5F9",
        "changing_room": "#F8FAFC",
        "prep_corridor": "#FFFFFF",
        "sulphide_area": "#F8FAFC",
        "on_hold_storage": "#F1F5F9",
        "main_hall": "#FFFFFF",
        "toilets": "#F1F5F9",
        "canteen": "#F8FAFC",
        "merged_cs_office": "#F8FAFC",
        "entryway": "#F1F5F9",
        "external_cold_storage": "#E2E8F0",
    }
    for rm in spec["rooms"]:
        fc = room_fills.get(rm["id"], "#FFFFFF")
        rect = patches.Rectangle((rm["x"], rm["y"]), rm["w"], rm["h"], facecolor=fc, edgecolor="none", zorder=1)
        ax.add_patch(rect)

    # Non-blocking floor striping zones
    for zn in spec["zones"]:
        zrect = patches.Rectangle(
            (zn["x"], zn["y"]),
            zn["w"],
            zn["h"],
            facecolor="#F1F5F9" if zn["id"] == "Z-SORTING" else "#F8FAFC",
            edgecolor="#475569",
            linewidth=1.1,
            linestyle="--",
            zorder=3,
        )
        ax.add_patch(zrect)
        cx, cy = zn["x"] + zn["w"] / 2.0, zn["y"] + zn["h"] / 2.0
        if zn["id"] == "Z-SORTING":
            ax.text(
                cx,
                cy,
                "SAMPLE SORTING DROP-OFF\n300 x 400 cm Zone\n(Old TLO & Stairs Demolished)",
                ha="center",
                va="center",
                fontsize=6.2,
                fontweight="bold",
                color="#334155",
                zorder=4,
            )
        elif zn["id"] == "Z-WALKWAY":
            ax.text(
                cx,
                cy + 700,
                "CENTRAL MAIN WALKWAY  (240 cm CLEAR CORRIDOR)",
                ha="center",
                va="center",
                rotation=90,
                fontsize=7.6,
                fontweight="bold",
                color="#334155",
                zorder=4,
            )
        elif zn["id"] == "Z-ONHOLD-PATH":
            ax.text(cx, cy, "60 cm WALKING PATH (400 cm)", ha="center", va="center", fontsize=6.0, fontweight="bold", color="#334155", zorder=4)
        elif zn["id"] == "Z-TOILET-CORR":
            ax.text(cx, cy, "Access Corridor to Canteen & Office", ha="center", va="center", fontsize=6.0, color="#475569", zorder=4)

    # Conveyors
    for conv in spec["conveyors"]:
        cx, cy, cw, ch = conv["x"], conv["y"], conv["w"], conv["h"]
        rect = patches.Rectangle((cx, cy), cw, ch, facecolor="#CBD5E1", edgecolor="#334155", linewidth=1.35, zorder=7)
        ax.add_patch(rect)
        # Roller slats every 350 mm
        for ry in range(int(cy + 250), int(cy + ch - 150), 350):
            ax.plot([cx + 45, cx + cw - 45], [ry, ry], color="#64748B", linewidth=0.6, zorder=8)
        # Flow arrow at top end of roller
        ax.annotate(
            "",
            xy=(cx + cw / 2.0, cy + 200),
            xytext=(cx + cw / 2.0, cy + 1200),
            arrowprops=dict(arrowstyle="->", color="#0F172A", lw=1.6),
            zorder=9,
        )
        lbl = (
            "WATERS ROLLER (60 cm)"
            if conv["id"] == "CONV-WATERS"
            else f"DOUBLE-DECK SOIL ROLLER {conv['id'][-1]} (Lower Dry | Upper Wet)"
        )
        ax.text(
            cx + cw / 2.0,
            cy + ch / 2.0 + 350,
            lbl,
            ha="center",
            va="center",
            rotation=90,
            fontsize=5.6,
            fontweight="bold",
            color="#0F172A",
            bbox=dict(boxstyle="square,pad=0.14", facecolor="#E2E8F0", edgecolor="none", alpha=0.94),
            zorder=10,
        )

    # Stations & Equipment (parents first, then benchtop children)
    parents = [i for i in spec["stations_and_equipment"] if i["parent_id"] is None]
    children = [i for i in spec["stations_and_equipment"] if i["parent_id"] is not None]

    # Map to quickly identify if a Soils desk hosts a fume hood
    fh_hosts = {ch["parent_id"] for ch in children if ch["category"] == "benchtop_fume_hood"}

    for item in parents:
        x, y, w, h = item["x"], item["y"], item["w"], item["h"]
        cat = item["category"]
        if cat in ("bench", "island_bench"):
            fc, ec, lw = "#E2E8F0", "#334155", 1.15
        elif cat in ("fume_hood",):
            fc, ec, lw = "#CBD5E1", "#0F172A", 1.6
        elif cat in ("drying_oven", "grinder", "fridge"):
            fc, ec, lw = "#D6D9DF", "#1E293B", 1.25
        elif cat in ("storage_rack",):
            fc, ec, lw = "#E2E8F0", "#334155", 1.2
        elif cat in ("wc_cubicle", "wash_alcove"):
            fc, ec, lw = "#FFFFFF", "#475569", 1.0
        else:
            fc, ec, lw = "#F1F5F9", "#334155", 1.15

        rect = patches.Rectangle((x, y), w, h, facecolor=fc, edgecolor=ec, linewidth=lw, zorder=8)
        ax.add_patch(rect)

        # Special hatches / details
        if cat == "fume_hood":
            hatch = patches.Rectangle((x, y), w, h, facecolor="none", edgecolor="#475569", hatch="///", linewidth=0.9, zorder=9)
            ax.add_patch(hatch)
        elif cat == "storage_rack":
            # Shelf longitudinal bars
            ax.plot([x + 60, x + w - 60], [y + h * 0.35, y + h * 0.35], color="#94A3B8", lw=0.7, zorder=9)
            ax.plot([x + 60, x + w - 60], [y + h * 0.65, y + h * 0.65], color="#94A3B8", lw=0.7, zorder=9)
        elif cat == "wash_alcove":
            for bx in (x + 250, x + 700):
                ax.add_patch(patches.Rectangle((bx, y + 250), 280, 420, facecolor="#E2E8F0", edgecolor="#475569", lw=0.8, zorder=9))
        elif cat == "kitchenette":
            ax.add_patch(patches.Rectangle((x + 150, y + 400), 420, 580, facecolor="#E2E8F0", edgecolor="#475569", lw=0.8, zorder=9))

        # Labels (clean non-overlapping placement)
        cx, cy = x + w / 2.0, y + h / 2.0
        if item["id"] in ("SUL-OUTER-BENCH", "SUL-DIV-BENCH"):
            pass  # children carry labels cleanly
        elif item["id"] == "SUL-ISLAND":
            ax.text(
                x + 480,
                cy,
                "CENTRAL ISLAND BENCH  (1.50 m x 5.40 m)\nDouble-Sided Worktop  •  3 Extra PCs",
                ha="center",
                va="center",
                rotation=90,
                fontsize=6.5,
                fontweight="bold",
                color="#0F172A",
                zorder=11,
            )
        elif cat == "waters_station":
            vertical = h > w
            short_nm = item["name"] + "\n(PC+Prt)"
            ax.text(cx, cy, short_nm, ha="center", va="center", rotation=90 if vertical else 0, fontsize=5.3, fontweight="bold", color="#0F172A", zorder=11)
        elif cat == "soils_station":
            short_nm = item["name"].replace(" + FH 1", "").replace(" + FH 2", "").replace("Hybrid Split/Reg", "Hybrid Split").replace("Shaker & Vial", "Shaker/Vial")
            sub = "PC+Prt" if item["has_pc"] else "60x130 Bench"
            if item["id"] in fh_hosts:
                tx = (x + (x + 730)) / 2.0
                ax.text(tx, cy, f"{item['id']}: Hybrid\nPC+Prt", ha="center", va="center", fontsize=4.6, fontweight="bold", color="#0F172A", zorder=11)
            else:
                ax.text(cx, cy, f"{short_nm}\n{sub}", ha="center", va="center", fontsize=5.1, fontweight="bold", color="#0F172A", zorder=11)
        elif cat == "office_desk":
            ax.text(cx, cy, f"{item['name']}\nDual-Screen", ha="center", va="center", fontsize=5.4, fontweight="bold", color="#0F172A", zorder=11)
        elif cat == "fridge":
            ax.text(cx, cy, "500 L\nFRIDGE", ha="center", va="center", rotation=90, fontsize=5.5, fontweight="bold", color="#0F172A", zorder=11)
        elif item["id"] == "POST-GRIND-PC":
            ax.text(cx, cy, "Post-Grind Scan PC\n60 x 120 cm", ha="center", va="center", fontsize=5.0, fontweight="bold", color="#0F172A", zorder=11)
        elif item["id"] == "LOG-RM":
            ax.text(cx, cy, "LOGISTICS / RAPID MOISTURE (344x77 cm)\nPC + Label Printer (Facing Wall)", ha="center", va="center", fontsize=5.1, fontweight="bold", color="#0F172A", zorder=11)
        elif item["id"] in ("LOG-WS-1", "LOG-WS-2"):
            ax.text(cx, cy, f"Logistics WS {item['id'][-1]}\n70x210 cm • PC", ha="center", va="center", fontsize=5.3, fontweight="bold", color="#0F172A", zorder=11)
        elif item["id"] == "LOG-SHELF":
            ax.text(cx, cy, "5-TIER SHELF\n70x150 cm", ha="center", va="center", fontsize=4.9, fontweight="bold", color="#0F172A", zorder=11)
        elif item["id"] in ("ONHOLD-RACK-A", "ONHOLD-RACK-B"):
            ax.text(cx, cy, item["name"].upper(), ha="center", va="center", fontsize=5.6, fontweight="bold", color="#0F172A", zorder=11)
        elif item["id"] in ("OVEN-1", "OVEN-2"):
            ax.text(cx, cy, item["name"], ha="center", va="center", rotation=90, fontsize=6.4, fontweight="bold", color="#0F172A", zorder=11)
        elif item["id"] == "CANT-KITCH":
            ax.text(cx, cy, "KITCHENETTE", ha="center", va="center", rotation=90, fontsize=5.8, fontweight="bold", color="#0F172A", zorder=11)
        elif item["id"] == "WC-BASINS":
            ax.text(cx, cy + 160, "Basins /\nBoiler", ha="center", va="center", fontsize=5.0, fontweight="bold", color="#0F172A", zorder=11)
        elif cat == "wc_cubicle":
            ax.text(cx, cy, item["id"].replace("-", " "), ha="center", va="center", fontsize=5.6, fontweight="bold", color="#0F172A", zorder=11)
        elif cat == "fume_hood":
            ax.text(cx, cy, "Grinding\nFume Hood", ha="center", va="center", fontsize=5.8, fontweight="bold", color="#0F172A", bbox=dict(boxstyle="square,pad=0.14", facecolor="#FFFFFF", edgecolor="none", alpha=0.92), zorder=12)
        else:
            ax.text(cx, cy, item["name"], ha="center", va="center", fontsize=5.8, fontweight="bold", color="#0F172A", zorder=11)

        if item.get("seat"):
            draw_chair_symbol(ax, item["seat"])

    # Benchtop children
    for ch in children:
        x, y, w, h = ch["x"], ch["y"], ch["w"], ch["h"]
        cat = ch["category"]
        if cat == "benchtop_fume_hood":
            rect = patches.Rectangle((x, y), w, h, facecolor="#CBD5E1", edgecolor="#0F172A", linewidth=1.35, hatch="///", zorder=11)
            ax.add_patch(rect)
            ax.text(x + w / 2.0, y + h / 2.0, "FH\n50x50", ha="center", va="center", fontsize=5.0, fontweight="bold", color="#0F172A", bbox=dict(boxstyle="square,pad=0.05", facecolor="#FFFFFF", edgecolor="none", alpha=0.85), zorder=12)
        else:
            fc = "#D6D9DF" if cat in ("sink", "toc_station") else "#CBD5E1"
            rect = patches.Rectangle((x, y), w, h, facecolor=fc, edgecolor="#334155", linewidth=1.0, zorder=10)
            ax.add_patch(rect)
            if cat == "sink":
                ax.add_patch(patches.Rectangle((x + 80, y + 120), w - 160, h - 240, facecolor="#F8FAFC", edgecolor="#64748B", lw=0.75, zorder=11))
            short_lbl = {
                "SUL-WPC-1": "Wall PC 1",
                "SUL-WPC-2": "Wall PC 2",
                "SUL-WPC-3": "Wall PC 3",
                "SUL-WPC-4": "Wall PC 4",
                "SUL-IPC-1": "Island\nPC 1",
                "SUL-IPC-2": "Island\nPC 2",
                "SUL-IPC-3": "Island\nPC 3",
                "SUL-DPC-1": "PC 1",
                "SUL-SHK-1": "Shaker 1\n60x90",
                "SUL-SHK-2": "Shaker 2\n60x90",
                "SUL-SINK-1": "WASH SINK 1",
                "SUL-SINK-2": "WASH SINK 2",
                "SUL-TOC": "TOC Vac Pump\n24-Cell (15x15)",
            }.get(ch["id"], ch["name"])
            rot = 90 if (h > w and ch["id"].startswith("SUL-") and not ch["id"].startswith("SUL-WPC") and not ch["id"].startswith("SUL-IPC")) else 0
            ax.text(x + w / 2.0, y + h / 2.0, short_lbl, ha="center", va="center", rotation=rot, fontsize=4.7, fontweight="bold", color="#0F172A", zorder=12)

        if ch.get("seat"):
            draw_chair_symbol(ax, ch["seat"])

    # Walls (split cleanly around doors)
    for wall in spec["walls"]:
        segs = split_wall_around_doors(wall, spec["doors"])
        kind = wall["kind"]
        if kind == "exterior":
            col, lw = "#0F172A", 3.2
        elif kind == "glazed_partition":
            col, lw = "#64748B", 2.0
        elif kind == "external_enclosure":
            col, lw = "#334155", 2.0
        else:
            col, lw = "#334155", 2.2
        for sx1, sy1, sx2, sy2 in segs:
            if kind == "glazed_partition":
                ax.plot([sx1, sx2], [sy1, sy2], color=col, linewidth=lw, linestyle=(0, (6, 2)), zorder=14)
            else:
                ax.plot([sx1, sx2], [sy1, sy2], color=col, linewidth=lw, solid_capstyle="butt", zorder=14)

    # Doors & Swings
    for door in spec["doors"]:
        draw_door_symbol(ax, door)

    # Door / Gate Callouts
    ax.text(6650, -320, "EXIT DOOR 1\n(SOILS OUT)", ha="center", va="bottom", fontsize=6.4, fontweight="bold", color="#334155", zorder=20)
    ax.text(17530, -320, "EXIT DOOR 2\n(WATERS OUT)", ha="center", va="bottom", fontsize=6.4, fontweight="bold", color="#1E3A8A", zorder=20)
    ax.text(16100, 18820, "MAIN ENTRANCE DOOR\n(SAMPLE DROP-OFF)", ha="center", va="top", fontsize=6.6, fontweight="bold", color="#0F172A", zorder=20)
    ax.text(4480, 19400, "Door to\nCanteen", ha="right", va="center", fontsize=5.3, fontweight="bold", color="#334155", zorder=20)

    # Room & Zone Headings
    hdr_pill = dict(boxstyle="round,pad=0.22", facecolor="#FFFFFF", edgecolor="#E2E8F0", lw=0.6, alpha=0.94)
    ax.text(1350, 480, "GRINDING ROOM\n(Retained • 2,700 x 4,700 mm)", ha="center", va="center", fontsize=6.0, fontweight="bold", color="#0F172A", zorder=18)
    ax.text(4300, 480, "DRYING ROOM\n(Retained • 3,200 x 3,500 mm)", ha="center", va="center", fontsize=6.0, fontweight="bold", color="#0F172A", zorder=18)
    ax.text(1350, 5900, "CHANGING ROOM\n(Retained)", ha="center", va="center", fontsize=6.2, fontweight="bold", color="#0F172A", zorder=18)
    ax.text(4300, 5600, "PREP CORRIDOR", ha="center", va="center", fontsize=6.4, fontweight="bold", color="#475569", bbox=hdr_pill, zorder=18)
    ax.text(3050, 8180, "SULPHIDE AREA\n(5,900 x 9,088 mm • 8 PCs + Scan PC)", ha="center", va="center", fontsize=6.3, fontweight="bold", color="#0F172A", zorder=18)
    ax.text(8550, 16270, "TOILETS — UPGRADED TO 4 W/Cs (5,337 x 2,048 mm)", ha="center", va="center", fontsize=5.7, fontweight="bold", color="#0F172A", zorder=18)
    ax.text(2275, 18600, "CANTEEN (MODERNIZED)\nDirect Door from CS Office", ha="center", va="center", fontsize=6.1, fontweight="bold", color="#0F172A", zorder=18)
    ax.text(8550, 18520, "MERGED CUSTOMER SERVICE / ADMIN OFFICE (8,000 x 3,442 mm)\n8 Workstations with Dual-Screen PCs (Dividing Wall Removed)", ha="center", va="center", fontsize=6.1, fontweight="bold", color="#0F172A", zorder=18)
    ax.text(13290, 19850, "ENTRYWAY", ha="center", va="center", rotation=90, fontsize=6.5, fontweight="bold", color="#334155", zorder=18)
    ax.text(-1650, 9000, "EXTERNAL COLD STORAGE\n(Retained Outside Left Wall • 1,800 x 10,800 mm)", ha="center", va="center", rotation=90, fontsize=6.5, fontweight="bold", color="#334155", zorder=18)
    ax.text(9400, 4420, "SOILS LANE — 3 x 5 ARRAY (15 STATIONS) + 2 DOUBLE-DECK ROLLERS", ha="center", va="center", fontsize=7.0, fontweight="bold", color="#0F172A", bbox=hdr_pill, zorder=18)
    ax.text(16300, 2650, "WATERS LANE (10 STATIONS)", ha="center", va="center", fontsize=7.0, fontweight="bold", color="#1E3A8A", bbox=hdr_pill, zorder=18)

    # Sulphide intervals annotations (150 cm bench intervals)
    for gy_mid in (9730, 11830, 13930):
        ax.text(350, gy_mid, "150 cm bench", ha="center", va="center", rotation=90, fontsize=5.1, color="#475569", zorder=12)

    # Sample Segregation Flow Overlays (subtle dashed arrows)
    for fp in spec["flow_paths"]:
        pts = fp["points"]
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        col = "#1E3A8A" if fp["stream"] == "waters" else ("#334155" if fp["stream"] == "soils" else "#64748B")
        ls = "--" if fp["stream"] != "soils_prep" else ":"
        ax.plot(xs[:-1], ys[:-1], color=col, linewidth=1.6, linestyle=ls, alpha=0.85, zorder=16)
        ax.annotate(
            "",
            xy=(xs[-1], ys[-1]),
            xytext=(xs[-2], ys[-2]),
            arrowprops=dict(arrowstyle="-|>,head_width=0.35,head_length=0.55", color=col, lw=1.6, ls=ls),
            zorder=16,
        )

    # Outer & Interior Dimension Annotations
    draw_dimension_line(ax, 0, -1100, 2700, -1100, "2,700 mm", fontsize=6.2)
    draw_dimension_line(ax, 2700, -1100, 5900, -1100, "3,200 mm", fontsize=6.2)
    draw_dimension_line(ax, 5900, -1100, 18293, -1100, "12,393 mm (Main Hall)", fontsize=6.4)
    draw_dimension_line(ax, 0, -1620, 18293, -1620, "18,293 mm MAIN SHELL WIDTH", fontsize=6.8)

    draw_dimension_line(ax, 18950, 0, 18950, 18134, "18,134 mm SHELL DEPTH", fontsize=6.8, vertical=True)
    draw_dimension_line(ax, -550, 0, -550, 7100, "7,100 mm", fontsize=6.0, vertical=True)
    draw_dimension_line(ax, -550, 7100, -550, 16188, "9,088 mm (Sulphide)", fontsize=6.0, vertical=True)
    draw_dimension_line(ax, -550, 16188, -550, 18134, "1,946", fontsize=5.6, vertical=True)

    draw_dimension_line(ax, 0, 22150, 4550, 22150, "4,550 mm (Canteen)", fontsize=6.2)
    draw_dimension_line(ax, 4550, 22150, 12550, 22150, "8,000 mm (Merged Office)", fontsize=6.2)
    draw_dimension_line(ax, 12550, 22150, 14030, 22150, "1,480", fontsize=5.6)
    draw_dimension_line(ax, 0, 22920, 18293, 22920, "18,293 mm TOTAL BUILDING SHELL WIDTH  (Front Wing Depth: 3,442 mm)", fontsize=6.8)

    draw_dimension_line(ax, 700, 15550, 2200, 15550, "150 cm aisle", fontsize=5.6)
    draw_dimension_line(ax, 2200, 15550, 3700, 15550, "1.50 m", fontsize=5.6)
    draw_dimension_line(ax, 3700, 15550, 5200, 15550, "150 cm aisle", fontsize=5.6)
    draw_dimension_line(ax, 12300, 3300, 14700, 3300, "240 cm CLEAR", fontsize=5.8)

    # Right Sidebar Legend & Specification Key
    ax_leg.set_xlim(0, 1)
    ax_leg.set_ylim(0, 1)
    ax_leg.set_xticks([])
    ax_leg.set_yticks([])
    for sp in ax_leg.spines.values():
        sp.set_edgecolor("#CBD5E1")
        sp.set_linewidth(1.0)

    ax_leg.add_patch(patches.Rectangle((0, 0.945), 1, 0.055, facecolor="#0F172A", edgecolor="none"))
    ax_leg.text(0.05, 0.972, "LEGEND & ARCHITECTURAL KEY", color="#FFFFFF", fontsize=9.2, fontweight="bold", va="center")

    legend_rows = [
        ("#F1F5F9", "#334155", "Workstations & Benches", "10 Waters • 15 Soils • 8 CS Dual-Screen"),
        ("#CBD5E1", "#334155", "Roller Conveyors (3 Total)", "1x 60 cm Waters • 2x Double-Deck Soils"),
        ("#CBD5E1", "#0F172A", "Fume Hoods (3 Total)", "2x 50x50 cm (S8, S11) + 1x Grinding"),
        ("#E2E8F0", "#334155", "Sulphide Wing (8+1 PCs)", "1.50x5.40 m Island • Shakers • Sinks • TOC"),
        ("#D6D9DF", "#1E293B", "Retained Heavy Equipment", "2x Drying Ovens • 2x Grinders • Ext Cold"),
        ("#E2E8F0", "#334155", "On-Hold & Logistics Storage", "2x 400 cm 6-Tier Racks • 500 L Fridge"),
        ("#F8FAFC", "#475569", "Demarcated Floor Zones", "240 cm Walkway • 300x400 cm Sorting"),
    ]
    y_cur = 0.895
    for fc, ec, title, desc in legend_rows:
        ax_leg.add_patch(patches.Rectangle((0.05, y_cur - 0.015), 0.11, 0.028, facecolor=fc, edgecolor=ec, lw=1.1))
        ax_leg.text(0.19, y_cur + 0.005, title, fontsize=7.6, fontweight="bold", color="#0F172A", va="center")
        ax_leg.text(0.19, y_cur - 0.016, desc, fontsize=6.6, color="#475569", va="center")
        y_cur -= 0.058

    ax_leg.plot([0.05, 0.95], [0.49, 0.49], color="#CBD5E1", lw=0.9)
    ax_leg.text(0.05, 0.465, "ONE-DIRECTIONAL SAMPLE FLOW", fontsize=8.4, fontweight="bold", color="#0F172A")
    flow_rows = [
        ("#0F172A", "-", "Main Door -> 300 x 400 cm Sample Sorting"),
        ("#1E3A8A", "--", "Waters Stream (Bottom->Top) -> Exit Door 2"),
        ("#334155", "--", "Soils Stream (Bottom->Top) -> Exit Door 1"),
        ("#64748B", ":", "Dry Soil Loop -> Prep Corridor / Drying / Grinding"),
    ]
    yf = 0.432
    for col, ls, txt in flow_rows:
        ax_leg.plot([0.05, 0.16], [yf, yf], color=col, lw=1.8, linestyle=ls)
        ax_leg.text(0.19, yf, txt, fontsize=6.8, color="#1E293B", va="center")
        yf -= 0.032

    ax_leg.plot([0.05, 0.95], [0.30, 0.30], color="#CBD5E1", lw=0.9)
    ax_leg.text(0.05, 0.275, "CONSOLIDATED FACILITY METRICS", fontsize=8.4, fontweight="bold", color="#0F172A")

    items = spec["stations_and_equipment"]
    total_pcs = sum(1 for i in items if i["has_pc"])
    total_printers = sum(1 for i in items if i["has_label_printer"])
    main_area_m2 = (spec["shell"]["main_building"]["w"] * spec["shell"]["main_building"]["h"]) / 1e6
    ext_area_m2 = (spec["shell"]["front_extension"]["w"] * spec["shell"]["front_extension"]["h"]) / 1e6
    metrics = [
        f"• Gross Internal Area: {main_area_m2 + ext_area_m2:.1f} m2 (+19.4 m2 Ext Cold)",
        f"• Production Stations: 25 (10 Waters + 15 Soils)",
        f"• Total Workstations / PCs: {total_pcs} PCs (50 Monitors)",
        f"• Label Printers: {total_printers}  |  Fume Hoods: 3",
        f"• Roller Conveyors: 3 (1 Waters + 2 Double-Deck)",
        "• Clear Central Walkway: 240 cm (0 Cross-Traffic)",
        "• Drying Door (D-DRY): Optimized +Y Swing (Clear)",
        "• Demolished: Team Leaders Office, Stairs, CS Divider",
    ]
    ym = 0.242
    for m in metrics:
        ax_leg.text(0.05, ym, m, fontsize=6.8, color="#334155", va="center")
        ym -= 0.028

    for ext in ("svg", "png", "pdf"):
        out_file = OUT_DIR / f"Project_Vol_2D_Spec.{ext}"
        fig.savefig(out_file, dpi=300, bbox_inches="tight", pad_inches=0.12)
        print(f"Saved 2D spec: {out_file}")
    plt.close(fig)


def style_header_row(ws: openpyxl.worksheet.worksheet.Worksheet, row_idx: int, col_count: int) -> None:
    fill = PatternFill("solid", fgColor="0F172A")
    font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
    align = Alignment(horizontal="center", vertical="center", wrap_text=True)
    for col in range(1, col_count + 1):
        cell = ws.cell(row=row_idx, column=col)
        cell.fill = fill
        cell.font = font
        cell.alignment = align
    ws.row_dimensions[row_idx].height = 24


def apply_table_borders(ws: openpyxl.worksheet.worksheet.Worksheet, min_r: int, max_r: int, min_c: int, max_c: int) -> None:
    thin = Side(style="thin", color="CBD5E1")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    zebra = PatternFill("solid", fgColor="F8FAFC")
    for r in range(min_r, max_r + 1):
        for c in range(min_c, max_c + 1):
            cell = ws.cell(row=r, column=c)
            cell.border = border
            if r > min_r and r % 2 == 1 and cell.fill.fill_type is None:
                cell.fill = zebra


def autofit_columns(ws: openpyxl.worksheet.worksheet.Worksheet, max_width: int = 44) -> None:
    for col in ws.columns:
        col_letter = get_column_letter(col[0].column)
        best = 10
        for cell in col:
            if cell.row <= 2:
                continue
            val = str(cell.value or "")
            for line in val.splitlines():
                best = max(best, len(line) + 3)
        ws.column_dimensions[col_letter].width = min(best, max_width)


def generate_excel_schedule(spec: dict[str, Any]) -> None:
    """Create 3-tab Excel BOM & Segregation Schedule workbook."""
    wb = openpyxl.Workbook()
    items = spec["stations_and_equipment"]
    conveyors = spec["conveyors"]
    rooms = spec["rooms"]
    rooms_by_id = {r["id"]: r for r in rooms}

    # --- TAB 1: Executive Summary ---
    ws1 = wb.active
    ws1.title = "Executive Summary"
    ws1.views.sheetView[0].showGridLines = True

    ws1.merge_cells("A1:F1")
    ws1["A1"] = f"{spec['meta']['project_name'].upper()} — {spec['meta']['facility_title'].upper()}"
    ws1["A1"].font = Font(name="Calibri", size=14, bold=True, color="FFFFFF")
    ws1["A1"].fill = PatternFill("solid", fgColor="0F172A")
    ws1["A1"].alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws1.row_dimensions[1].height = 30

    ws1.merge_cells("A2:F2")
    ws1["A2"] = f"{spec['meta']['address']}  |  Consolidated Phases 1, 2 & 3  |  Single Source of Truth: data/layout_spec.json"
    ws1["A2"].font = Font(name="Calibri", size=10, italic=True, color="334155")
    ws1["A2"].fill = PatternFill("solid", fgColor="E2E8F0")
    ws1["A2"].alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws1.row_dimensions[2].height = 20

    # KPI Summary Block
    ws1["A4"] = "Key Facility Metrics"
    ws1["A4"].font = Font(name="Calibri", size=11, bold=True, color="0F172A")
    headers1 = ["Metric", "Count / Value", "Unit", "Operational Scope"]
    for idx, h in enumerate(headers1, start=1):
        ws1.cell(row=5, column=idx, value=h)
    style_header_row(ws1, 5, 4)

    main_m2 = spec["shell"]["main_building"]["w"] * spec["shell"]["main_building"]["h"] / 1e6
    ext_m2 = spec["shell"]["front_extension"]["w"] * spec["shell"]["front_extension"]["h"] / 1e6
    cold_m2 = spec["shell"]["external_cold_storage"]["w"] * spec["shell"]["external_cold_storage"]["h"] / 1e6
    total_pcs = sum(1 for i in items if i["has_pc"])
    dual_pcs = sum(1 for i in items if i["dual_monitor"])
    total_displays = total_pcs + dual_pcs
    total_printers = sum(1 for i in items if i["has_label_printer"])
    total_hoods = sum(1 for i in items if i["has_fume_hood"])

    kpis = [
        ("Main Shell Footprint", round(main_m2, 2), "m2", "18,293 x 18,134 mm (Left Wing + Main Hall)"),
        ("Front Extension Footprint", round(ext_m2, 2), "m2", "14,030 x 3,442 mm (Canteen + Merged CS Office + Entryway)"),
        ("Gross Internal Area (Main + Front)", round(main_m2 + ext_m2, 2), "m2", "Consolidated indoor operational footprint"),
        ("External Cold Storage (Retained)", round(cold_m2, 2), "m2", "1,800 x 10,800 mm outside west exterior wall"),
        ("Waters Lane Stations", sum(1 for i in items if i["category"] == "waters_station"), "stations", "2 Reg + 4 Reg/Split + 4 Testing + 60 cm roller"),
        ("Soils 3x5 Array Stations", sum(1 for i in items if i["category"] == "soils_station"), "stations", "6 Reg + 6 Hybrid Split/Reg + 3 Shaker/Vial + 2 double-deck rollers"),
        ("Sulphide Room PCs (+ Post-Grind Scan)", 8, "+ 1 Scan PC", "4 outer wall + 3 island (1.50x5.40 m) + 1 dividing bench + 1 scan"),
        ("Merged CS Office Workstations", dual_pcs, "desks", "8 dual-screen PC workstations (16 displays)"),
        ("Total PCs / Total Monitors", f"{total_pcs} / {total_displays}", "units", "All workstations across Waters, Soils, Sulphide, Logistics & CS Office"),
        ("Label Printers", total_printers, "units", "10 Waters + 12 Soils + 1 Rapid Moisture"),
        ("Fume Hoods (Total)", total_hoods, "units", "1 Grinding Room (108x108 cm) + 2 Soils Benchtop (50x50 cm on S8 & S11)"),
        ("Roller Conveyors", len(conveyors), "lines", "1 single-deck Waters (11.25 m) + 2 double-deck Soils (9.80 m each)"),
        ("Central Segregation Walkway", 240, "cm", "Continuous 240 cm clear barrier between Soils & Waters (0 crossings)"),
    ]
    for r_off, row_vals in enumerate(kpis, start=6):
        for c_idx, val in enumerate(row_vals, start=1):
            cell = ws1.cell(row=r_off, column=c_idx, value=val)
            cell.font = Font(name="Calibri", size=10, bold=(c_idx == 2), color="0F172A")
            cell.alignment = Alignment(horizontal="center" if c_idx in (2, 3) else "left", vertical="center")
    apply_table_borders(ws1, 5, 5 + len(kpis), 1, 4)

    # Room Area Schedule
    start_r = 5 + len(kpis) + 3
    ws1.cell(row=start_r - 1, column=1, value="Room & Zone Schedule").font = Font(name="Calibri", size=11, bold=True, color="0F172A")
    room_headers = ["Room ID", "Room Name", "Wing", "Width (mm)", "Depth (mm)", "Net Area (m2)", "Status", "Phase"]
    for idx, h in enumerate(room_headers, start=1):
        ws1.cell(row=start_r, column=idx, value=h)
    style_header_row(ws1, start_r, len(room_headers))

    for off, rm in enumerate(rooms, start=start_r + 1):
        net_mm2 = rm["w"] * rm["h"]
        if rm.get("exclude_subrect"):
            ex = rm["exclude_subrect"]
            net_mm2 -= ex["w"] * ex["h"]
        vals = [rm["id"], rm["name"], rm["wing"], rm["w"], rm["h"], round(net_mm2 / 1e6, 2), rm["status"], rm["phase"]]
        for c_idx, v in enumerate(vals, start=1):
            c = ws1.cell(row=off, column=c_idx, value=v)
            c.font = Font(name="Calibri", size=10, color="0F172A")
            c.alignment = Alignment(horizontal="right" if c_idx in (4, 5, 6) else "left", vertical="center")
            if c_idx == 6:
                c.number_format = "0.00"
    apply_table_borders(ws1, start_r, start_r + len(rooms), 1, len(room_headers))

    # Scope Summary (Demolished vs Retained vs Upgraded)
    scope_r = start_r + len(rooms) + 3
    ws1.cell(row=scope_r - 1, column=1, value="Demolition, Retention & Redevelopment Scope").font = Font(name="Calibri", size=11, bold=True, color="0F172A")
    for idx, h in enumerate(["Scope Category", "Element / Area", "CapEx / Operational Impact"], start=1):
        ws1.cell(row=scope_r, column=idx, value=h)
    style_header_row(ws1, scope_r, 3)
    scope_rows = []
    for txt in spec["meta"]["strategic_narrative"]["scope_changes"]["demolished"]:
        scope_rows.append(("Demolished", txt, "Clears Main Hall intake & merges open-plan CS Office"))
    for txt in spec["meta"]["strategic_narrative"]["scope_changes"]["retained"]:
        scope_rows.append(("Retained (Zero Move)", txt, "Preserves major utility plant & heavy M&E investment"))
    for txt in spec["meta"]["strategic_narrative"]["scope_changes"]["upgraded_and_new"]:
        scope_rows.append(("New / Upgraded", txt, "Delivers one-piece flow, 240 cm segregation & workplace upgrade"))
    for off, svals in enumerate(scope_rows, start=scope_r + 1):
        for c_idx, v in enumerate(svals, start=1):
            c = ws1.cell(row=off, column=c_idx, value=v)
            c.font = Font(name="Calibri", size=10, bold=(c_idx == 1), color="0F172A")
            c.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
    apply_table_borders(ws1, scope_r, scope_r + len(scope_rows), 1, 3)

    ws1.freeze_panes = "A6"
    autofit_columns(ws1, max_width=56)

    # --- TAB 2: Equipment Schedule ---
    ws2 = wb.create_sheet("Equipment Schedule")
    ws2.merge_cells("A1:M1")
    ws2["A1"] = "PROJECT VOL — ROOM-BY-ROOM FURNITURE, CONVEYOR & EQUIPMENT SCHEDULE"
    ws2["A1"].font = Font(name="Calibri", size=13, bold=True, color="FFFFFF")
    ws2["A1"].fill = PatternFill("solid", fgColor="0F172A")
    ws2["A1"].alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws2.row_dimensions[1].height = 28

    eq_headers = [
        "Item ID", "Room", "Category", "Description", "Width (mm)", "Length (mm)", "Height (mm)",
        "Qty", "Status", "PCs", "Label Printer", "Fume Hood", "Utilities & Notes"
    ]
    for idx, h in enumerate(eq_headers, start=1):
        ws2.cell(row=2, column=idx, value=h)
    style_header_row(ws2, 2, len(eq_headers))

    row_i = 3
    for conv in conveyors:
        rm_nm = rooms_by_id[conv["room_id"]]["name"]
        vals = [
            conv["id"], rm_nm, "conveyor", conv["name"], conv["w"], conv["h"], 920,
            1, "New", 0, 0, 0, f"Power 230V • {len(conv['decks'])} deck(s): {conv['notes']}"
        ]
        for c_idx, v in enumerate(vals, start=1):
            cell = ws2.cell(row=row_i, column=c_idx, value=v)
            cell.font = Font(name="Calibri", size=9.5, color="0F172A")
            cell.alignment = Alignment(horizontal="right" if c_idx in (5, 6, 7, 8, 10, 11, 12) else "left", vertical="center", wrap_text=True)
        row_i += 1

    for it in items:
        rm_nm = rooms_by_id[it["room_id"]]["name"]
        utils = []
        if it["has_pc"]:
            utils.append("Data + Power" + (" (Dual Monitor)" if it["dual_monitor"] else ""))
        if it["has_label_printer"]:
            utils.append("Label Printer")
        if it["has_fume_hood"]:
            utils.append("LEV Extraction")
        if it["has_sink"]:
            utils.append("Hot/Cold Water + Drain")
        if it["has_shaker"]:
            utils.append("230V Bench Power")
        if it["has_vacuum_pump"]:
            utils.append("Vacuum + Drainage")
        if it["category"] in ("drying_oven", "grinder", "fridge"):
            utils.append("Dedicated 3-Phase/230V")
        util_str = "; ".join(utils) if utils else "Standard"
        vals = [
            it["id"], rm_nm, it["category"], it["name"], it["w"], it["h"], it["height_mm"],
            1, "Retained" if it["retained"] else "New / Reconfigured",
            1 if it["has_pc"] else 0,
            1 if it["has_label_printer"] else 0,
            1 if it["has_fume_hood"] else 0,
            f"{util_str} — {it['notes']}",
        ]
        for c_idx, v in enumerate(vals, start=1):
            cell = ws2.cell(row=row_i, column=c_idx, value=v)
            cell.font = Font(name="Calibri", size=9.5, color="0F172A")
            cell.alignment = Alignment(horizontal="right" if c_idx in (5, 6, 7, 8, 10, 11, 12) else "left", vertical="center", wrap_text=True)
        row_i += 1

    # Totals row with formulas
    ws2.cell(row=row_i, column=1, value="TOTAL").font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
    ws2.cell(row=row_i, column=4, value=f"={row_i - 3} Scheduled Items").font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
    for c_idx, col_let in [(8, "H"), (10, "J"), (11, "K"), (12, "L")]:
        c = ws2.cell(row=row_i, column=c_idx, value=f"=SUM({col_let}3:{col_let}{row_i - 1})")
        c.font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
        c.alignment = Alignment(horizontal="right", vertical="center")
    for c_idx in range(1, len(eq_headers) + 1):
        ws2.cell(row=row_i, column=c_idx).fill = PatternFill("solid", fgColor="1E3A8A")
    apply_table_borders(ws2, 2, row_i, 1, len(eq_headers))
    ws2.freeze_panes = "A3"
    autofit_columns(ws2, max_width=48)

    # --- TAB 3: Segregation & Flow Matrix ---
    ws3 = wb.create_sheet("Segregation & Flow Matrix")
    ws3.merge_cells("A1:D1")
    ws3["A1"] = "PROJECT VOL — SAMPLE SEGREGATION & ONE-DIRECTIONAL FLOW MATRIX"
    ws3["A1"].font = Font(name="Calibri", size=13, bold=True, color="FFFFFF")
    ws3["A1"].fill = PatternFill("solid", fgColor="0F172A")
    ws3["A1"].alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws3.row_dimensions[1].height = 28

    m_headers = ["Workflow Dimension", "Waters Stream", "Soils Stream", "Dry Soil / Sulphide & Sample Control"]
    for idx, h in enumerate(m_headers, start=1):
        ws3.cell(row=2, column=idx, value=h)
    style_header_row(ws3, 2, 4)

    matrix_rows = [
        ("Entry Point", "Main Entrance Door (X=15,400..16,800, Y=18,134)", "Main Entrance Door (X=15,400..16,800, Y=18,134)", "Prep Corridor / Vestibule link off Main Hall"),
        ("Initial Triage & Sort", "300 x 400 cm Sorting Drop-Off Zone (east side)", "300 x 400 cm Sorting Drop-Off Zone (west side)", "Post-Grind Scan PC (60x120 cm) after Grinding/Drying"),
        ("Physical Segregation Barrier", "Right side of 240 cm Central Main Walkway (X >= 14,700)", "Left side of 240 cm Central Main Walkway (X <= 12,300)", "Walled Left Wing (X = 0..5,900) separated from Main Hall"),
        ("Processing Stations", "10 Stations: 2 Reg + 4 Reg/Split + 4 Testing (all PC+Prt)", "15 Stations (3x5 grid, 60x130 cm, 150 cm gaps; 12 PC+Prt)", "8 Sulphide PCs (4 wall + 3 island 1.50x5.40 m + 1 div) + 2 Shakers + 2 Sinks + TOC"),
        ("Conveyor Architecture", "1x 60 cm Single-Deck Roller Conveyor (11.25 m)", "2x 60 cm Double-Deck Rollers: Lower Dry | Upper Wet/Prepared", "Manual short-hop trays via 150 cm Sulphide aisles & Prep Corridor"),
        ("Extraction / Containment", "Closed liquid handling & testing stations", "2x 50x50 cm Benchtop Fume Hoods (S8 & S11 Hybrid)", "1x Grinding Fume Hood (108x108 cm) + TOC Vacuum Extraction"),
        ("Logistics / QC Support", "5-Tier Subcontract Shelf (70x150 cm) at north-east", "Rapid Moisture Bench (344x77 cm) + Logistics WS 1 & 2 (70x210 cm)", "Drying Room (2 Ovens) & Grinding Room (2 Grinders) retained"),
        ("Quarantine & Cold Storage", "Routed via rear corridor or External Cold Storage", "On-Hold Storage (2x 400 cm 6-tier racks, 60 cm path) + 500 L Fridge", "External Cold Storage (1,800 x 10,800 mm) outside west wall"),
        ("Outbound Dispatch Door", "Exit Door 2 (Waters Out) at X=16,980..18,080, Y=0", "Exit Door 1 (Soils Out) at X=6,100..7,200, Y=0", "Returns to Soils upper deck or dispatched via Exit Door 1"),
        ("Cross-Stream Touchpoints", "0 (validated zero polyline crossings)", "0 (validated zero polyline crossings)", "0 cross-contamination with Waters Lane"),
    ]
    for off, rvals in enumerate(matrix_rows, start=3):
        for c_idx, v in enumerate(rvals, start=1):
            c = ws3.cell(row=off, column=c_idx, value=v)
            c.font = Font(name="Calibri", size=10, bold=(c_idx == 1), color="0F172A")
            c.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
        ws3.row_dimensions[off].height = 30
    apply_table_borders(ws3, 2, 2 + len(matrix_rows), 1, 4)
    ws3.freeze_panes = "A3"
    autofit_columns(ws3, max_width=46)

    for ws in (ws1, ws2, ws3):
        ws.page_setup.orientation = ws.ORIENTATION_LANDSCAPE
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0
        ws.sheet_properties.pageSetUpPr.fitToPage = True

    out_xlsx = OUT_DIR / "Project_Vol_Equipment_Schedule.xlsx"
    wb.save(out_xlsx)
    print(f"Saved Excel BOM: {out_xlsx}")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    spec = load_spec()
    generate_2d_plans(spec)
    generate_excel_schedule(spec)


if __name__ == "__main__":
    main()
