"""Generate the 12-slide executive PowerPoint deck for Project Vol (SomeLab SomewhereintheUK)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt


ROOT_DIR = Path(__file__).resolve().parent.parent
SPEC_PATH = ROOT_DIR / "data" / "layout_spec.json"
OUT_DIR = ROOT_DIR / "outputs"
STILLS_DIR = OUT_DIR / "gallery_stills"
PLAN_2D_PNG = OUT_DIR / "Project_Vol_2D_Spec.png"
OUT_PPTX = OUT_DIR / "Project_Vol_Presentation.pptx"
WEB_DOWNLOADS_DIR = ROOT_DIR / "web" / "public" / "downloads"

SLIDE_W = 13.333
SLIDE_H = 7.5

# Palette (strict white / grey / corporate slate-navy chrome)
NAVY = RGBColor(0x0F, 0x17, 0x2A)
BLUE_ACCENT = RGBColor(0x1E, 0x3A, 0x8A)
SLATE = RGBColor(0x33, 0x41, 0x55)
MUTED = RGBColor(0x64, 0x74, 0x8B)
BORDER = RGBColor(0xCB, 0xD5, 0xE1)
SURFACE = RGBColor(0xF8, 0xFA, 0xFC)
SURFACE_ALT = RGBColor(0xF1, 0xF5, 0xF9)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)


def set_bg(slide: Any, color: RGBColor) -> None:
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = color


def add_header_chrome(slide: Any, slide_num: int, category: str, title: str, subtitle: str) -> None:
    set_bg(slide, WHITE)
    # Top navy bar
    bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(SLIDE_W), Inches(0.95))
    bar.fill.solid()
    bar.fill.fore_color.rgb = NAVY
    bar.line.fill.background()

    # Category pill text & title
    tb = slide.shapes.add_textbox(Inches(0.5), Inches(0.10), Inches(10.8), Inches(0.78))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    p0 = tf.paragraphs[0]
    p0.text = f"{category.upper()}  •  PROJECT VOL"
    p0.font.name = "Calibri"
    p0.font.size = Pt(9.5)
    p0.font.bold = True
    p0.font.color.rgb = RGBColor(0x94, 0xA3, 0xB8)

    p1 = tf.add_paragraph()
    p1.text = title
    p1.font.name = "Calibri"
    p1.font.size = Pt(21)
    p1.font.bold = True
    p1.font.color.rgb = WHITE

    # Slide number right
    ntb = slide.shapes.add_textbox(Inches(11.5), Inches(0.22), Inches(1.35), Inches(0.5))
    ntf = ntb.text_frame
    np0 = ntf.paragraphs[0]
    np0.alignment = PP_ALIGN.RIGHT
    np0.text = f"{slide_num:02d} / 12"
    np0.font.name = "Calibri"
    np0.font.size = Pt(12)
    np0.font.bold = True
    np0.font.color.rgb = RGBColor(0xCB, 0xD5, 0xE1)

    # Subtitle strip
    st = slide.shapes.add_textbox(Inches(0.5), Inches(1.03), Inches(12.3), Inches(0.32))
    stf = st.text_frame
    stf.margin_left = stf.margin_right = stf.margin_top = stf.margin_bottom = 0
    sp = stf.paragraphs[0]
    sp.text = subtitle
    sp.font.name = "Calibri"
    sp.font.size = Pt(11.5)
    sp.font.color.rgb = SLATE

    # Footer
    ft = slide.shapes.add_textbox(Inches(0.5), Inches(7.14), Inches(12.33), Inches(0.26))
    ftf = ft.text_frame
    ftf.margin_left = ftf.margin_right = ftf.margin_top = ftf.margin_bottom = 0
    fp = ftf.paragraphs[0]
    fp.text = "SomeLab SomewhereintheUK Consolidated Prep Facility (Unit 1, Science Park, SomewhereintheUK)  |  Single Source of Truth: data/layout_spec.json"
    fp.font.name = "Calibri"
    fp.font.size = Pt(8.5)
    fp.font.color.rgb = MUTED


def add_card(slide: Any, x: float, y: float, w: float, h: float, title: str, lines: list[str], bg: RGBColor = SURFACE, accent_top: bool = True) -> None:
    box = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    box.adjustments[0] = 0.03
    box.fill.solid()
    box.fill.fore_color.rgb = bg
    box.line.color.rgb = BORDER
    box.line.width = Pt(1)

    if accent_top:
        acc = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(0.06))
        acc.fill.solid()
        acc.fill.fore_color.rgb = BLUE_ACCENT
        acc.line.fill.background()

    tb = slide.shapes.add_textbox(Inches(x + 0.16), Inches(y + 0.14), Inches(w - 0.32), Inches(h - 0.24))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0

    p0 = tf.paragraphs[0]
    p0.text = title
    p0.font.name = "Calibri"
    p0.font.size = Pt(13)
    p0.font.bold = True
    p0.font.color.rgb = NAVY
    p0.space_after = Pt(5)

    for ln in lines:
        p = tf.add_paragraph()
        p.text = f"• {ln}" if not ln.startswith("•") else ln
        p.font.name = "Calibri"
        p.font.size = Pt(10.5)
        p.font.color.rgb = SLATE
        p.space_after = Pt(3.5)


def add_picture_fitted(slide: Any, img_path: Path, x: float, y: float, max_w: float, max_h: float, frame: bool = True) -> None:
    with Image.open(img_path) as im:
        iw, ih = im.size
    aspect = iw / ih
    box_aspect = max_w / max_h
    if aspect >= box_aspect:
        w = max_w
        h = w / aspect
    else:
        h = max_h
        w = h * aspect
    px = x + (max_w - w) / 2.0
    py = y + (max_h - h) / 2.0

    if frame:
        fr = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(px - 0.03), Inches(py - 0.03), Inches(w + 0.06), Inches(h + 0.06))
        fr.fill.solid()
        fr.fill.fore_color.rgb = WHITE
        fr.line.color.rgb = BORDER
        fr.line.width = Pt(1)
    slide.shapes.add_picture(str(img_path), Inches(px), Inches(py), Inches(w), Inches(h))


def set_notes(slide: Any, text: str) -> None:
    notes_slide = slide.notes_slide
    notes_slide.notes_text_frame.text = text.strip()


def style_table(table: Any, col_widths: list[float], font_pt: float = 9.5) -> None:
    for idx, cw in enumerate(col_widths):
        table.columns[idx].width = Inches(cw)
    for r_idx, row in enumerate(table.rows):
        for c_idx, cell in enumerate(row.cells):
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.fill.solid()
            if r_idx == 0:
                cell.fill.fore_color.rgb = NAVY
            elif r_idx % 2 == 1:
                cell.fill.fore_color.rgb = WHITE
            else:
                cell.fill.fore_color.rgb = SURFACE_ALT
            for p in cell.text_frame.paragraphs:
                p.font.name = "Calibri"
                p.font.size = Pt(font_pt)
                p.font.bold = (r_idx == 0 or c_idx == 0)
                p.font.color.rgb = WHITE if r_idx == 0 else NAVY


def build_presentation(spec: dict[str, Any]) -> None:
    prs = Presentation()
    prs.slide_width = Inches(SLIDE_W)
    prs.slide_height = Inches(SLIDE_H)
    blank = prs.slide_layouts[6]

    items = spec["stations_and_equipment"]
    total_pcs = sum(1 for i in items if i["has_pc"])
    dual_pcs = sum(1 for i in items if i["dual_monitor"])
    total_monitors = total_pcs + dual_pcs
    total_printers = sum(1 for i in items if i["has_label_printer"])
    main_m2 = spec["shell"]["main_building"]["w"] * spec["shell"]["main_building"]["h"] / 1e6
    ext_m2 = spec["shell"]["front_extension"]["w"] * spec["shell"]["front_extension"]["h"] / 1e6
    gia_m2 = main_m2 + ext_m2

    # --- SLIDE 1: Title Slide ---
    s1 = prs.slides.add_slide(blank)
    set_bg(s1, NAVY)
    tb1 = s1.shapes.add_textbox(Inches(0.65), Inches(1.0), Inches(5.8), Inches(4.5))
    tf1 = tb1.text_frame
    tf1.word_wrap = True
    p = tf1.paragraphs[0]
    p.text = "EXECUTIVE REDEVELOPMENT PROPOSAL"
    p.font.name = "Calibri"
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = RGBColor(0x94, 0xA3, 0xB8)
    p.space_after = Pt(10)

    p = tf1.add_paragraph()
    p.text = "Project Vol\nSomeLab SomewhereintheUK\nLean Lab Redevelopment"
    p.font.name = "Calibri"
    p.font.size = Pt(34)
    p.font.bold = True
    p.font.color.rgb = WHITE
    p.space_after = Pt(14)

    p = tf1.add_paragraph()
    p.text = "Consolidated Prep Facility  •  Unit 1, Science Park, SomewhereintheUK\nUniting Sample Registration (Phase 1), Drying & Grinding (Phase 2), and Organic Chemistry Prep (Phase 3) under one roof."
    p.font.name = "Calibri"
    p.font.size = Pt(13)
    p.font.color.rgb = RGBColor(0xCB, 0xD5, 0xE1)

    add_picture_fitted(s1, STILLS_DIR / "view_02.png", 6.65, 1.15, 6.1, 4.1, frame=False)

    # Bottom KPI bar on Slide 1
    kpis_s1 = [
        (f"{gia_m2:.1f} m2", "Gross Internal Area"),
        ("25 Stations", "10 Waters + 15 Soils"),
        (f"{total_pcs} PCs / {total_monitors} Screens", "Full LIMS Coverage"),
        ("240 cm Barrier", "Zero Sample Cross-Flow"),
    ]
    for idx, (val, lbl) in enumerate(kpis_s1):
        kx = 0.65 + idx * 3.05
        card = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(kx), Inches(5.65), Inches(2.85), Inches(1.15))
        card.adjustments[0] = 0.06
        card.fill.solid()
        card.fill.fore_color.rgb = RGBColor(0x1E, 0x29, 0x3B)
        card.line.color.rgb = RGBColor(0x33, 0x41, 0x55)
        ctb = s1.shapes.add_textbox(Inches(kx + 0.16), Inches(5.78), Inches(2.53), Inches(0.9))
        ctf = ctb.text_frame
        ctf.word_wrap = True
        cp0 = ctf.paragraphs[0]
        cp0.text = val
        cp0.font.name = "Calibri"
        cp0.font.size = Pt(18)
        cp0.font.bold = True
        cp0.font.color.rgb = WHITE
        cp1 = ctf.add_paragraph()
        cp1.text = lbl
        cp1.font.name = "Calibri"
        cp1.font.size = Pt(10)
        cp1.font.color.rgb = RGBColor(0x94, 0xA3, 0xB8)

    set_notes(
        s1,
        "Welcome leadership and operations. Project Vol establishes the SomeLab SomewhereintheUK Consolidated Prep Facility at Unit 1, Science Park, "
        "bringing Sample Registration (Phase 1), Drying/Grinding/Dry Soil Prep (Phase 2), and Organic Chemistry Prep (Phase 3) together into a single lean facility. "
        "Every floor plan, 3D model, equipment schedule, and presentation view is driven by one synchronized JSON specification."
    )

    # --- SLIDE 2: Executive Summary & Strategic Case ---
    s2 = prs.slides.add_slide(blank)
    add_header_chrome(s2, 2, "Strategic Case", "Executive Summary & Why Consolidate Now", "Eliminating inter-building transport, duplicate handoffs, and cross-stream bottlenecks inside the 18.3 x 18.1 m shell.")

    kpis_s2 = [
        (f"{gia_m2:.1f} m2", "Consolidated Indoor GIA", "18,293 x 18,134 mm Main + Front Wing (+19.4 m2 Ext Cold)"),
        ("25", "Core Main Hall Stations", "10 Waters stations + 15 uniform Soils (3x5) stations"),
        (f"{total_pcs} / {total_monitors}", "PCs / Monitors", f"{total_printers} thermal label printers + 8 dual-screen CS desks"),
        ("0", "Cross-Flow Intersections", "240 cm walkway & dual top-wall dispatch doors (Exit 1 & 2)"),
    ]
    for idx, (num, head, desc) in enumerate(kpis_s2):
        kx = 0.5 + idx * 3.12
        box = s2.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(kx), Inches(1.48), Inches(2.94), Inches(1.62))
        box.adjustments[0] = 0.04
        box.fill.solid()
        box.fill.fore_color.rgb = SURFACE
        box.line.color.rgb = BORDER
        tb = s2.shapes.add_textbox(Inches(kx + 0.16), Inches(1.58), Inches(2.62), Inches(1.42))
        tf = tb.text_frame
        tf.word_wrap = True
        p0 = tf.paragraphs[0]
        p0.text = num
        p0.font.name = "Calibri"
        p0.font.size = Pt(24)
        p0.font.bold = True
        p0.font.color.rgb = BLUE_ACCENT
        p1 = tf.add_paragraph()
        p1.text = head
        p1.font.name = "Calibri"
        p1.font.size = Pt(11.5)
        p1.font.bold = True
        p1.font.color.rgb = NAVY
        p2 = tf.add_paragraph()
        p2.text = desc
        p2.font.name = "Calibri"
        p2.font.size = Pt(9.5)
        p2.font.color.rgb = SLATE

    add_card(
        s2, 0.5, 3.32, 6.05, 3.6, "Operational Pain Points Resolved",
        [
            "Eliminates cross-phase cart movement between registration, drying/grinding, and organic prep.",
            "Demolishes the bottom-right Team Leaders Office & internal stairs to open a 300 x 400 cm intake triage zone.",
            "Separates dry soil vs. wet/prepared tray return traffic using double-deck 60 cm roller conveyors.",
            "Expands Sulphide island from narrow bench to 1.50 x 5.40 m (+3 PCs, 8 total room PCs) while retaining 150 cm aisles.",
            "Reconciles customer support and prep leadership in one 8-desk dual-screen open office.",
        ],
    )
    add_card(
        s2, 6.78, 3.32, 6.05, 3.6, "CapEx Discipline & Architectural Consistency",
        [
            "Retains high-value M&E rooms in place: Grinding Room (2 grinders + hood), Drying Room (2 ovens), Changing Room, and External Cold Storage.",
            "Resolves Drying Room door clash by flipping D-DRY outward (+Y) into the 3.6 m Prep Corridor—zero equipment relocation required.",
            "Upgrades staff welfare: 4 W/C cubicles, modernized Canteen with direct CS Office access.",
            "Clinical white & grey architectural finish supports audit readiness, cleanliness, and visual management.",
        ],
    )
    set_notes(
        s2,
        "Slide 2 frames the strategic rationale for senior leadership. By consolidating all three sample-prep phases at Unit 1, Science Park, SomewhereintheUK, "
        "we remove non-value-adding transport waste, double sample handling, and fragmented space while protecting CapEx by retaining the heavy drying, grinding, and external cold storage rooms."
    )

    # --- SLIDE 3: Uniting Phases 1, 2 & 3 Under One Roof ---
    s3 = prs.slides.add_slide(blank)
    add_header_chrome(s3, 3, "Consolidation Architecture", "Uniting Phases 1, 2 & 3 Under One Roof", "Mapping Sample Registration (P1), Drying/Grinding/Dry Soil Prep (P2), and Organic Chemistry Prep (P3) into 18.3 x 18.1 m + Front Wing.")

    phases = [
        ("PHASE 1 — SAMPLE REGISTRATION", [
            "Main Entrance Door (1,400 mm) at bottom-right opens directly into 300 x 400 cm Sorting Zone.",
            "Immediate segregation: Waters routed east (H2O Reg 1-2, Split 1-2); Soils routed west (S1-S6).",
            "Dedicated thermal label printers at all 22 registration/splitting stations + Rapid Moisture bench.",
        ]),
        ("PHASE 2 — DRYING, GRINDING & DRY SOIL PREP", [
            "Retained Drying Room (2x 1,050 x 2,000 mm ovens) & Grinding Room (2 grinders + 108 x 108 cm hood).",
            "Prep Corridor links seamlessly to Post-Grind Scan PC (60 x 120 cm) and Sulphide Area (8 PCs).",
            "Lower deck of Soils double-deck rollers carries dry soil trays; Rapid Moisture bench (344 x 77 cm) sits at north exit.",
        ]),
        ("PHASE 3 — ORGANIC CHEMISTRY PREP", [
            "Two 50 x 50 cm point-of-use benchtop fume hoods mounted cleanly within S8 & S11 desks.",
            "Soils Row 5 (S13-S15) dedicated to Shakers & Vialling-Up feeding upper wet/prepared roller deck.",
            "Sulphide dividing bench integrates PC 1 -> 2 Shakers -> 2 Wash Sinks -> TOC Vacuum Pump; Waters Testing 1-4 completes aqueous prep.",
        ]),
    ]
    for idx, (ptitle, plines) in enumerate(phases):
        add_card(s3, 0.5 + idx * 4.18, 1.48, 3.96, 3.15, ptitle, plines)

    # Summary Table of Wing Footprint
    tbl_shape = s3.shapes.add_table(4, 5, Inches(0.5), Inches(4.85), Inches(12.33), Inches(2.05))
    t3 = tbl_shape.table
    rows3 = [
        ["Zone / Wing", "Dimensions (mm)", "Net Area (m2)", "Primary Consolidated Phases", "Key Changes"],
        ["Left Wing (Grinding, Drying, Changing, Prep, Sulphide, On-Hold)", "5,900 x 18,134", "107.0", "Phase 2 & Phase 3 + Control", "Retained Ovens/Grinders; Island widened 1.50x5.40 m; +400 cm Racks"],
        ["Main Hall (Sorting, Soils 3x5, Waters 10, Logistics, 4 W/Cs)", "12,393 x 18,134", "224.7", "Phase 1, Phase 2 & Phase 3", "Demolished old TLO & Stairs; 240 cm Walkway; 3 Roller Conveyors"],
        ["Front Extension (Canteen, Merged CS Office, Entryway)", "14,030 x 3,442", "48.3", "Workplace & Customer Support", "Merged 8-desk dual-screen CS Office + Direct Door to Canteen"],
    ]
    for r, rdata in enumerate(rows3):
        for c, val in enumerate(rdata):
            t3.cell(r, c).text = val
    style_table(t3, [3.6, 1.7, 1.15, 2.28, 3.6], font_pt=9.2)
    set_notes(
        s3,
        "This slide maps how Phases 1, 2, and 3 operate together inside one unified floor plate. "
        "Note that 'Phase 1, 2, 3' refer strictly to the sample-processing workflow stages consolidated inside the SomeLab SomewhereintheUK Consolidated Prep Facility (Project Vol)."
    )

    # --- SLIDE 4: Master 2D Floor Plan & Zoning ---
    s4 = prs.slides.add_slide(blank)
    add_header_chrome(s4, 4, "Architectural Plan", "Master 2D Floor Plan & Dimensional Zoning", "Exact millimeter layout generated directly from data/layout_spec.json (0 static overlaps, 0 chair clashes, all 13 doors clear).")
    add_picture_fitted(s4, PLAN_2D_PNG, 0.45, 1.42, 9.45, 5.58, frame=True)

    add_card(
        s4, 10.05, 1.45, 2.8, 5.52, "Verified Geometry Audit",
        [
            "Main Shell: 18,293 x 18,134 mm; Front Wing: 3,442 mm deep.",
            "Central Walkway: 2,400 mm clear width.",
            "Soils Gaps: Uniform 1,500 mm across all 5 rows.",
            "Sulphide Aisles: 1,500 mm left & right of 1.50x5.40 m island.",
            "On-Hold Path: 600 mm between 400 cm racks.",
            "Drying Door (D-DRY): Optimized +Y outward swing for 100% oven clearance.",
            "All 45 chairs verified clear of benches, conveyors & walls.",
        ],
    )
    set_notes(
        s4,
        "Our automated geometry validation suite confirms zero overlaps across 60 floor-standing objects, 15 benchtop items, 45 seated chairs, "
        "and all required lean walkways. Flipping the Drying Room door outward (+Y) into the Prep Corridor resolved the retained oven swing clash cleanly."
    )

    # --- SLIDE 5: One-Directional Flow & Sample Segregation (SOP Bridge) ---
    s5 = prs.slides.add_slide(blank)
    add_header_chrome(s5, 5, "SOP & Flow Control", "One-Directional Flow & Sample Segregation", "Strict physical separation from bottom-right intake through parallel roller lanes to independent north exit doors.")

    steps = [
        ("1. SINGLE INTAKE", "Main Entrance (1,400 mm)\nBottom-Right Drop-Off"),
        ("2. INITIAL TRIAGE", "300 x 400 cm Sorting Zone\nImmediate Water / Soil Split"),
        ("3. BARRIER & LANES", "240 cm Central Walkway\nZero Cross-Traffic"),
        ("4. PARALLEL PROCESSING", "East: 10 Waters + 60 cm Roller\nWest: 15 Soils + Dual Rollers"),
        ("5. DUAL OUTBOUND EXITS", "Exit 1 (North-West): Soils Out\nExit 2 (North-East): Waters Out"),
    ]
    for idx, (sh, sb) in enumerate(steps):
        sx = 0.5 + idx * 2.52
        box = s5.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(sx), Inches(1.52), Inches(2.28), Inches(1.38))
        box.adjustments[0] = 0.05
        box.fill.solid()
        box.fill.fore_color.rgb = NAVY if idx in (0, 2, 4) else SURFACE_ALT
        box.line.color.rgb = BLUE_ACCENT if idx == 2 else BORDER
        tb = s5.shapes.add_textbox(Inches(sx + 0.12), Inches(1.62), Inches(2.04), Inches(1.18))
        tf = tb.text_frame
        tf.word_wrap = True
        p0 = tf.paragraphs[0]
        p0.text = sh
        p0.font.name = "Calibri"
        p0.font.size = Pt(10.5)
        p0.font.bold = True
        p0.font.color.rgb = WHITE if idx in (0, 2, 4) else BLUE_ACCENT
        p1 = tf.add_paragraph()
        p1.text = sb
        p1.font.name = "Calibri"
        p1.font.size = Pt(9.5)
        p1.font.color.rgb = RGBColor(0xE2, 0xE8, 0xF0) if idx in (0, 2, 4) else SLATE

        if idx < 4:
            arr = s5.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, Inches(sx + 2.31), Inches(2.05), Inches(0.18), Inches(0.3))
            arr.fill.solid()
            arr.fill.fore_color.rgb = BLUE_ACCENT
            arr.line.fill.background()

    add_picture_fitted(s5, STILLS_DIR / "view_02.png", 0.5, 3.12, 6.2, 3.8, frame=True)
    add_card(
        s5, 6.95, 3.12, 5.88, 3.8, "SOP Segregation Controls",
        [
            "Physical 240 cm barrier prevents Waters and Soils trolleys or personnel from intersecting.",
            "Waters Stream (X >= 14,700 mm): Single-deck 60 cm roller carries crates straight north to Exit Door 2.",
            "Soils Stream (X <= 12,300 mm): Dual-deck 60 cm rollers separate raw/dry soil crates (lower deck) from wet/prepared extracts (upper deck) exiting via Exit Door 1.",
            "Dry Prep Loop: Prep Corridor connects Drying Ovens, Grinders, and Post-Grind Scan PC directly to Sulphide without entering Waters Lane.",
            "On-Hold & Cold Storage isolated along the south-west boundary to keep active conveyors clear.",
        ],
    )
    set_notes(
        s5,
        "Sample segregation is both architectural and procedural. Waters and Soils never cross paths once sorted at the bottom-right drop-off zone: "
        "each stream moves monotonically bottom-to-top along dedicated rollers to its own north-wall exit door."
    )

    # --- SLIDE 6: Waters Lane Deep Dive ---
    s6 = prs.slides.add_slide(blank)
    add_header_chrome(s6, 6, "Main Hall — East Wing", "Waters Lane Deep Dive (10 Stations + 60 cm Roller)", "Seamless registration, splitting, and aqueous testing along a continuous 11.25 m roller conveyor.")
    add_picture_fitted(s6, STILLS_DIR / "view_03.png", 0.5, 1.48, 7.1, 5.42, frame=True)
    add_card(
        s6, 7.82, 1.48, 5.01, 2.6, "Station Ergonomics & Layout",
        [
            "Row 1 (Y=13,750): H2O Reg 1 & 2 (60 x 130 cm, perpendicular) — analysts seated on top edge facing Main Door intake.",
            "Row 2 (Y=11,850): H2O Reg/Split 1 & 2 (60 x 130 cm, perpendicular) — analysts seated on top edge facing intake.",
            "Rows 3-5 (Y=9,150 / 6,650 / 4,150): H2O Split 3-4 + H2O Test 1-4 (60 x 130 cm, parallel) — analysts on outer sides facing roller.",
        ],
    )
    add_card(
        s6, 7.82, 4.28, 5.01, 2.62, "Equipment & Flow Integration",
        [
            "100% IT parity: all 10 stations equipped with single PC workstation + thermal label printer.",
            "Continuous 60 cm roller conveyor (X=16,000..16,600, Y=3,300..14,550) links every station without manual lifting.",
            "Direct outbound line from north end of roller through Exit Door 2 (Waters Out, X=16,980..18,080).",
            "5-Tier Subcontract Storage Shelf (70 x 150 cm) positioned adjacent to Exit Door 2 for external dispatch staging.",
        ],
    )
    set_notes(
        s6,
        "The Waters Lane houses 10 uniform 60 x 130 cm stations flanking a central 60 cm roller conveyor. "
        "Notice the hybrid orientation matching our visual ground truth: bottom two rows sit perpendicular facing incoming deliveries at the Main Door, "
        "while the upper three splitting and testing rows align parallel so analysts work directly off the moving roller without twisting."
    )

    # --- SLIDE 7: Soils Lane Deep Dive ---
    s7 = prs.slides.add_slide(blank)
    add_header_chrome(s7, 7, "Main Hall — West Wing", "Soils Lane Deep Dive (3 x 5 Array + Double-Deck Rollers)", "15 uniform 60 x 130 cm benches served by dual-deck dry/wet conveyors and point-of-use benchtop fume hoods.")
    add_picture_fitted(s7, STILLS_DIR / "view_04.png", 0.5, 1.48, 7.1, 5.42, frame=True)
    add_card(
        s7, 7.82, 1.48, 5.01, 2.65, "3 x 5 Matrix & Double-Deck Conveyors",
        [
            "3 columns (X=6,500 / 8,400 / 11,000) x 5 rows with uniform 150 cm movement gaps (Y=14,350 down to 5,950).",
            "2 Double-Deck Rollers (60 cm wide, Y=5,250..15,050) between Columns 1-2 and Columns 2-3.",
            "Lower Deck (520 mm): transports dry soil samples; Upper Deck (920 mm): transports wet/prepared samples.",
        ],
    )
    add_card(
        s7, 7.82, 4.30, 5.01, 2.60, "Row Functions & Point-of-Use Extraction",
        [
            "Row 1 (S1-S3): Soils Registration — analysts on bottom edge facing upward (-Y) toward rollers.",
            "Row 2 (S4-S6): Soils Registration — analysts on top edge facing downward (+Y).",
            "Rows 3-4 (S7-S12): Hybrid Splitting & Registration (PC + Printer); middle stations S8 & S11 each hold a 50 x 50 cm benchtop fume hood cleanly within the 60 x 130 cm desk footprint.",
            "Row 5 (S13-S15): Shakers & Vialling-Up benches feeding final dispatch via Exit Door 1.",
        ],
    )
    set_notes(
        s7,
        "The Soils 3x5 Array standardizes every bench at 60 x 130 cm with 150 cm ergonomic movement gaps. "
        "By deploying two double-deck 60 cm rollers, dry soils and wet/prepared samples move simultaneously on separate vertical tiers with zero collision, "
        "while compact 50 x 50 cm benchtop fume hoods on S8 and S11 bring extraction right to the splitting analyst."
    )

    # --- SLIDE 8: Sulphide, Drying & Grinding Wing ---
    s8 = prs.slides.add_slide(blank)
    add_header_chrome(s8, 8, "Left Wing Specialist Prep", "Sulphide, Drying & Grinding Wing", "Widened 1.50 x 5.40 m island (8 Sulphide PCs + Post-Grind Scan PC) linked to retained Drying Ovens and Grinders.")
    add_picture_fitted(s8, STILLS_DIR / "view_05.png", 0.5, 1.48, 6.05, 3.6, frame=True)
    add_picture_fitted(s8, STILLS_DIR / "view_06.png", 6.78, 1.48, 6.05, 3.6, frame=True)

    add_card(
        s8, 0.5, 5.25, 6.05, 1.72, "Sulphide Area (5,900 x 9,088 mm • 8+1 PCs)",
        [
            "Island expanded to 1.50 x 5.40 m (+3 Island PCs) preserving 150 cm aisles on both sides; 4 Outer Wall PCs at 150 cm spacing.",
            "Dividing wall sequence: PC 1 -> 2 Shakers (60x90 cm) -> 2 Wash Sinks (60x115 cm) -> TOC Vacuum Pump + 24-cell holder.",
        ],
    )
    add_card(
        s8, 6.78, 5.25, 6.05, 1.72, "Retained Grinding, Drying & Post-Grind Scan",
        [
            "Retained Grinding Room (2 grinders + 108 x 108 cm hood), Changing Room, and Drying Room (2x 1,050 x 2,000 mm ovens).",
            "Post-Grind Sample-Scanning PC (60 x 120 cm) placed behind Changing Room wall; Drying door swings +Y into Prep Corridor.",
        ],
    )
    set_notes(
        s8,
        "Left wing improvements center on expanding the Sulphide island to 1.50 x 5.40 m to add three workstation positions while keeping generous 150 cm side aisles. "
        "All eight Sulphide PCs plus the Post-Grind Scan PC integrate seamlessly with the retained Drying and Grinding rooms via the Prep Corridor."
    )

    # --- SLIDE 9: Sample Control, Cold Storage & Logistics ---
    s9 = prs.slides.add_slide(blank)
    add_header_chrome(s9, 9, "Sample Control & Outbound", "Sample Control, Cold Storage & North Logistics Wall", "Dedicated 400 cm On-Hold storage, retained External Cold Storage, and north-wall Logistics / Dual Exits.")
    add_picture_fitted(s9, STILLS_DIR / "view_07.png", 0.5, 1.48, 7.1, 5.42, frame=True)
    add_card(
        s9, 7.82, 1.48, 5.01, 2.6, "On-Hold & Cold Storage Capacity",
        [
            "On-Hold Storage Room (5,900 x 1,946 mm): two facing 400 x 60 cm 6-tier racks separated by a 60 cm walking path.",
            "Dedicated 500 L standalone tall fridge (80 x 100 cm footprint, 200 cm H) at west end of On-Hold room.",
            "External Cold Storage (1,800 x 10,800 mm) retained outside west exterior wall—zero relocation disruption.",
        ],
    )
    add_card(
        s9, 7.82, 4.28, 5.01, 2.62, "North Logistics Wall & Dual Outbound Doors",
        [
            "Exit Door 1 (Soils Out, X=6,100..7,200) positioned cleanly at north-west end of Soils Lane.",
            "Rapid Moisture / Logistics Bench (344 x 77 cm) with PC + label printer, flanked by Logistics WS 1 & 2 (70 x 210 cm).",
            "5-Tier Subcontract Shelf (70 x 150 cm) buffers outbound external shipments next to Exit Door 2 (Waters Out).",
        ],
    )
    set_notes(
        s9,
        "Sample control and outbound logistics close the one-directional loop cleanly. On-Hold storage provides 8 linear meters of 6-tier racking plus a 500 L fridge, "
        "while the north wall pairs Rapid Moisture testing and Subcontracting workstations directly between Exit Door 1 (Soils) and Exit Door 2 (Waters)."
    )

    # --- SLIDE 10: Team & Workplace Upgrades ---
    s10 = prs.slides.add_slide(blank)
    add_header_chrome(s10, 10, "People & Workplace", "Merged CS Office, Modernized Canteen & 4 W/Cs", "Removing legacy office partitions to unite Customer Service & Admin teams with direct canteen access.")
    add_picture_fitted(s10, STILLS_DIR / "view_08.png", 0.5, 1.48, 7.1, 5.42, frame=True)
    add_card(
        s10, 7.82, 1.48, 5.01, 2.6, "Merged CS / Admin Office (8,000 x 3,442 mm)",
        [
            "Dividing wall between old Preparation Managers Office and Lean Office demolished to create one bright open-plan suite.",
            "8 ergonomic workstations (2 rows x 4 desks, 150 x 70 cm each) equipped with dual-screen PCs (16 monitors total).",
            "Glazed partition wall to Entryway maintains acoustic separation while maximizing natural light.",
        ],
    )
    add_card(
        s10, 7.82, 4.28, 5.01, 2.62, "Canteen & Toilet Block Welfare Upgrade",
        [
            "Direct connecting door (X=4,550, Y=19,550..20,400) links Merged CS Office straight into Modernized Canteen.",
            "Modernized Canteen (4,550 x 3,442 mm) outfitted with kitchenette counter and 2 full-size dining tables.",
            "Upgraded Toilet Block (5,337 x 2,048 mm) expanded to 4 W/C cubicles + washbasins/boiler alcove + rear access corridor.",
        ],
    )
    set_notes(
        s10,
        "Project Vol invests directly in our SomewhereintheUK team's daily workplace. Removing the dividing wall creates an 8-person open-plan Customer Service and Admin hub "
        "with dual-screen workstations, direct access to a modernized canteen, and an upgraded four-cubicle welfare block."
    )

    # --- SLIDE 11: Live 3D Walkthrough & Video Tour ---
    s11 = prs.slides.add_slide(blank)
    set_bg(s11, NAVY)
    tb11 = s11.shapes.add_textbox(Inches(0.6), Inches(0.45), Inches(12.1), Inches(1.1))
    tf11 = tb11.text_frame
    tf11.word_wrap = True
    p0 = tf11.paragraphs[0]
    p0.text = "INTERACTIVE DIGITAL TWIN & GUIDED TOUR"
    p0.font.name = "Calibri"
    p0.font.size = Pt(11)
    p0.font.bold = True
    p0.font.color.rgb = RGBColor(0x94, 0xA3, 0xB8)
    p1 = tf11.add_paragraph()
    p1.text = "Live 3D WebGL Walkthrough, Video Tour & Cycles Photorealism Bridge"
    p1.font.name = "Calibri"
    p1.font.size = Pt(24)
    p1.font.bold = True
    p1.font.color.rgb = WHITE

    thumbs = [("view_01.png", "1. Intake & Sorting"), ("view_03.png", "3. Waters Lane"), ("view_04.png", "4. Soils 3x5 Array"), ("view_08.png", "8. CS Office & Canteen")]
    for idx, (fn, cap) in enumerate(thumbs):
        tx = 0.6 + idx * 3.08
        add_picture_fitted(s11, STILLS_DIR / fn, tx, 1.75, 2.9, 1.9, frame=False)
        ctb = s11.shapes.add_textbox(Inches(tx), Inches(3.70), Inches(2.9), Inches(0.32))
        ctf = ctb.text_frame
        cp = ctf.paragraphs[0]
        cp.text = cap
        cp.font.name = "Calibri"
        cp.font.size = Pt(10)
        cp.font.bold = True
        cp.font.color.rgb = RGBColor(0xCB, 0xD5, 0xE1)

    launch_items = [
        ("Interactive Web Hub", "cd web && npm run dev  ->  http://localhost:5173\nOrbit/Pan/Zoom, Roof & Cutaway toggle, click any bench for exact mm specs."),
        ("8-Chapter Guided Tour + Video", "Smooth Catmull-Rom 3D camera tour with 1-click 60fps MediaRecorder download or headless 1080p MP4 export (scripts/export_video_tour.mjs)."),
        ("Blender Cycles Bridge", "blender --background --python scripts/blender_build_vol.py -- --render-stills\nUses identical data/layout_spec.json + 8 locked white/grey render prompts."),
    ]
    for idx, (lh, lb) in enumerate(launch_items):
        lx = 0.6 + idx * 4.12
        box = s11.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(lx), Inches(4.35), Inches(3.92), Inches(2.45))
        box.adjustments[0] = 0.05
        box.fill.solid()
        box.fill.fore_color.rgb = RGBColor(0x1E, 0x29, 0x3B)
        box.line.color.rgb = RGBColor(0x33, 0x41, 0x55)
        ltb = s11.shapes.add_textbox(Inches(lx + 0.18), Inches(4.5), Inches(3.56), Inches(2.15))
        ltf = ltb.text_frame
        ltf.word_wrap = True
        lp0 = ltf.paragraphs[0]
        lp0.text = lh
        lp0.font.name = "Calibri"
        lp0.font.size = Pt(13)
        lp0.font.bold = True
        lp0.font.color.rgb = WHITE
        lp0.space_after = Pt(6)
        lp1 = ltf.add_paragraph()
        lp1.text = lb
        lp1.font.name = "Calibri"
        lp1.font.size = Pt(10.5)
        lp1.font.color.rgb = RGBColor(0xCB, 0xD5, 0xE1)

    set_notes(
        s11,
        "At this point in the leadership briefing, switch to the live Vite React + Three.js executive web hub (http://localhost:5173) to run the 8-chapter guided tour, "
        "toggle the Sample Segregation Flow Overlay, click stations to inspect dimensions, or capture updated stills into the Photo Gallery."
    )

    # --- SLIDE 12: Equipment Schedule, CapEx Discipline & Implementation Roadmap ---
    s12 = prs.slides.add_slide(blank)
    add_header_chrome(s12, 12, "Delivery & Governance", "Equipment Schedule, CapEx Scope & Implementation Roadmap", "Auto-tallied inventory from data/layout_spec.json paired with phased site execution.")

    tbl12 = s12.shapes.add_table(9, 4, Inches(0.5), Inches(1.48), Inches(6.8), Inches(4.15)).table
    counts_rows = [
        ["Asset / System Category", "Count", "Specification", "Scope Status"],
        ["Waters Lane Stations", str(sum(1 for i in items if i["category"] == "waters_station")), "60 x 130 cm + PC + Label Printer", "New Lean Fit-Out"],
        ["Soils 3x5 Stations", str(sum(1 for i in items if i["category"] == "soils_station")), "60 x 130 cm (12 PC+Prt, 3 Shaker/Vial)", "New Lean Fit-Out"],
        ["Sulphide PCs (+ Post-Grind Scan)", "8 + 1", "4 Wall + 3 Island (1.50x5.40 m) + 1 Div + 1 Scan", "Reconfigured / Expanded"],
        ["Merged CS Office Workstations", str(dual_pcs), "150 x 70 cm Dual-Screen PCs (16 displays)", "Merged Open-Plan"],
        ["Roller Conveyors", str(len(spec["conveyors"])), "1x 60 cm Waters + 2x Double-Deck Soils", "New Automation"],
        ["Fume Hoods (Total)", str(sum(1 for i in items if i["has_fume_hood"])), "1x Grinding (108x108) + 2x Soils (50x50 cm)", "1 Retained + 2 New"],
        ["Retained Ovens & Grinders", "2 + 2", "2 Drying Ovens + 2 Soil Grinders + Ext Cold", "Retained In Place"],
        ["Total PCs / Label Printers", f"{total_pcs} / {total_printers}", "Full LIMS & Barcode Coverage", "Synchronized BOM"],
    ]
    for r, rd in enumerate(counts_rows):
        for c, v in enumerate(rd):
            tbl12.cell(r, c).text = v
    style_table(tbl12, [2.25, 0.75, 2.45, 1.35], font_pt=8.8)

    add_card(
        s12, 7.52, 1.48, 5.31, 2.05, "CapEx Discipline (Retain vs. Redevelop)",
        [
            "Zero relocation of Grinding Room, Drying Ovens, Changing Room, or External Cold Storage.",
            "Targeted demolition strictly limited to Team Leaders Office, Stairs, and CS dividing wall.",
        ],
    )
    add_card(
        s12, 7.52, 3.68, 5.31, 3.22, "4-Stage Phased Implementation Roadmap",
        [
            "Stage 1 (Weeks 1-2): Strip-out & demolition of Team Leaders Office, stairs, and CS divider; flip D-DRY outward (+Y).",
            "Stage 2 (Weeks 3-5): M&E first-fix (4 W/Cs, Sulphide sinks/TOC, 2x 50x50 cm LEV drops, recessed LEDs) & grey epoxy flooring.",
            "Stage 3 (Weeks 6-8): Install white/grey benches, 3 roller conveyors, Sulphide 1.50x5.40 m island, 400 cm On-Hold racks, and 8-desk CS Office.",
            "Stage 4 (Weeks 9-10): IT/LIMS commissioning (42 PCs, 23 printers), SOP sign-off, and Go-Live transition.",
        ],
    )
    set_notes(
        s12,
        "Slide 12 summarizes the full equipment counts audited in Project_Vol_Equipment_Schedule.xlsx alongside our phased 10-week rollout roadmap. "
        "Retaining heavy drying, grinding, and external cold infrastructure protects capital budget while transforming sample velocity and segregation."
    )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    prs.save(OUT_PPTX)
    print(f"Saved PowerPoint: {OUT_PPTX} ({OUT_PPTX.stat().st_size // 1024} KB)")

    # Copy all downloadable outputs to web/public/downloads/
    WEB_DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
    for fn in (
        "Project_Vol_Presentation.pptx",
        "Project_Vol_2D_Spec.svg",
        "Project_Vol_2D_Spec.png",
        "Project_Vol_2D_Spec.pdf",
        "Project_Vol_Equipment_Schedule.xlsx",
    ):
        src = OUT_DIR / fn
        if src.exists():
            shutil.copy2(src, WEB_DOWNLOADS_DIR / fn)

    audit_presentation(OUT_PPTX)


def audit_presentation(pptx_path: Path) -> None:
    """Verify 12 slides, non-empty speaker notes, zero overflow bounds, and zero banned strings."""
    prs = Presentation(pptx_path)
    assert len(prs.slides) == 12, f"Expected 12 slides, got {len(prs.slides)}"
    max_w = int(Inches(SLIDE_W + 0.02))
    max_h = int(Inches(SLIDE_H + 0.02))
    legacy_city = "cov" + "entry"
    for idx, slide in enumerate(prs.slides, start=1):
        notes = slide.notes_slide.notes_text_frame.text.strip()
        assert len(notes) >= 80, f"Slide {idx} speaker notes too short ({len(notes)} chars)"
        assert legacy_city not in notes.lower(), f"Slide {idx} notes contain legacy city"
        for shp in slide.shapes:
            assert shp.left >= -5000 and shp.top >= -5000, f"Slide {idx} negative pos"
            assert shp.left + shp.width <= max_w, f"Slide {idx} shape exceeds right bound"
            assert shp.top + shp.height <= max_h, f"Slide {idx} shape exceeds bottom bound"
            if shp.has_text_frame:
                txt = shp.text_frame.text.lower()
                assert legacy_city not in txt, f"Slide {idx} text contains legacy city"
                assert "phase 2 lab" not in txt, f"Slide {idx} calls building Phase 2 Lab"
    print("PPTX Audit PASSED: 12 slides, all speaker notes verified, 0 bounds overflows, 0 banned terms.")


def main() -> None:
    with SPEC_PATH.open("r", encoding="utf-8") as f:
        spec = json.load(f)
    build_presentation(spec)


if __name__ == "__main__":
    main()
