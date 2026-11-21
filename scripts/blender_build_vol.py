"""Standalone Blender Python script to build the Project Vol 3D scene and render Cycles stills/MP4.

Usage:
    blender --background --python scripts/blender_build_vol.py -- --render-stills
    blender --background --python scripts/blender_build_vol.py -- --render-video
    blender --background --python scripts/blender_build_vol.py -- --save-blend --samples 128
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

import bpy
from mathutils import Vector


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent
SPEC_PATH = ROOT_DIR / "data" / "layout_spec.json"
OUT_STILLS_DIR = ROOT_DIR / "outputs" / "blender_stills"
OUT_VIDEO_PATH = ROOT_DIR / "outputs" / "Project_Vol_Blender_Tour.mp4"
OUT_BLEND_PATH = ROOT_DIR / "outputs" / "Project_Vol.blend"


def mm(val: float) -> float:
    return float(val) / 1000.0


def to_blender_xyz(x_mm: float, y_mm: float, z_mm: float = 0.0) -> tuple[float, float, float]:
    """Convert layout_spec mm (X right, Y down, Z up) into Blender meters (X right, Y north, Z up)."""
    return (mm(x_mm), -mm(y_mm), mm(z_mm))


def hex_to_rgba(hex_str: str, alpha: float = 1.0) -> tuple[float, float, float, float]:
    h = hex_str.lstrip("#")
    r, g, b = (int(h[i : i + 2], 16) / 255.0 for i in (0, 2, 4))
    # Convert sRGB to approximate linear for Principled BSDF
    return (r ** 2.2, g ** 2.2, b ** 2.2, alpha)


def make_material(name: str, hex_col: str, roughness: float = 0.55, metallic: float = 0.0, transmission: float = 0.0, emission: float = 0.0) -> bpy.types.Material:
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name=name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    rgba = hex_to_rgba(hex_col)
    bsdf.inputs["Base Color"].default_value = rgba
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    if "Transmission Weight" in bsdf.inputs:
        bsdf.inputs["Transmission Weight"].default_value = transmission
    elif "Transmission" in bsdf.inputs:
        bsdf.inputs["Transmission"].default_value = transmission
    if emission > 0.0:
        if "Emission Color" in bsdf.inputs:
            bsdf.inputs["Emission Color"].default_value = rgba
        if "Emission Strength" in bsdf.inputs:
            bsdf.inputs["Emission Strength"].default_value = emission
    return mat


def add_box(
    collection: bpy.types.Collection,
    name: str,
    x1_mm: float,
    y1_mm: float,
    z1_mm: float,
    x2_mm: float,
    y2_mm: float,
    z2_mm: float,
    mat: bpy.types.Material,
) -> bpy.types.Object:
    cx = (x1_mm + x2_mm) / 2.0
    cy = (y1_mm + y2_mm) / 2.0
    cz = (z1_mm + z2_mm) / 2.0
    sx = max(1.0, abs(x2_mm - x1_mm))
    sy = max(1.0, abs(y2_mm - y1_mm))
    sz = max(1.0, abs(z2_mm - z1_mm))

    bpy.ops.mesh.primitive_cube_add(size=1.0, location=to_blender_xyz(cx, cy, cz))
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = (mm(sx), mm(sy), mm(sz))
    obj.data.materials.append(mat)
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    collection.objects.link(obj)
    return obj


def split_wall_intervals(wall: dict[str, Any], doors: list[dict[str, Any]]) -> list[tuple[float, float, float, float]]:
    x1, y1, x2, y2 = float(wall["x1"]), float(wall["y1"]), float(wall["x2"]), float(wall["y2"])
    vertical = abs(x1 - x2) < 1e-6
    w_doors = [d for d in doors if d.get("wall_id") == wall["id"]]
    if not w_doors:
        return [(x1, y1, x2, y2)]
    if vertical:
        lo, hi = min(y1, y2), max(y1, y2)
        cuts = sorted((min(d["y1"], d["y2"]), max(d["y1"], d["y2"])) for d in w_doors)
        segs, cur = [], lo
        for a, b in cuts:
            if a > cur + 1:
                segs.append((x1, cur, x1, a))
            cur = max(cur, b)
        if cur < hi - 1:
            segs.append((x1, cur, x1, hi))
        return segs
    lo, hi = min(x1, x2), max(x1, x2)
    cuts = sorted((min(d["x1"], d["x2"]), max(d["x1"], d["x2"])) for d in w_doors)
    segs, cur = [], lo
    for a, b in cuts:
        if a > cur + 1:
            segs.append((cur, y1, a, y1))
        cur = max(cur, b)
    if cur < hi - 1:
        segs.append((cur, y1, hi, y1))
    return segs


def clear_scene() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)


def create_collection(name: str) -> bpy.types.Collection:
    col = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(col)
    return col


def build_blender_scene(spec: dict[str, Any]) -> None:
    clear_scene()
    pal = spec["meta"]["palette"]["physical"]

    mats = {
        "wall": make_material("Wall_Pure_White", pal["wall_white"], roughness=0.65),
        "ceiling": make_material("Ceiling_White", pal["ceiling_white"], roughness=0.75),
        "led": make_material("Ceiling_LED_Panel", "#FFFFFF", roughness=0.2, emission=7.5),
        "floor": make_material("Floor_Epoxy_Grey", pal["floor_epoxy"], roughness=0.35),
        "stripe": make_material("Floor_Striping_Charcoal", pal["floor_striping"], roughness=0.45),
        "cabinet": make_material("Cabinet_White", pal["cabinet_white"], roughness=0.45),
        "worktop": make_material("Worktop_Warm_Grey", pal["worktop_warm_grey"], roughness=0.38),
        "steel": make_material("Brushed_Stainless", pal["stainless_steel"], roughness=0.28, metallic=0.88),
        "chair": make_material("Charcoal_Ergonomic", pal["chair_charcoal"], roughness=0.55),
        "glass": make_material("Frosted_Glass", pal["glass_tint"], roughness=0.14, transmission=0.78),
        "monitor": make_material("Monitor_Matte_Slate", "#1E293B", roughness=0.30),
        "tray_dry": make_material("Tray_Dry_LightGrey", "#CBD5E1", roughness=0.45),
        "tray_wet": make_material("Tray_Wet_MidGrey", "#64748B", roughness=0.40),
    }

    col_arch = create_collection("01_Architecture")
    col_conv = create_collection("02_Conveyors")
    col_equip = create_collection("03_Workstations_Equipment")
    col_cams = create_collection("04_Cameras_Lights")

    # Floor & External Cold Storage
    mb = spec["shell"]["main_building"]
    fe = spec["shell"]["front_extension"]
    ec = spec["shell"]["external_cold_storage"]
    ceil_h = float(spec["meta"]["coordinate_system"]["ceiling_height_mm"])

    add_box(col_arch, "Floor_Main", mb["x"], mb["y"], -120, mb["x"] + mb["w"], mb["y"] + mb["h"], 0, mats["floor"])
    add_box(col_arch, "Floor_FrontExt", fe["x"], fe["y"], -120, fe["x"] + fe["w"], fe["y"] + fe["h"], 0, mats["floor"])
    add_box(col_arch, "External_Cold_Storage", ec["x"], ec["y"], 0, ec["x"] + ec["w"], ec["y"] + ec["h"], 2800, mats["cabinet"])

    # Zone floor striping
    for zn in spec["zones"]:
        add_box(col_arch, f"Zone_{zn['id']}", zn["x"], zn["y"], 1, zn["x"] + zn["w"], zn["y"] + zn["h"], 6, mats["stripe"])

    # Recessed LED ceiling panels (placed at ceiling height, hidden or above cutaway)
    for lx in range(1500, 17500, 3200):
        for ly in range(2000, 17000, 3600):
            add_box(col_arch, f"LED_{lx}_{ly}", lx - 600, ly - 150, ceil_h - 40, lx + 600, ly + 150, ceil_h, mats["led"])

    # Walls with door openings + door header lintels
    for wall in spec["walls"]:
        if wall["kind"] == "external_enclosure":
            continue
        t = float(wall["thickness_mm"])
        half = t / 2.0
        wh = float(wall["height_mm"])
        mat = mats["glass"] if wall["kind"] == "glazed_partition" else mats["wall"]
        segs = split_wall_intervals(wall, spec["doors"])
        for idx, (sx1, sy1, sx2, sy2) in enumerate(segs):
            if abs(sx1 - sx2) < 1e-3:
                add_box(col_arch, f"{wall['id']}_{idx}", sx1 - half, min(sy1, sy2), 0, sx1 + half, max(sy1, sy2), wh, mat)
            else:
                add_box(col_arch, f"{wall['id']}_{idx}", min(sx1, sx2), sy1 - half, 0, max(sx1, sx2), sy1 + half, wh, mat)

        # Lintel above doors
        for d in [dr for dr in spec["doors"] if dr.get("wall_id") == wall["id"]]:
            dh = float(d["height_mm"])
            if abs(d["x1"] - d["x2"]) < 1e-3:
                add_box(col_arch, f"Lintel_{d['id']}", d["x1"] - half, min(d["y1"], d["y2"]), dh, d["x1"] + half, max(d["y1"], d["y2"]), wh, mat)
            else:
                add_box(col_arch, f"Lintel_{d['id']}", min(d["x1"], d["x2"]), d["y1"] - half, dh, max(d["x1"], d["x2"]), d["y1"] + half, wh, mat)

    # Door leaves
    for d in spec["doors"]:
        if not d.get("hinge") or d["swing_dir"] == "open_passage":
            continue
        hx, hy = float(d["hinge"][0]), float(d["hinge"][1])
        w = float(d["width_mm"])
        dh = float(d["height_mm"])
        sd = d["swing_dir"]
        if sd == "+X":
            add_box(col_arch, f"Leaf_{d['id']}", hx, hy - 22, 0, hx + w, hy + 22, dh, mats["wall"])
        elif sd == "-X":
            add_box(col_arch, f"Leaf_{d['id']}", hx - w, hy - 22, 0, hx, hy + 22, dh, mats["wall"])
        elif sd == "+Y":
            add_box(col_arch, f"Leaf_{d['id']}", hx - 22, hy, 0, hx + 22, hy + w, dh, mats["wall"])
        elif sd == "-Y":
            add_box(col_arch, f"Leaf_{d['id']}", hx - 22, hy - w, 0, hx + 22, hy, dh, mats["wall"])

    # Roller Conveyors + Cylindrical Rollers + Trays
    for conv in spec["conveyors"]:
        cx, cy, cw, ch = float(conv["x"]), float(conv["y"]), float(conv["w"]), float(conv["h"])
        for leg_y in (cy + 120, cy + ch - 120):
            add_box(col_conv, f"{conv['id']}_LegL_{int(leg_y)}", cx + 20, leg_y - 30, 0, cx + 70, leg_y + 30, 920, mats["steel"])
            add_box(col_conv, f"{conv['id']}_LegR_{int(leg_y)}", cx + cw - 70, leg_y - 30, 0, cx + cw - 20, leg_y + 30, 920, mats["steel"])
        for d_idx, deck in enumerate(conv["decks"]):
            z = float(deck["z_mm"])
            add_box(col_conv, f"{conv['id']}_FrameL_{d_idx}", cx, cy, z - 60, cx + 45, cy + ch, z, mats["steel"])
            add_box(col_conv, f"{conv['id']}_FrameR_{d_idx}", cx + cw - 45, cy, z - 60, cx + cw, cy + ch, z, mats["steel"])
            add_box(col_conv, f"{conv['id']}_Bed_{d_idx}", cx + 45, cy, z - 45, cx + cw - 45, cy + ch, z - 10, mats["steel"])
            t_mat = mats["tray_dry"] if deck["stream"] == "soils_dry" else mats["tray_wet"]
            for ty in range(int(cy + 600), int(cy + ch - 700), 1800):
                add_box(col_conv, f"{conv['id']}_Tray_{d_idx}_{ty}", cx + 110, ty, z, cx + cw - 110, ty + 420, z + 110, t_mat)

    # Stations & Equipment
    for it in spec["stations_and_equipment"]:
        x, y, w, h = float(it["x"]), float(it["y"]), float(it["w"]), float(it["h"])
        z0 = float(it["elev_mm"])
        z1 = z0 + float(it["height_mm"])
        cat = it["category"]

        if cat in ("bench", "island_bench", "waters_station", "soils_station", "logistics_station", "sulphide_scan_pc", "office_desk", "dining_table", "kitchenette", "wash_alcove"):
            if z1 - z0 > 120:
                add_box(col_equip, f"{it['id']}_Base", x + 20, y + 20, z0, x + w - 20, y + h - 20, z1 - 45, mats["cabinet"])
            add_box(col_equip, f"{it['id']}_Top", x, y, z1 - 45, x + w, y + h, z1, mats["worktop"])
        elif cat in ("fume_hood", "benchtop_fume_hood"):
            add_box(col_equip, f"{it['id']}_Base", x, y, z0, x + w, y + h, z0 + 180, mats["cabinet"])
            add_box(col_equip, f"{it['id']}_Glass", x + 15, y + 15, z0 + 180, x + w - 15, y + h - 15, z1 - 100, mats["glass"])
            add_box(col_equip, f"{it['id']}_Plenum", x, y, z1 - 100, x + w, y + h, z1, mats["worktop"])
        elif cat in ("drying_oven", "grinder", "fridge"):
            add_box(col_equip, f"{it['id']}_Body", x, y, z0, x + w, y + h, z1, mats["steel"])
        elif cat == "storage_rack":
            tiers = int(it.get("tiers", 5))
            step = (z1 - 150) / max(1, tiers - 1)
            for t_idx in range(tiers):
                sz = 120 + t_idx * step
                add_box(col_equip, f"{it['id']}_Tier_{t_idx}", x, y, sz, x + w, y + h, sz + 35, mats["worktop"])
        elif cat == "wc_cubicle":
            add_box(col_equip, f"{it['id']}_Cubicle", x, y, z0, x + w, y + h, z1, mats["wall"])
        elif cat in ("shaker", "sink", "toc_station", "sulphide_pc"):
            add_box(col_equip, f"{it['id']}_Unit", x + 30, y + 30, z0, x + w - 30, y + h - 30, z0 + 220, mats["steel"] if cat == "sink" else mats["cabinet"])

        if it["has_pc"]:
            cx, cy = x + w / 2.0, y + h / 2.0
            if it["dual_monitor"]:
                add_box(col_equip, f"{it['id']}_MonL", cx - 540, cy - 60, z1 + 120, cx - 40, cy - 20, z1 + 440, mats["monitor"])
                add_box(col_equip, f"{it['id']}_MonR", cx + 40, cy - 60, z1 + 120, cx + 540, cy - 20, z1 + 440, mats["monitor"])
            else:
                mw, mh = (45, 420) if h > w and cat == "waters_station" else (420, 45)
                add_box(col_equip, f"{it['id']}_Mon", cx - mw / 2, cy - mh / 2, z1 + 100, cx + mw / 2, cy + mh / 2, z1 + 400, mats["monitor"])
        if it["has_label_printer"]:
            add_box(col_equip, f"{it['id']}_Prt", x + 80, y + 80, z1, x + 260, y + 260, z1 + 170, mats["steel"])
        if it.get("seat"):
            sx, sy = float(it["seat"]["x"]), float(it["seat"]["y"])
            add_box(col_equip, f"{it['id']}_ChairSeat", sx - 200, sy - 200, 420, sx + 200, sy + 200, 470, mats["chair"])
            add_box(col_equip, f"{it['id']}_ChairBase", sx - 60, sy - 60, 0, sx + 60, sy + 60, 420, mats["steel"])

    # Studio Lighting
    bpy.ops.object.light_add(type="SUN", location=(8.0, -8.0, 14.0))
    sun = bpy.context.active_object
    sun.data.energy = 3.2
    sun.rotation_euler = (math.radians(32), math.radians(18), math.radians(-24))
    for c in list(sun.users_collection):
        c.objects.unlink(sun)
    col_cams.objects.link(sun)

    # World background: clean daylight studio white
    world = bpy.data.worlds.new("Studio_White")
    bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs["Color"].default_value = (0.95, 0.96, 0.98, 1.0)
        bg.inputs["Strength"].default_value = 0.85

    # Build 8 named chapter cameras
    for ch in spec["tour_chapters"]:
        cam_data = bpy.data.cameras.new(f"Cam_View_{ch['id']:02d}")
        cam_data.lens = 24.0
        cam_obj = bpy.data.objects.new(f"Cam_View_{ch['id']:02d}", cam_data)
        col_cams.objects.link(cam_obj)
        cam_pos = Vector(to_blender_xyz(*ch["camera_mm"]))
        tgt_pos = Vector(to_blender_xyz(*ch["target_mm"]))
        cam_obj.location = cam_pos
        direction = tgt_pos - cam_pos
        cam_obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def configure_cycles(samples: int) -> None:
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.image_settings.file_format = "PNG"


def main() -> None:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(description="Build & render Project Vol in Blender Cycles.")
    parser.add_argument("--render-stills", action="store_true", help="Batch-render all 8 architectural stills")
    parser.add_argument("--render-video", action="store_true", help="Render animated MP4 walkthrough")
    parser.add_argument("--save-blend", action="store_true", help="Save Project_Vol.blend")
    parser.add_argument("--samples", type=int, default=64, help="Cycles samples per frame")
    args = parser.parse_args(argv)

    with SPEC_PATH.open("r", encoding="utf-8") as f:
        spec = json.load(f)

    build_blender_scene(spec)
    configure_cycles(args.samples)

    if args.save_blend:
        OUT_BLEND_PATH.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(OUT_BLEND_PATH))
        print(f"Saved Blend scene: {OUT_BLEND_PATH}")

    if args.render_stills:
        OUT_STILLS_DIR.mkdir(parents=True, exist_ok=True)
        for ch in spec["tour_chapters"]:
            cam = bpy.data.objects[f"Cam_View_{ch['id']:02d}"]
            bpy.context.scene.camera = cam
            bpy.context.scene.render.filepath = str(OUT_STILLS_DIR / f"view_{ch['id']:02d}.png")
            bpy.ops.render.render(write_still=True)

    if args.render_video:
        scene = bpy.context.scene
        cam = bpy.data.objects["Cam_View_01"]
        scene.camera = cam
        scene.frame_start = 1
        fps = 24
        scene.render.fps = fps
        cur_f = 1
        for ch in spec["tour_chapters"]:
            cam_pos = Vector(to_blender_xyz(*ch["camera_mm"]))
            tgt_pos = Vector(to_blender_xyz(*ch["target_mm"]))
            cam.location = cam_pos
            cam.rotation_euler = (tgt_pos - cam_pos).to_track_quat("-Z", "Y").to_euler()
            cam.keyframe_insert(data_path="location", frame=cur_f)
            cam.keyframe_insert(data_path="rotation_euler", frame=cur_f)
            cur_f += int(ch["duration_sec"] * fps)
        scene.frame_end = cur_f
        scene.render.image_settings.file_format = "FFMPEG"
        scene.render.ffmpeg.format = "MPEG4"
        scene.render.ffmpeg.codec = "H264"
        scene.render.filepath = str(OUT_VIDEO_PATH)
        bpy.ops.render.render(animation=True)


if __name__ == "__main__":
    main()
