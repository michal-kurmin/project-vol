"""Automated geometry, clearance, door-swing, and inventory validator for Project Vol."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parent.parent
SPEC_PATH = ROOT_DIR / "data" / "layout_spec.json"


def rect_overlap(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> tuple[float, float]:
    """Return (ox, oy) overlap dimensions in mm between two AABBs (x1, y1, x2, y2)."""
    ox = min(a[2], b[2]) - max(a[0], b[0])
    oy = min(a[3], b[3]) - max(a[1], b[1])
    return ox, oy


def item_box(item: dict[str, Any]) -> tuple[float, float, float, float]:
    return (float(item["x"]), float(item["y"]), float(item["x"] + item["w"]), float(item["y"] + item["h"]))


def rect_contains(outer: tuple[float, float, float, float], inner: tuple[float, float, float, float], tol: float = 1e-6) -> bool:
    return (
        inner[0] >= outer[0] - tol
        and inner[1] >= outer[1] - tol
        and inner[2] <= outer[2] + tol
        and inner[3] <= outer[3] + tol
    )


def circle_intersects_rect(cx: float, cy: float, r: float, rect: tuple[float, float, float, float]) -> bool:
    """Return True if circle (cx, cy, r) strictly overlaps AABB (x1, y1, x2, y2)."""
    closest_x = max(rect[0], min(cx, rect[2]))
    closest_y = max(rect[1], min(cy, rect[3]))
    dx = cx - closest_x
    dy = cy - closest_y
    return (dx * dx + dy * dy) < (r * r - 1e-6)


def ccw(ax: float, ay: float, bx: float, by: float, cx: float, cy: float) -> float:
    return (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)


def segments_intersect(p1: tuple[float, float], p2: tuple[float, float], q1: tuple[float, float], q2: tuple[float, float]) -> bool:
    """Return True if closed 2D segments p1-p2 and q1-q2 intersect."""
    if max(p1[0], p2[0]) < min(q1[0], q2[0]) or max(q1[0], q2[0]) < min(p1[0], p2[0]):
        return False
    if max(p1[1], p2[1]) < min(q1[1], q2[1]) or max(q1[1], q2[1]) < min(p1[1], p2[1]):
        return False
    d1 = ccw(*p1, *p2, *q1)
    d2 = ccw(*p1, *p2, *q2)
    d3 = ccw(*q1, *q2, *p1)
    d4 = ccw(*q1, *q2, *p2)
    if ((d1 > 0 and d2 < 0) or (d1 < 0 and d2 > 0)) and ((d3 > 0 and d4 < 0) or (d3 < 0 and d4 > 0)):
        return True
    # Collinear overlap check
    eps = 1e-6
    for val, pt, s_a, s_b in [(d1, q1, p1, p2), (d2, q2, p1, p2), (d3, p1, q1, q2), (d4, p2, q1, q2)]:
        if abs(val) < eps:
            if min(s_a[0], s_b[0]) - eps <= pt[0] <= max(s_a[0], s_b[0]) + eps and min(s_a[1], s_b[1]) - eps <= pt[1] <= max(s_a[1], s_b[1]) + eps:
                return True
    return False


def wall_aabb(wall: dict[str, Any], shell: dict[str, Any]) -> tuple[float, float, float, float]:
    """Compute physical wall footprint in mm following exterior-outward convention."""
    x1, y1, x2, y2 = float(wall["x1"]), float(wall["y1"]), float(wall["x2"]), float(wall["y2"])
    t = float(wall["thickness_mm"])
    wid = wall["id"]
    if wall["kind"] == "exterior":
        if wid == "W-EXT-TOP":
            return (x1 - t, -t, x2 + t, 0.0)
        if wid == "W-EXT-RIGHT":
            return (x1, y1, x1 + t, y2 + t)
        if wid == "W-EXT-MAIN-BOT-R":
            return (x1, y1, x2 + t, y1 + t)
        if wid == "W-EXT-ENTRY-E":
            return (x1, y1, x1 + t, y2 + t)
        if wid == "W-EXT-FRONT-BOT":
            return (x1 - t, y1, x2 + t, y1 + t)
        if wid == "W-EXT-LEFT":
            return (x1 - t, y1 - t, x1, y2 + t)
    # Interior or external enclosure: centered on centerline
    half = t / 2.0
    if abs(x1 - x2) < 1e-6:
        return (x1 - half, min(y1, y2), x1 + half, max(y1, y2))
    return (min(x1, x2), y1 - half, max(x1, x2), y1 + half)


def door_sweep_samples(door: dict[str, Any]) -> list[tuple[float, float]]:
    """Sample points inside the 90-degree door leaf sweep sector for clearance auditing."""
    if not door.get("hinge") or door["swing_dir"] == "open_passage":
        return []
    hx, hy = float(door["hinge"][0]), float(door["hinge"][1])
    x1, y1, x2, y2 = float(door["x1"]), float(door["y1"]), float(door["x2"]), float(door["y2"])
    radius = float(door["width_mm"])
    sdir = door["swing_dir"]

    # Closed leaf angle from hinge toward latch
    dx = (x2 if abs(hx - x1) < 1e-3 else x1) - hx
    dy = (y2 if abs(hy - y1) < 1e-3 else y1) - hy
    if abs(hx - x1) < 1e-3 and abs(hy - y1) < 1e-3:
        dx, dy = x2 - hx, y2 - hy
    closed_ang = math.atan2(dy, dx)

    # Open leaf angle per swing_dir
    open_angles = {"+X": 0.0, "-X": math.pi, "+Y": math.pi / 2.0, "-Y": -math.pi / 2.0}
    open_ang = open_angles[sdir]
    # Shortest signed 90-degree delta
    delta = (open_ang - closed_ang + math.pi) % (2.0 * math.pi) - math.pi

    pts: list[tuple[float, float]] = []
    for ri in range(2, 11):
        r = radius * (ri / 10.0)
        for ai in range(1, 18):
            ang = closed_ang + delta * (ai / 18.0)
            pts.append((hx + r * math.cos(ang), hy + r * math.sin(ang)))
    return pts


def run_validation() -> int:
    with SPEC_PATH.open("r", encoding="utf-8") as f:
        spec = json.load(f)

    rooms_by_id = {r["id"]: r for r in spec["rooms"]}
    items = spec["stations_and_equipment"]
    items_by_id = {i["id"]: i for i in items}
    conveyors = spec["conveyors"]
    walls = spec["walls"]
    walls_by_id = {w["id"]: w for w in walls}
    doors = spec["doors"]
    shell = spec["shell"]

    hard_failures = 0
    advisories = 0

    print("=================================================================")
    print("PROJECT VOL - GEOMETRY, CLEARANCE & INVENTORY VALIDATION")
    print(f"Spec: {SPEC_PATH}")
    print("=================================================================")

    # 1. Static Floor-Standing Overlap Check
    floor_objects = [
        {"id": i["id"], "name": i["name"], "box": item_box(i), "room_id": i["room_id"]}
        for i in items
        if i["parent_id"] is None
    ] + [
        {"id": c["id"], "name": c["name"], "box": item_box(c), "room_id": c["room_id"]}
        for c in conveyors
    ]

    overlap_hits = []
    for idx_a in range(len(floor_objects)):
        for idx_b in range(idx_a + 1, len(floor_objects)):
            a, b = floor_objects[idx_a], floor_objects[idx_b]
            ox, oy = rect_overlap(a["box"], b["box"])
            if ox > 0 and oy > 0:
                overlap_hits.append((a["id"], b["id"], ox, oy))
    if overlap_hits:
        hard_failures += len(overlap_hits)
        print(f"[FAIL] 1. Static Floor-Standing Overlap Check: {len(overlap_hits)} overlap(s)")
        for a_id, b_id, ox, oy in overlap_hits:
            print(f"       - {a_id} vs {b_id}: {ox:.0f} x {oy:.0f} mm")
    else:
        print(f"[PASS] 1. Static Floor-Standing Overlap Check: 0 overlaps across {len(floor_objects)} objects")

    # 2. Benchtop Host Containment & Sibling Overlap Check
    children = [i for i in items if i["parent_id"] is not None]
    child_errors = []
    by_parent: dict[str, list[dict[str, Any]]] = {}
    for ch in children:
        pid = ch["parent_id"]
        if pid not in items_by_id:
            child_errors.append(f"{ch['id']} references unknown parent {pid}")
            continue
        parent = items_by_id[pid]
        if not rect_contains(item_box(parent), item_box(ch)):
            child_errors.append(f"{ch['id']} exceeds host {pid} footprint")
        by_parent.setdefault(pid, []).append(ch)
    for pid, group in by_parent.items():
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                ox, oy = rect_overlap(item_box(group[i]), item_box(group[j]))
                if ox > 0 and oy > 0:
                    child_errors.append(f"{group[i]['id']} overlaps sibling {group[j]['id']} on {pid} ({ox:.0f}x{oy:.0f} mm)")
    if child_errors:
        hard_failures += len(child_errors)
        print(f"[FAIL] 2. Benchtop Host Containment & Sibling Check: {len(child_errors)} issue(s)")
        for e in child_errors:
            print(f"       - {e}")
    else:
        print(f"[PASS] 2. Benchtop Host Containment & Sibling Check: {len(children)} mounted items cleanly contained")

    # 3. Room Containment Check
    room_errors = []
    for obj in floor_objects:
        rid = obj["room_id"]
        if rid not in rooms_by_id:
            room_errors.append(f"{obj['id']} references unknown room {rid}")
            continue
        rm = rooms_by_id[rid]
        rbox = item_box(rm)
        if not rect_contains(rbox, obj["box"]):
            room_errors.append(f"{obj['id']} extends outside room {rid}")
        excl = rm.get("exclude_subrect")
        if excl:
            ox, oy = rect_overlap(item_box(excl), obj["box"])
            if ox > 0 and oy > 0:
                room_errors.append(f"{obj['id']} intrudes into excluded subrect of {rid} ({ox:.0f}x{oy:.0f} mm)")
    if room_errors:
        hard_failures += len(room_errors)
        print(f"[FAIL] 3. Room Containment Check: {len(room_errors)} violation(s)")
        for e in room_errors:
            print(f"       - {e}")
    else:
        print(f"[PASS] 3. Room Containment Check: all {len(floor_objects)} objects strictly within assigned rooms")

    # 4. Building Shell & Room Tiling Check
    main_b = item_box(shell["main_building"])
    front_b = item_box(shell["front_extension"])
    ext_cold = item_box(shell["external_cold_storage"])
    shell_errors = []
    interior_rooms = [r for r in spec["rooms"] if r["id"] != "external_cold_storage"]
    for rm in interior_rooms:
        rb = item_box(rm)
        if not (rect_contains(main_b, rb) or rect_contains(front_b, rb)):
            shell_errors.append(f"Room {rm['id']} outside main_building/front_extension")
    for i in range(len(interior_rooms)):
        for j in range(i + 1, len(interior_rooms)):
            ra, rb = interior_rooms[i], interior_rooms[j]
            # main_hall explicitly excludes toilets subrect
            if {ra["id"], rb["id"]} == {"main_hall", "toilets"}:
                continue
            ox, oy = rect_overlap(item_box(ra), item_box(rb))
            if ox > 0 and oy > 0:
                shell_errors.append(f"Room {ra['id']} overlaps {rb['id']} ({ox:.0f}x{oy:.0f} mm)")
    if ext_cold[2] > 0:
        shell_errors.append(f"External Cold Storage X2={ext_cold[2]} must be <= 0")
    if shell_errors:
        hard_failures += len(shell_errors)
        print(f"[FAIL] 4. Building Shell & Room Tiling Check: {len(shell_errors)} violation(s)")
        for e in shell_errors:
            print(f"       - {e}")
    else:
        print(f"[PASS] 4. Building Shell & Room Tiling Check: {len(interior_rooms)} interior rooms + 1 external unit valid")

    # 5. Required Clear Aisles, Intervals & Flow Segregation Check
    aisle_errors = []
    soils_col3_max_x = max(i["x"] + i["w"] for i in items if i["category"] == "soils_station")
    waters_min_x = min(i["x"] for i in items if i["category"] == "waters_station")
    walkway_clear = waters_min_x - soils_col3_max_x
    if walkway_clear < 2400:
        aisle_errors.append(f"Central walkway clear width {walkway_clear} mm < 2400 mm")

    sul_outer = items_by_id["SUL-OUTER-BENCH"]
    sul_island = items_by_id["SUL-ISLAND"]
    sul_div = items_by_id["SUL-DIV-BENCH"]
    sul_left_aisle = sul_island["x"] - (sul_outer["x"] + sul_outer["w"])
    sul_right_aisle = sul_div["x"] - (sul_island["x"] + sul_island["w"])
    if sul_left_aisle != 1500 or sul_right_aisle != 1500:
        aisle_errors.append(f"Sulphide aisles L={sul_left_aisle} mm, R={sul_right_aisle} mm (expected 1500 mm each)")

    w_pcs = sorted([items_by_id[f"SUL-WPC-{k}"] for k in range(1, 5)], key=lambda d: d["y"])
    wpc_gaps = [w_pcs[k + 1]["y"] - (w_pcs[k]["y"] + w_pcs[k]["h"]) for k in range(3)]
    if any(g != 1500 for g in wpc_gaps):
        aisle_errors.append(f"Sulphide Wall PC gaps {wpc_gaps} (expected [1500, 1500, 1500])")

    soils_rows_y = sorted({i["y"] for i in items if i["category"] == "soils_station"})
    soil_gaps = [soils_rows_y[k + 1] - (soils_rows_y[k] + 600) for k in range(len(soils_rows_y) - 1)]
    if any(g != 1500 for g in soil_gaps):
        aisle_errors.append(f"Soils row movement gaps {soil_gaps} (expected 1500 mm each)")

    rack_a, rack_b = items_by_id["ONHOLD-RACK-A"], items_by_id["ONHOLD-RACK-B"]
    onhold_gap = rack_b["y"] - (rack_a["y"] + rack_a["h"])
    if onhold_gap != 600:
        aisle_errors.append(f"On-Hold walking path {onhold_gap} mm (expected 600 mm)")

    # Flow polylines cross-intersection test
    flows_by_stream = {f["stream"]: f["points"] for f in spec["flow_paths"]}
    waters_pts = flows_by_stream["waters"]
    soils_all = [flows_by_stream["soils"], flows_by_stream["soils_prep"]]
    flow_crossings = 0
    for i in range(len(waters_pts) - 1):
        w1, w2 = tuple(waters_pts[i]), tuple(waters_pts[i + 1])
        for s_pts in soils_all:
            for j in range(len(s_pts) - 1):
                if segments_intersect(w1, w2, tuple(s_pts[j]), tuple(s_pts[j + 1])):
                    flow_crossings += 1
                    aisle_errors.append(f"Waters flow crosses Soils flow between {w1}->{w2} and {s_pts[j]}->{s_pts[j+1]}")

    if aisle_errors:
        hard_failures += len(aisle_errors)
        print(f"[FAIL] 5. Aisles, Intervals & Flow Segregation Check: {len(aisle_errors)} issue(s)")
        for e in aisle_errors:
            print(f"       - {e}")
    else:
        print(
            "[PASS] 5. Aisles, Intervals & Flow Segregation Check: "
            f"Walkway={walkway_clear} mm, Sulphide Aisles={sul_left_aisle}/{sul_right_aisle} mm, "
            f"Wall PC Gaps={wpc_gaps[0]} mm, Soils Gaps={soil_gaps[0]} mm, On-Hold Path={onhold_gap} mm, "
            f"Flow Crossings={flow_crossings}"
        )

    # 6. Seated Chair Clearance Check
    chair_radius = 220.0
    chairs = [(i["id"], float(i["seat"]["x"]), float(i["seat"]["y"])) for i in items if i.get("seat")]
    wall_boxes = [(w["id"], wall_aabb(w, shell)) for w in walls]
    chair_errors = []
    for cid, cx, cy in chairs:
        for obj in floor_objects:
            if circle_intersects_rect(cx, cy, chair_radius, obj["box"]):
                chair_errors.append(f"Chair {cid} hits {obj['id']}")
        for wid, wb in wall_boxes:
            if circle_intersects_rect(cx, cy, chair_radius, wb):
                chair_errors.append(f"Chair {cid} hits wall {wid}")
    for i in range(len(chairs)):
        for j in range(i + 1, len(chairs)):
            c1, c2 = chairs[i], chairs[j]
            dist = math.hypot(c1[1] - c2[1], c1[2] - c2[2])
            if dist < 2.0 * chair_radius - 1e-6:
                chair_errors.append(f"Chair {c1[0]} overlaps chair {c2[0]} (dist={dist:.1f} mm)")
    if chair_errors:
        hard_failures += len(chair_errors)
        print(f"[FAIL] 6. Seated Chair Clearance Check: {len(chair_errors)} collision(s)")
        for e in chair_errors:
            print(f"       - {e}")
    else:
        print(f"[PASS] 6. Seated Chair Clearance Check: all {len(chairs)} analyst/office chairs clear of desks, walls & peers")

    # 7. Door Alignment & Swing Arc Audit
    door_align_errors = []
    door_advisories = []
    for d in doors:
        wid = d["wall_id"]
        if wid not in walls_by_id:
            door_align_errors.append(f"Door {d['id']} references unknown wall {wid}")
            continue
        w = walls_by_id[wid]
        wx_min, wx_max = min(w["x1"], w["x2"]), max(w["x1"], w["x2"])
        wy_min, wy_max = min(w["y1"], w["y2"]), max(w["y1"], w["y2"])
        if not (wx_min <= d["x1"] <= wx_max and wx_min <= d["x2"] <= wx_max and wy_min <= d["y1"] <= wy_max and wy_min <= d["y2"] <= wy_max):
            door_align_errors.append(f"Door {d['id']} outside wall {wid} bounds")
        samples = door_sweep_samples(d)
        hits = []
        for obj in floor_objects:
            bx1, by1, bx2, by2 = obj["box"]
            if any(bx1 < px < bx2 and by1 < py < by2 for px, py in samples):
                hits.append(obj["id"])
        if hits:
            door_advisories.append((d["id"], d["swing_dir"], hits, d.get("note", "")))

    if door_align_errors:
        hard_failures += len(door_align_errors)
        print(f"[FAIL] 7a. Door Wall Alignment Check: {len(door_align_errors)} error(s)")
        for e in door_align_errors:
            print(f"       - {e}")
    else:
        print(f"[PASS] 7a. Door Wall Alignment Check: all {len(doors)} doors/passages aligned on host walls")

    if door_advisories:
        advisories += len(door_advisories)
        print(f"[WARN] 7b. Door Swing Arc Audit: {len(doors) - len(door_advisories)} CLEAR, {len(door_advisories)} ADVISORY")
        for did, sdir, hits, note in door_advisories:
            print(f"       [ADVISORY] {did} (swing={sdir}) sweep contacts {', '.join(hits)} -- {note}")
    else:
        print(f"[PASS] 7b. Door Swing Arc Audit: all {len(doors)} door swings 100% clear")

    # 8. Specification Inventory Parity Check
    counts = {
        "waters_stations": sum(1 for i in items if i["category"] == "waters_station"),
        "soils_stations": sum(1 for i in items if i["category"] == "soils_station"),
        "sulphide_room_pcs": sum(1 for i in items if i["room_id"] == "sulphide_area" and i["category"] == "sulphide_pc"),
        "post_grind_scan_pcs": sum(1 for i in items if i["category"] == "sulphide_scan_pc"),
        "cs_office_dual_desks": sum(1 for i in items if i["category"] == "office_desk" and i["dual_monitor"]),
        "logistics_workstations": sum(1 for i in items if i["category"] == "logistics_station"),
        "logistics_shelf": sum(1 for i in items if i["id"] == "LOG-SHELF"),
        "fume_hoods": sum(1 for i in items if i["has_fume_hood"]),
        "conveyors": len(conveyors),
        "drying_ovens": sum(1 for i in items if i["category"] == "drying_oven"),
        "grinders": sum(1 for i in items if i["category"] == "grinder"),
        "onhold_racks": sum(1 for i in items if i["room_id"] == "on_hold_storage" and i["category"] == "storage_rack"),
        "onhold_fridges": sum(1 for i in items if i["category"] == "fridge"),
        "wc_cubicles": sum(1 for i in items if i["category"] == "wc_cubicle"),
        "total_pcs": sum(1 for i in items if i["has_pc"]),
        "total_label_printers": sum(1 for i in items if i["has_label_printer"]),
    }
    expected = {
        "waters_stations": 10,
        "soils_stations": 15,
        "sulphide_room_pcs": 8,
        "post_grind_scan_pcs": 1,
        "cs_office_dual_desks": 8,
        "logistics_workstations": 3,
        "logistics_shelf": 1,
        "fume_hoods": 3,
        "conveyors": 3,
        "drying_ovens": 2,
        "grinders": 2,
        "onhold_racks": 2,
        "onhold_fridges": 1,
        "wc_cubicles": 4,
        "total_pcs": 42,
        "total_label_printers": 23,
    }
    inv_mismatches = [f"{k}: got {counts[k]}, expected {expected[k]}" for k in expected if counts[k] != expected[k]]
    if inv_mismatches:
        hard_failures += len(inv_mismatches)
        print(f"[FAIL] 8. Specification Inventory Parity Check: {len(inv_mismatches)} mismatch(es)")
        for m in inv_mismatches:
            print(f"       - {m}")
    else:
        print(
            "[PASS] 8. Specification Inventory Parity Check: "
            f"Waters={counts['waters_stations']}, Soils={counts['soils_stations']}, "
            f"SulphidePCs={counts['sulphide_room_pcs']}+{counts['post_grind_scan_pcs']}scan, "
            f"CSDesks={counts['cs_office_dual_desks']}, FumeHoods={counts['fume_hoods']}, "
            f"Conveyors={counts['conveyors']}, TotalPCs={counts['total_pcs']}, "
            f"LabelPrinters={counts['total_label_printers']}"
        )

    print("=================================================================")
    print(f"SUMMARY: hard_failures={hard_failures}, advisories={advisories}")
    print("=================================================================")
    return 1 if hard_failures else 0


if __name__ == "__main__":
    sys.exit(run_validation())
