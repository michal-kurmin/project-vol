# Project Vol — SomeLab SomewhereintheUK Consolidated Prep Facility

Executive visualization, technical specification, and presentation suite for the redevelopment of the **SomeLab Laboratory in SomewhereintheUK (Unit 1, Science Park)** — consolidating **Phase 1 (Sample Registration)**, **Phase 2 (Drying, Grinding & Dry Soil Prep)**, and **Phase 3 (Organic Chemistry Prep)** under one roof with one-piece, one-directional flow and strict Waters vs. Soils sample segregation.

All deliverables are driven by a Single Source of Truth: [`data/layout_spec.json`](data/layout_spec.json).

## Directory Structure

```text
project-vol/
├── data/
│   └── layout_spec.json                     # Single source of truth (mm coordinates, equipment, flow paths)
├── web/                                     # Vite + React + Three.js + Tailwind executive web hub
│   ├── src/components/                      # Lab3DViewer, FloorPlan2DView, PhotoGallery, SlideDeckViewer
│   ├── src/assets/gallery/                  # Captured 3D stills & photorealistic render slots
│   └── public/downloads/                    # Downloadable 2D specs, .xlsx schedule, and .pptx deck
├── scripts/
│   ├── validate_layout.py                   # Automated geometry, clearance & inventory audit
│   ├── generate_2d_specs.py                 # 2D monochrome SVG/PNG/PDF + 3-tab Excel BOM generator
│   ├── render_3d_stills.py                  # Deterministic 16:9 white/grey 3D architectural stills
│   ├── generate_presentation.py             # 12-slide executive PowerPoint (.pptx) generator + audit
│   ├── blender_build_vol.py             # Standalone Blender Cycles photorealism & MP4 builder
│   └── export_video_tour.mjs                # Optional Playwright + FFmpeg 1080p 60fps MP4 exporter
└── outputs/
    ├── Project_Vol_2D_Spec.svg          # Vector 2D architectural plan
    ├── Project_Vol_2D_Spec.png          # 300 DPI 2D floor plan
    ├── Project_Vol_2D_Spec.pdf          # Printable vector PDF floor plan
    ├── Project_Vol_Equipment_Schedule.xlsx
    ├── Project_Vol_Presentation.pptx    # 12-slide executive PowerPoint with speaker notes
    ├── gallery_prompts.json                 # 8 camera-locked white/grey architectural prompts
    └── gallery_stills/                      # Rendered 16:9 stills (view_01.png .. view_08.png)
```

## 1. Validate Layout Geometry

```bash
python scripts/validate_layout.py
```

## 2. Regenerate Deliverables from `data/layout_spec.json`

```bash
python scripts/generate_2d_specs.py
python scripts/render_3d_stills.py
python scripts/generate_presentation.py
```

## 3. Launch the Live Executive Web Hub

```bash
cd web
npm install
npm run dev
```

Open `http://localhost:5173` in your browser to explore:
- **3D Model & Tour:** Orbit/pan/zoom, cutaway/full-height/roof/top-down modes, station click inspection HUD, Sample Segregation Flow Overlay, 8-chapter guided tour, **Record Tour Video** (60fps WebM), and **Capture Gallery Stills**.
- **2D Spec:** Interactive zoomable SVG plan with layer toggles and direct downloads (SVG, PNG, PDF, `.xlsx`).
- **Photo Gallery:** 8 architectural viewpoints with category filters, dimension callouts, render prompts, fullscreen lightbox, and drop-in Cycles/AI image replacement.
- **Slideshow:** 12-slide executive deck mirroring `Project_Vol_Presentation.pptx` with keyboard navigation (`←`/`→`), speaker notes, and 1-click `.pptx` download.

## 4. Export a 1080p 60fps MP4 Tour Video (Optional)

Requires Playwright (`cd web && npm install -D playwright`) and `ffmpeg` on `PATH`:

```bash
node scripts/export_video_tour.mjs
```

## 5. Render Photorealistic Cycles Stills / Video in Blender

```bash
blender --background --python scripts/blender_build_vol.py -- --render-stills --samples 128
blender --background --python scripts/blender_build_vol.py -- --render-video --save-blend
```
