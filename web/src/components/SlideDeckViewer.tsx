import { useEffect, useState } from 'react';
import {
  ChevronLeft,
  ChevronRight,
  Download,
  FileText,
  Presentation as PresentationIcon,
  ArrowRight,
} from 'lucide-react';
import type { LayoutSpec } from '../types/layout';
import { DEFAULT_GALLERY_IMAGES } from './PhotoGallery';

interface SlideDeckViewerProps {
  spec: LayoutSpec;
  capturedStills: Record<number, string>;
  onOpen3DTour: () => void;
}

interface SlideModel {
  id: number;
  category: string;
  title: string;
  subtitle: string;
  notes: string;
  render: () => JSX.Element;
}

export default function SlideDeckViewer({
  spec,
  capturedStills,
  onOpen3DTour,
}: SlideDeckViewerProps) {
  const [index, setIndex] = useState(0);
  const [showNotes, setShowNotes] = useState(true);

  const img = (id: number) => capturedStills[id] ?? DEFAULT_GALLERY_IMAGES[id];
  const items = spec.stations_and_equipment;
  const totalPcs = items.filter((i) => i.has_pc).length;
  const dualPcs = items.filter((i) => i.dual_monitor).length;
  const totalMonitors = totalPcs + dualPcs;
  const totalPrinters = items.filter((i) => i.has_label_printer).length;
  const giaM2 = (
    (spec.shell.main_building.w * spec.shell.main_building.h +
      spec.shell.front_extension.w * spec.shell.front_extension.h) /
    1e6
  ).toFixed(1);

  const slides: SlideModel[] = [
    {
      id: 1,
      category: 'Executive Redevelopment Proposal',
      title: 'Project Vol — SomeLab SomewhereintheUK Lean Lab Redevelopment',
      subtitle: 'Consolidated Prep Facility • Unit 1, Science Park, SomewhereintheUK',
      notes:
        'Project Vol establishes the SomeLab SomewhereintheUK Consolidated Prep Facility at Unit 1, Science Park, uniting Sample Registration (Phase 1), Drying & Grinding (Phase 2), and Organic Chemistry Prep (Phase 3) under one roof.',
      render: () => (
        <div className="bg-slate-900 text-white rounded-xl p-8 h-full flex flex-col justify-between">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-center">
            <div>
              <div className="text-xs font-bold uppercase tracking-widest text-slate-400">
                SomeLab SomewhereintheUK • Unit 1, Science Park
              </div>
              <h2 className="text-3xl font-bold mt-2 leading-tight">
                Project Vol — Consolidated Prep Facility
              </h2>
              <p className="text-sm text-slate-300 mt-3 leading-relaxed">
                Transitioning to one-piece, one-directional lean flow: unifying Phases 1, 2 &amp; 3 with complete physical segregation of Waters and Soils.
              </p>
            </div>
            <img src={img(2)} alt="Central Segregation Walkway" className="rounded-lg border border-slate-700 w-full aspect-video object-cover" />
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-6">
            {[
              [`${giaM2} m²`, 'Gross Internal Area'],
              ['25 Stations', '10 Waters + 15 Soils'],
              [`${totalPcs} PCs / ${totalMonitors} Screens`, 'Full LIMS Coverage'],
              ['240 cm Barrier', '0 Sample Crossings'],
            ].map(([v, l]) => (
              <div key={l} className="bg-slate-800 border border-slate-700 rounded-lg p-3">
                <div className="text-lg font-bold">{v}</div>
                <div className="text-xs text-slate-400">{l}</div>
              </div>
            ))}
          </div>
        </div>
      ),
    },
    {
      id: 2,
      category: 'Strategic Case',
      title: 'Executive Summary & Why Consolidate Now',
      subtitle: 'Eliminating inter-building transport, duplicate handoffs, and cross-stream bottlenecks.',
      notes:
        'Consolidating all three sample-prep workflows into the 18.3 x 18.1 m shell eliminates non-value-adding cart movement while protecting CapEx by retaining heavy drying, grinding, and external cold rooms.',
      render: () => (
        <div className="space-y-5">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {[
              [`${giaM2} m²`, 'Consolidated Indoor GIA'],
              ['25', 'Production Stations (10W / 15S)'],
              [`${totalPcs} / ${totalMonitors}`, `PCs / Monitors (${totalPrinters} Printers)`],
              ['0', 'Cross-Flow Intersections'],
            ].map(([n, l]) => (
              <div key={l} className="bg-slate-50 border border-slate-200 rounded-lg p-3">
                <div className="text-2xl font-bold text-blue-900">{n}</div>
                <div className="text-xs font-medium text-slate-700 mt-0.5">{l}</div>
              </div>
            ))}
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs text-slate-700">
            <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 space-y-2">
              <div className="font-bold text-sm text-slate-900">Operational Pain Points Resolved</div>
              <p>• Demolishes bottom-right Team Leaders Office &amp; stairs to create a 300 × 400 cm Sorting Drop-Off Zone.</p>
              <p>• Double-deck Soils rollers separate dry soil (lower) and wet/prepared (upper) trays.</p>
              <p>• Sulphide island expanded to 1.50 × 5.40 m (+3 PCs, 8 total PCs) with 150 cm aisles.</p>
            </div>
            <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 space-y-2">
              <div className="font-bold text-sm text-slate-900">CapEx Discipline &amp; Clinical Finish</div>
              <p>• Retains Grinding Room, Drying Room, Changing Room, and External Cold Storage in place.</p>
              <p>• Flipping Drying Room door D-DRY outward (+Y) clears retained ovens with zero machinery move.</p>
              <p>• Monochrome white &amp; grey finish supports hygiene, lighting, and visual management.</p>
            </div>
          </div>
        </div>
      ),
    },
    {
      id: 3,
      category: 'Consolidation Architecture',
      title: 'Uniting Phases 1, 2 & 3 Under One Roof',
      subtitle: 'Mapping Sample Registration (P1), Drying/Grinding (P2), and Organic Chemistry Prep (P3).',
      notes:
        'Phases 1, 2, and 3 represent the consolidated analytical workflow stages operating together inside the SomeLab SomewhereintheUK Consolidated Prep Facility.',
      render: () => (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
          {spec.meta.strategic_narrative.consolidated_phases.map((ph) => (
            <div key={ph.phase} className="bg-slate-50 border border-slate-200 rounded-lg p-4 border-t-4 border-t-blue-900">
              <div className="font-bold text-blue-900 uppercase">{ph.phase}</div>
              <div className="text-sm font-bold text-slate-900 mt-1">{ph.name}</div>
              <p className="text-slate-600 mt-2 leading-relaxed">{ph.description}</p>
            </div>
          ))}
        </div>
      ),
    },
    {
      id: 4,
      category: 'Architectural Plan',
      title: 'Master 2D Floor Plan & Dimensional Zoning',
      subtitle: 'Driven directly by data/layout_spec.json — 0 overlaps, 0 chair clashes, all 13 doors clear.',
      notes:
        'All millimeter coordinates are audited automatically by scripts/validate_layout.py before generating 2D CAD sheets, 3D WebGL geometry, and this deck.',
      render: () => (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 items-center">
          <img
            src="/downloads/Project_Vol_2D_Spec.png"
            alt="Master 2D Architectural Plan"
            className="lg:col-span-2 rounded-lg border border-slate-200 w-full max-h-[420px] object-contain bg-white"
          />
          <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 text-xs space-y-2 text-slate-700">
            <div className="font-bold text-sm text-slate-900">Verified Clearances</div>
            <div>• Shell: 18,293 × 18,134 mm</div>
            <div>• Front Wing: 14,030 × 3,442 mm</div>
            <div>• Central Walkway: 2,400 mm clear</div>
            <div>• Soils Row Gaps: 1,500 mm uniform</div>
            <div>• Sulphide Aisles: 1,500 mm L &amp; R</div>
            <div>• On-Hold Path: 600 mm between racks</div>
            <div>• D-DRY Door: +Y swing into Prep Corridor</div>
          </div>
        </div>
      ),
    },
    {
      id: 5,
      category: 'SOP & Flow Control',
      title: 'One-Directional Flow & Sample Segregation',
      subtitle: 'Single intake -> 300 x 400 cm sorting -> 240 cm walkway -> Exit 1 (Soils) / Exit 2 (Waters).',
      notes:
        'Waters and Soils never intersect once sorted at the Main Entrance drop-off zone, ensuring strict contamination control and one-piece flow.',
      render: () => (
        <div className="space-y-4">
          <div className="grid grid-cols-5 gap-2 text-center text-xs">
            {[
              '1. Single Intake\nMain Door',
              '2. Sorting Zone\n300 × 400 cm',
              '3. 240 cm Barrier\nZero Crossing',
              '4. Parallel Lanes\nRollers (3)',
              '5. Dual Exits\nExit 1 S / Exit 2 W',
            ].map((s, idx) => (
              <div
                key={s}
                className={`p-2.5 rounded-lg border font-semibold whitespace-pre-line ${
                  idx % 2 === 0 ? 'bg-slate-900 text-white border-slate-900' : 'bg-slate-100 text-slate-800 border-slate-200'
                }`}
              >
                {s}
              </div>
            ))}
          </div>
          <img src={img(2)} alt="240 cm Central Walkway" className="w-full max-h-[320px] object-cover rounded-lg border border-slate-200" />
        </div>
      ),
    },
    {
      id: 6,
      category: 'Main Hall — East Wing',
      title: 'Waters Lane Deep Dive (10 Stations + 60 cm Roller)',
      subtitle: '2 Reg + 4 Reg/Split + 4 Testing stations along a continuous 11.25 m conveyor.',
      notes:
        'Bottom two rows sit perpendicular facing the Main Door intake; upper three rows align parallel to the 60 cm roller with analysts seated on outer edges.',
      render: () => (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 items-center">
          <img src={img(3)} alt="Waters Lane" className="rounded-lg border border-slate-200 w-full aspect-video object-cover" />
          <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 text-xs space-y-2 text-slate-700">
            <div className="font-bold text-sm text-slate-900">Waters Lane Architecture</div>
            <p>• Row 1 (Y=13,750): H2O Reg 1 &amp; 2 perpendicular, analysts facing Main Door.</p>
            <p>• Row 2 (Y=11,850): H2O Reg/Split 1 &amp; 2 perpendicular, analysts facing Main Door.</p>
            <p>• Rows 3–5 (Y=9,150 / 6,650 / 4,150): Split 3–4 &amp; Test 1–4 parallel to roller, analysts on outer sides facing roller.</p>
            <p>• All 10 stations have PC + thermal label printer; direct dispatch via Exit Door 2.</p>
          </div>
        </div>
      ),
    },
    {
      id: 7,
      category: 'Main Hall — West Wing',
      title: 'Soils Lane Deep Dive (3 x 5 Array + Double-Deck Rollers)',
      subtitle: '15 uniform 60 x 130 cm benches, 2 dual-deck dry/wet rollers, and 50 x 50 cm benchtop fume hoods.',
      notes:
        'Lower roller deck (520 mm) moves dry soil samples; upper deck (920 mm) moves wet/prepared extracts. S8 and S11 host 50x50 cm benchtop fume hoods.',
      render: () => (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 items-center">
          <img src={img(4)} alt="Soils 3x5 Array" className="rounded-lg border border-slate-200 w-full aspect-video object-cover" />
          <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 text-xs space-y-2 text-slate-700">
            <div className="font-bold text-sm text-slate-900">Soils 3×5 Station Matrix</div>
            <p>• 3 columns × 5 rows of uniform 60 × 130 cm desks with 150 cm row gaps.</p>
            <p>• Row 1 (S1–S3) seated on bottom edge facing upward; Rows 2–5 seated on top edge facing downward.</p>
            <p>• S8 &amp; S11 hold 50 × 50 cm point-of-use benchtop fume hoods within the desk footprint.</p>
            <p>• Row 5 (S13–S15) houses Shakers &amp; Vialling-Up feeding Exit Door 1.</p>
          </div>
        </div>
      ),
    },
    {
      id: 8,
      category: 'Left Wing Specialist Prep',
      title: 'Sulphide, Drying & Grinding Wing',
      subtitle: 'Widened 1.50 x 5.40 m island (8 total PCs + Scan PC), retained ovens & grinders.',
      notes:
        'Sulphide island expansion adds 3 PCs while preserving 150 cm left/right aisles alongside the dividing bench utility sequence and retained Drying/Grinding rooms.',
      render: () => (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-2">
            <img src={img(5)} alt="Sulphide Area" className="rounded-lg border border-slate-200 w-full aspect-video object-cover" />
            <div className="text-xs text-slate-700 bg-slate-50 border border-slate-200 rounded-lg p-3">
              <strong>Sulphide (5,900 × 9,088 mm):</strong> 4 Wall PCs + 3 Island PCs (1.50 × 5.40 m) + Dividing PC 1 → 2 Shakers → 2 Sinks → TOC Vac Pump.
            </div>
          </div>
          <div className="space-y-2">
            <img src={img(6)} alt="Drying & Grinding Wing" className="rounded-lg border border-slate-200 w-full aspect-video object-cover" />
            <div className="text-xs text-slate-700 bg-slate-50 border border-slate-200 rounded-lg p-3">
              <strong>Drying &amp; Grinding:</strong> Retained 2 Ovens, 2 Grinders, 108×108 cm Hood + Post-Grind Scan PC (60 × 120 cm).
            </div>
          </div>
        </div>
      ),
    },
    {
      id: 9,
      category: 'Sample Control & Outbound',
      title: 'Sample Control, Cold Storage & North Logistics Wall',
      subtitle: '400 cm On-Hold racks (60 cm path), 500 L fridge, External Cold Storage & Rapid Moisture.',
      notes:
        'North wall anchors Exit Door 1 (Soils), Rapid Moisture (344x77 cm), Logistics WS 1 & 2 (70x210 cm), 5-tier shelf, and Exit Door 2 (Waters).',
      render: () => (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 items-center">
          <img src={img(7)} alt="Logistics & Dual Exits" className="rounded-lg border border-slate-200 w-full aspect-video object-cover" />
          <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 text-xs space-y-2 text-slate-700">
            <div className="font-bold text-sm text-slate-900">Control &amp; Outbound Capacity</div>
            <p>• On-Hold Storage: 2× 400 cm 6-tier racks separated by 60 cm walking path + 500 L tall fridge.</p>
            <p>• External Cold Storage: Retained 1,800 × 10,800 mm unit outside left exterior wall.</p>
            <p>• Rapid Moisture Bench (344 × 77 cm) + Logistics WS 1 &amp; 2 (70 × 210 cm) + 5-Tier Shelf (70 × 150 cm).</p>
          </div>
        </div>
      ),
    },
    {
      id: 10,
      category: 'People & Workplace',
      title: 'Merged CS Office, Modernized Canteen & 4 W/Cs',
      subtitle: '8,000 x 3,442 mm open-plan office (8 dual-screen desks) with direct door to Canteen.',
      notes:
        'Removing the Prep Manager / Lean dividing wall unites Admin and Customer Service teams with direct access to a modernized canteen and 4 upgraded W/Cs.',
      render: () => (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 items-center">
          <img src={img(8)} alt="Merged CS Office & Canteen" className="rounded-lg border border-slate-200 w-full aspect-video object-cover" />
          <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 text-xs space-y-2 text-slate-700">
            <div className="font-bold text-sm text-slate-900">Workplace Modernization</div>
            <p>• Merged CS / Admin Office: 8 workstations (2 rows × 4 desks, 150 × 70 cm) with 16 displays.</p>
            <p>• Direct connecting door opens straight into the modernized Canteen (kitchenette + 2 dining tables).</p>
            <p>• Upgraded Toilet Block (5,337 × 2,048 mm): 4 W/C cubicles + washbasins/boiler alcove + rear corridor.</p>
          </div>
        </div>
      ),
    },
    {
      id: 11,
      category: 'Interactive Digital Twin',
      title: 'Live 3D Walkthrough & Guided Video Tour',
      subtitle: 'Switch seamlessly to the real-time Three.js model, 8-chapter tour, and 60fps video capture.',
      notes:
        'Use the Launch 3D Guided Tour button below to demonstrate the interactive Three.js model, sample flow overlay, and still/video capture live.',
      render: () => (
        <div className="bg-slate-900 text-white rounded-xl p-6 space-y-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {[1, 3, 4, 8].map((id) => (
              <img key={id} src={img(id)} alt={`Chapter ${id}`} className="rounded-lg border border-slate-700 aspect-video object-cover" />
            ))}
          </div>
          <div className="flex flex-wrap items-center justify-between gap-4 pt-2">
            <div className="text-xs text-slate-300 max-w-xl">
              Explore orbit/cutaway controls, click any station for exact dimensions, run the 8-chapter Catmull-Rom guided tour, or record a 60fps video directly from the browser canvas.
            </div>
            <button
              onClick={onOpen3DTour}
              className="px-4 py-2 rounded-lg bg-white text-slate-900 font-bold text-xs flex items-center gap-2 hover:bg-slate-100"
            >
              Launch 3D Model &amp; Guided Tour <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      ),
    },
    {
      id: 12,
      category: 'Delivery & Governance',
      title: 'Equipment Schedule, CapEx Discipline & Rollout Roadmap',
      subtitle: 'Synchronized inventory tallies from data/layout_spec.json and 10-week phased execution.',
      notes:
        'Full equipment quantities tie 1:1 to Project_Vol_Equipment_Schedule.xlsx across all three tabs.',
      render: () => (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 text-xs">
          <div className="border border-slate-200 rounded-lg overflow-hidden">
            <table className="w-full text-left border-collapse">
              <thead className="bg-slate-900 text-white">
                <tr>
                  <th className="p-2">Category</th>
                  <th className="p-2">Count</th>
                  <th className="p-2">Scope</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 bg-white">
                {[
                  ['Waters Stations', '10', 'New Lean Fit-Out'],
                  ['Soils 3×5 Stations', '15', 'New Lean Fit-Out'],
                  ['Sulphide PCs (+ Scan)', '8 + 1', 'Expanded Island'],
                  ['CS Dual-Screen Desks', '8 (16 screens)', 'Merged Office'],
                  ['Roller Conveyors', '3 (1W + 2S)', 'Automated Flow'],
                  ['Fume Hoods', '3 (1Gr + 2x50cm)', '1 Retained + 2 New'],
                  ['Total PCs / Printers', `${totalPcs} / ${totalPrinters}`, 'Full LIMS Sync'],
                ].map(([a, b, c]) => (
                  <tr key={a}>
                    <td className="p-2 font-semibold text-slate-900">{a}</td>
                    <td className="p-2 font-mono">{b}</td>
                    <td className="p-2 text-slate-600">{c}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 space-y-2 text-slate-700">
            <div className="font-bold text-sm text-slate-900">10-Week Implementation Roadmap</div>
            <p>• <strong>Weeks 1–2:</strong> Demolish Team Leaders Office, stairs &amp; CS divider; flip D-DRY outward (+Y).</p>
            <p>• <strong>Weeks 3–5:</strong> M&amp;E first-fix (4 W/Cs, Sulphide sinks/TOC, 2× 50×50 cm LEV, linear LEDs) &amp; epoxy floor.</p>
            <p>• <strong>Weeks 6–8:</strong> Install white/grey benches, 3 rollers, 1.50×5.40 m island, 400 cm racks &amp; 8 CS desks.</p>
            <p>• <strong>Weeks 9–10:</strong> LIMS/IT commissioning (42 PCs, 23 printers), SOP sign-off &amp; Go-Live.</p>
          </div>
        </div>
      ),
    },
  ];

  const current = slides[index];

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'ArrowRight' || e.key === ' ') {
        e.preventDefault();
        setIndex((i) => Math.min(slides.length - 1, i + 1));
      } else if (e.key === 'ArrowLeft') {
        e.preventDefault();
        setIndex((i) => Math.max(0, i - 1));
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [slides.length]);

  return (
    <div className="min-h-[calc(100vh-4.25rem)] bg-slate-100 p-4 md:p-6 flex flex-col">
      <div className="max-w-6xl w-full mx-auto flex-1 flex flex-col gap-4">
        {/* Top Controls */}
        <div className="bg-white border border-slate-200 rounded-xl px-4 py-2.5 flex flex-wrap items-center justify-between gap-2 shadow-sm">
          <div className="flex items-center gap-2">
            <PresentationIcon className="w-4 h-4 text-blue-900" />
            <span className="text-xs font-bold text-slate-900">
              Slide {current.id} of {slides.length}
            </span>
            <span className="text-xs text-slate-400">•</span>
            <span className="text-xs text-slate-600 hidden sm:inline">Use ← / → or Space to navigate</span>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowNotes((v) => !v)}
              className={`px-2.5 py-1.5 rounded-md text-xs font-medium border flex items-center gap-1 ${
                showNotes ? 'bg-slate-900 text-white border-slate-900' : 'bg-white text-slate-700 border-slate-300'
              }`}
            >
              <FileText className="w-3.5 h-3.5" /> Speaker Notes
            </button>
            <button
              onClick={() => setIndex((i) => Math.max(0, i - 1))}
              disabled={index === 0}
              className="p-1.5 rounded-md border border-slate-300 bg-white disabled:opacity-40 hover:bg-slate-50"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <button
              onClick={() => setIndex((i) => Math.min(slides.length - 1, i + 1))}
              disabled={index === slides.length - 1}
              className="p-1.5 rounded-md border border-slate-300 bg-white disabled:opacity-40 hover:bg-slate-50"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
            <a
              href="/downloads/Project_Vol_Presentation.pptx"
              download
              className="px-3 py-1.5 rounded-md text-xs font-semibold bg-blue-900 hover:bg-blue-800 text-white flex items-center gap-1.5 shadow-sm"
            >
              <Download className="w-3.5 h-3.5" /> Download .pptx
            </a>
          </div>
        </div>

        {/* Slide Canvas */}
        <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden flex-1 flex flex-col">
          {current.id !== 1 && current.id !== 11 && (
            <div className="bg-slate-900 text-white px-6 py-4 flex items-center justify-between">
              <div>
                <div className="text-[10px] font-bold uppercase tracking-widest text-slate-400">
                  {current.category} • Project Vol
                </div>
                <h2 className="text-xl font-bold mt-0.5">{current.title}</h2>
                <p className="text-xs text-slate-300 mt-0.5">{current.subtitle}</p>
              </div>
              <div className="text-xs font-mono text-slate-400">
                {String(current.id).padStart(2, '0')} / 12
              </div>
            </div>
          )}
          <div className="p-6 flex-1">{current.render()}</div>
        </div>

        {/* Speaker Notes */}
        {showNotes && (
          <div className="bg-white border border-slate-200 rounded-xl p-3.5 text-xs text-slate-700 shadow-sm">
            <span className="font-bold uppercase tracking-wider text-[10px] text-slate-500 mr-2">
              Presenter Notes:
            </span>
            {current.notes}
          </div>
        )}

        {/* Slide Strip */}
        <div className="flex flex-wrap gap-1.5 justify-center">
          {slides.map((sl, idx) => (
            <button
              key={sl.id}
              onClick={() => setIndex(idx)}
              className={`px-2.5 py-1 rounded-md text-xs font-medium border transition ${
                idx === index
                  ? 'bg-slate-900 text-white border-slate-900'
                  : 'bg-white text-slate-700 border-slate-300 hover:bg-slate-50'
              }`}
            >
              {sl.id}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
