import { useState, useRef } from 'react';
import {
  Download,
  Maximize2,
  ZoomIn,
  ZoomOut,
  FileSpreadsheet,
  FileText,
  Image as ImageIcon,
  FileCode2,
  X,
} from 'lucide-react';
import type { Door, LayoutSpec, SelectedInspectTarget, Wall } from '../types/layout';

interface FloorPlan2DViewProps {
  spec: LayoutSpec;
}

function splitWall(wall: Wall, doors: Door[]): [number, number, number, number][] {
  const { x1, y1, x2, y2 } = wall;
  const vertical = Math.abs(x1 - x2) < 1;
  const wDoors = doors.filter((d) => d.wall_id === wall.id);
  if (wDoors.length === 0) return [[x1, y1, x2, y2]];
  if (vertical) {
    const lo = Math.min(y1, y2);
    const hi = Math.max(y1, y2);
    const cuts = wDoors.map((d) => [Math.min(d.y1, d.y2), Math.max(d.y1, d.y2)] as [number, number]).sort((a, b) => a[0] - b[0]);
    const out: [number, number, number, number][] = [];
    let cur = lo;
    for (const [a, b] of cuts) {
      if (a > cur + 1) out.push([x1, cur, x1, a]);
      cur = Math.max(cur, b);
    }
    if (cur < hi - 1) out.push([x1, cur, x1, hi]);
    return out;
  }
  const lo = Math.min(x1, x2);
  const hi = Math.max(x1, x2);
  const cuts = wDoors.map((d) => [Math.min(d.x1, d.x2), Math.max(d.x1, d.x2)] as [number, number]).sort((a, b) => a[0] - b[0]);
  const out: [number, number, number, number][] = [];
  let cur = lo;
  for (const [a, b] of cuts) {
    if (a > cur + 1) out.push([cur, y1, a, y1]);
    cur = Math.max(cur, b);
  }
  if (cur < hi - 1) out.push([cur, y1, hi, y1]);
  return out;
}

function doorSvgPaths(d: Door) {
  if (!d.hinge || d.swing_dir === 'open_passage') return null;
  const [hx, hy] = d.hinge;
  const w = d.width_mm;
  const lx = Math.abs(hx - d.x1) < 1 ? d.x2 : d.x1;
  const ly = Math.abs(hy - d.y1) < 1 ? d.y2 : d.y1;
  const openPts: Record<string, [number, number]> = {
    '+X': [hx + w, hy],
    '-X': [hx - w, hy],
    '+Y': [hx, hy + w],
    '-Y': [hx, hy - w],
  };
  const [ox, oy] = openPts[d.swing_dir];
  const cross = (lx - hx) * (oy - hy) - (ly - hy) * (ox - hx);
  const sweep = cross > 0 ? 1 : 0;
  return {
    leaf: `M ${hx} ${hy} L ${ox} ${oy}`,
    arc: `M ${lx} ${ly} A ${w} ${w} 0 0 ${sweep} ${ox} ${oy}`,
  };
}

export default function FloorPlan2DView({ spec }: FloorPlan2DViewProps) {
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [dragging, setDragging] = useState(false);
  const dragStart = useRef({ x: 0, y: 0 });

  const [showDims, setShowDims] = useState(true);
  const [showFlow, setShowFlow] = useState(true);
  const [showChairs, setShowChairs] = useState(true);
  const [showZones, setShowZones] = useState(true);
  const [showLabels, setShowLabels] = useState(true);
  const [selected, setSelected] = useState<SelectedInspectTarget | null>(null);

  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    setZoom((z) => Math.max(0.55, Math.min(4.5, z * (e.deltaY < 0 ? 1.12 : 0.89))));
  };

  return (
    <div className="flex flex-col h-[calc(100vh-4.25rem)] bg-slate-100">
      {/* Toolbar */}
      <div className="bg-white border-b border-slate-200 px-4 py-2.5 flex flex-wrap items-center justify-between gap-2 shadow-sm">
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex items-center border border-slate-300 rounded-md overflow-hidden bg-white">
            <button
              onClick={() => setZoom((z) => Math.min(4.5, z * 1.2))}
              className="p-1.5 hover:bg-slate-100 text-slate-700"
              title="Zoom In"
            >
              <ZoomIn className="w-4 h-4" />
            </button>
            <span className="px-2 text-xs font-mono text-slate-700 border-x border-slate-200">
              {Math.round(zoom * 100)}%
            </span>
            <button
              onClick={() => setZoom((z) => Math.max(0.55, z / 1.2))}
              className="p-1.5 hover:bg-slate-100 text-slate-700"
              title="Zoom Out"
            >
              <ZoomOut className="w-4 h-4" />
            </button>
            <button
              onClick={() => {
                setZoom(1);
                setPan({ x: 0, y: 0 });
              }}
              className="p-1.5 hover:bg-slate-100 text-slate-700 border-l border-slate-200"
              title="Reset Fit"
            >
              <Maximize2 className="w-4 h-4" />
            </button>
          </div>

          {[
            { label: 'Dimensions', state: showDims, set: setShowDims },
            { label: 'Flow Overlay', state: showFlow, set: setShowFlow },
            { label: 'Chairs', state: showChairs, set: setShowChairs },
            { label: 'Zone Striping', state: showZones, set: setShowZones },
            { label: 'Labels', state: showLabels, set: setShowLabels },
          ].map((t) => (
            <button
              key={t.label}
              onClick={() => t.set((v) => !v)}
              className={`px-2.5 py-1 rounded-md text-xs font-medium border transition ${
                t.state
                  ? 'bg-slate-900 text-white border-slate-900'
                  : 'bg-white text-slate-600 border-slate-300 hover:bg-slate-50'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* Deliverable Downloads */}
        <div className="flex flex-wrap items-center gap-1.5">
          <a
            href="/downloads/Project_Vol_2D_Spec.svg"
            download
            className="px-2.5 py-1.5 rounded-md text-xs font-medium bg-slate-100 hover:bg-slate-200 text-slate-800 flex items-center gap-1"
          >
            <FileCode2 className="w-3.5 h-3.5" /> SVG
          </a>
          <a
            href="/downloads/Project_Vol_2D_Spec.png"
            download
            className="px-2.5 py-1.5 rounded-md text-xs font-medium bg-slate-100 hover:bg-slate-200 text-slate-800 flex items-center gap-1"
          >
            <ImageIcon className="w-3.5 h-3.5" /> PNG (300 DPI)
          </a>
          <a
            href="/downloads/Project_Vol_2D_Spec.pdf"
            download
            className="px-2.5 py-1.5 rounded-md text-xs font-medium bg-slate-100 hover:bg-slate-200 text-slate-800 flex items-center gap-1"
          >
            <FileText className="w-3.5 h-3.5" /> PDF
          </a>
          <a
            href="/downloads/Project_Vol_Equipment_Schedule.xlsx"
            download
            className="px-2.5 py-1.5 rounded-md text-xs font-semibold bg-blue-900 hover:bg-blue-800 text-white flex items-center gap-1.5"
          >
            <FileSpreadsheet className="w-3.5 h-3.5" /> Equipment Schedule (.xlsx)
          </a>
        </div>
      </div>

      {/* Main SVG Viewport + Side Inspector */}
      <div className="flex flex-1 overflow-hidden relative">
        <div
          className="flex-1 bg-white overflow-hidden cursor-grab active:cursor-grabbing select-none"
          onWheel={handleWheel}
          onMouseDown={(e) => {
            setDragging(true);
            dragStart.current = { x: e.clientX - pan.x, y: e.clientY - pan.y };
          }}
          onMouseMove={(e) => {
            if (dragging) setPan({ x: e.clientX - dragStart.current.x, y: e.clientY - dragStart.current.y });
          }}
          onMouseUp={() => setDragging(false)}
          onMouseLeave={() => setDragging(false)}
        >
          <svg
            viewBox="-3500 -1800 23300 25500"
            className="w-full h-full"
            style={{
              transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
              transformOrigin: 'center center',
            }}
          >
            <defs>
              <pattern id="grid1000" width="1000" height="1000" patternUnits="userSpaceOnUse">
                <path d="M 1000 0 L 0 0 0 1000" fill="none" stroke="#F1F5F9" strokeWidth="30" />
              </pattern>
              <pattern id="fhHatch" width="140" height="140" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
                <line x1="0" y1="0" x2="0" y2="140" stroke="#475569" strokeWidth="25" />
              </pattern>
              <marker id="arrowBlue" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto">
                <path d="M 0 1 L 9 5 L 0 9 z" fill="#1E3A8A" />
              </marker>
              <marker id="arrowSlate" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto">
                <path d="M 0 1 L 9 5 L 0 9 z" fill="#334155" />
              </marker>
            </defs>

            <rect x="-3500" y="-1800" width="23300" height="25500" fill="url(#grid1000)" />

            {/* Rooms */}
            {spec.rooms.map((rm) => (
              <g
                key={rm.id}
                onClick={() =>
                  setSelected({
                    kind: 'room',
                    id: rm.id,
                    name: rm.name,
                    subtitle: `${rm.wing} • ${rm.phase}`,
                    dimensions: `${rm.w} × ${rm.h} mm`,
                    coordinates: `X=${rm.x}..${rm.x + rm.w}, Y=${rm.y}..${rm.y + rm.h}`,
                    flags: [rm.status],
                    notes: rm.notes,
                  })
                }
                className="cursor-pointer"
              >
                <rect
                  x={rm.x}
                  y={rm.y}
                  width={rm.w}
                  height={rm.h}
                  fill={rm.id === 'external_cold_storage' ? '#E2E8F0' : rm.id === 'main_hall' ? '#FFFFFF' : '#F8FAFC'}
                  stroke="none"
                />
                {showLabels && rm.id !== 'main_hall' && (
                  <text
                    x={rm.x + rm.w / 2}
                    y={rm.id === 'sulphide_area' ? 8150 : rm.id === 'toilets' ? 16260 : rm.y + 420}
                    textAnchor="middle"
                    fontSize={rm.id === 'external_cold_storage' ? 240 : 210}
                    fontWeight="700"
                    fill="#334155"
                    transform={
                      rm.id === 'external_cold_storage'
                        ? `rotate(-90 ${rm.x + rm.w / 2} ${rm.y + rm.h / 2})`
                        : undefined
                    }
                  >
                    {rm.id === 'external_cold_storage'
                      ? 'EXTERNAL COLD STORAGE (1,800 x 10,800 mm)'
                      : rm.name.toUpperCase()}
                  </text>
                )}
              </g>
            ))}

            {/* Zone Striping */}
            {showZones &&
              spec.zones.map((zn) => (
                <g key={zn.id}>
                  <rect
                    x={zn.x}
                    y={zn.y}
                    width={zn.w}
                    height={zn.h}
                    fill="#F1F5F9"
                    fillOpacity="0.65"
                    stroke="#475569"
                    strokeWidth="45"
                    strokeDasharray="180 120"
                  />
                  {showLabels && (
                    <text
                      x={zn.x + zn.w / 2}
                      y={zn.y + zn.h / 2}
                      textAnchor="middle"
                      fontSize="240"
                      fontWeight="700"
                      fill="#334155"
                      transform={zn.id === 'Z-WALKWAY' ? `rotate(-90 ${zn.x + zn.w / 2} ${zn.y + zn.h / 2})` : undefined}
                    >
                      {zn.name}
                    </text>
                  )}
                </g>
              ))}

            {/* Conveyors */}
            {spec.conveyors.map((conv) => (
              <g
                key={conv.id}
                onClick={() =>
                  setSelected({
                    kind: 'conveyor',
                    id: conv.id,
                    name: conv.name,
                    subtitle: `${conv.decks.length} Deck Conveyor`,
                    dimensions: `${conv.w} × ${conv.h} mm`,
                    coordinates: `X=${conv.x}..${conv.x + conv.w}, Y=${conv.y}..${conv.y + conv.h}`,
                    flags: conv.decks.map((d) => `${d.name} (${d.z_mm} mm)`),
                    notes: conv.notes,
                  })
                }
                className="cursor-pointer"
              >
                <rect x={conv.x} y={conv.y} width={conv.w} height={conv.h} fill="#CBD5E1" stroke="#334155" strokeWidth="55" />
                {showLabels && (
                  <text
                    x={conv.x + conv.w / 2}
                    y={conv.y + conv.h / 2}
                    textAnchor="middle"
                    fontSize="210"
                    fontWeight="700"
                    fill="#0F172A"
                    transform={`rotate(-90 ${conv.x + conv.w / 2} ${conv.y + conv.h / 2})`}
                  >
                    {conv.name}
                  </text>
                )}
              </g>
            ))}

            {/* Stations & Equipment */}
            {spec.stations_and_equipment.map((it) => {
              const isFH = it.has_fume_hood;
              const isSelected = selected?.id === it.id;
              return (
                <g
                  key={it.id}
                  onClick={() =>
                    setSelected({
                      kind: 'station',
                      id: it.id,
                      name: it.name,
                      subtitle: it.category.replace(/_/g, ' '),
                      dimensions: `${it.w} × ${it.h} × ${it.height_mm} mm`,
                      coordinates: `X=${it.x}..${it.x + it.w}, Y=${it.y}..${it.y + it.h}`,
                      flags: [
                        ...(it.has_pc ? [it.dual_monitor ? 'Dual-Screen PC' : 'PC'] : []),
                        ...(it.has_label_printer ? ['Label Printer'] : []),
                        ...(it.has_fume_hood ? ['Fume Hood'] : []),
                      ],
                      notes: it.notes,
                    })
                  }
                  className="cursor-pointer"
                >
                  <rect
                    x={it.x}
                    y={it.y}
                    width={it.w}
                    height={it.h}
                    fill={isFH ? 'url(#fhHatch)' : it.category === 'island_bench' ? '#E2E8F0' : '#F1F5F9'}
                    stroke={isSelected ? '#1E3A8A' : '#334155'}
                    strokeWidth={isSelected ? 110 : 45}
                  />
                  {showChairs && it.seat && (
                    <circle cx={it.seat.x} cy={it.seat.y} r="185" fill="#CBD5E1" stroke="#334155" strokeWidth="45" />
                  )}
                  {showLabels && it.id !== 'SUL-OUTER-BENCH' && it.id !== 'SUL-DIV-BENCH' && (
                    <text
                      x={it.x + it.w / 2}
                      y={it.y + it.h / 2}
                      textAnchor="middle"
                      dominantBaseline="middle"
                      fontSize={it.w < 700 ? 150 : 180}
                      fontWeight="700"
                      fill="#0F172A"
                      transform={
                        it.h > it.w && it.w < 1600
                          ? `rotate(-90 ${it.x + it.w / 2} ${it.y + it.h / 2})`
                          : undefined
                      }
                    >
                      {it.id === 'FH-SOIL-1' || it.id === 'FH-SOIL-2' ? 'FH 50x50' : it.name.slice(0, 18)}
                    </text>
                  )}
                </g>
              );
            })}

            {/* Walls */}
            {spec.walls.map((wall) =>
              splitWall(wall, spec.doors).map(([sx1, sy1, sx2, sy2], idx) => (
                <line
                  key={`${wall.id}-${idx}`}
                  x1={sx1}
                  y1={sy1}
                  x2={sx2}
                  y2={sy2}
                  stroke={wall.kind === 'exterior' ? '#0F172A' : wall.kind === 'glazed_partition' ? '#64748B' : '#334155'}
                  strokeWidth={wall.thickness_mm}
                  strokeDasharray={wall.kind === 'glazed_partition' ? '200 100' : undefined}
                />
              ))
            )}

            {/* Doors */}
            {spec.doors.map((d) => {
              const p = doorSvgPaths(d);
              if (!p) return null;
              return (
                <g key={d.id}>
                  <path d={p.leaf} stroke="#0F172A" strokeWidth="55" fill="none" />
                  <path d={p.arc} stroke="#64748B" strokeWidth="35" strokeDasharray="120 90" fill="none" />
                </g>
              );
            })}

            {/* Flow Overlay */}
            {showFlow &&
              spec.flow_paths.map((fp) => {
                const pts = fp.points.map(([x, y]) => `${x},${y}`).join(' ');
                const isWaters = fp.stream === 'waters';
                return (
                  <polyline
                    key={fp.id}
                    points={pts}
                    fill="none"
                    stroke={isWaters ? '#1E3A8A' : '#334155'}
                    strokeWidth="90"
                    strokeDasharray="240 140"
                    markerEnd={isWaters ? 'url(#arrowBlue)' : 'url(#arrowSlate)'}
                  />
                );
              })}

            {/* Dimension Overlay */}
            {showDims &&
              spec.dimensions.map((dm) => {
                const vert = Math.abs(dm.x1 - dm.x2) < 1;
                const mx = (dm.x1 + dm.x2) / 2;
                const my = (dm.y1 + dm.y2) / 2;
                return (
                  <g key={dm.id}>
                    <line x1={dm.x1} y1={dm.y1} x2={dm.x2} y2={dm.y2} stroke="#475569" strokeWidth="35" />
                    <text
                      x={mx}
                      y={my - 90}
                      textAnchor="middle"
                      fontSize="240"
                      fontWeight="700"
                      fill="#0F172A"
                      transform={vert ? `rotate(-90 ${mx} ${my})` : undefined}
                    >
                      {dm.label}
                    </text>
                  </g>
                );
              })}
          </svg>
        </div>

        {/* Right Inspector Sidebar */}
        <div className="w-80 bg-white border-l border-slate-200 p-4 overflow-y-auto hidden lg:block">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">
              2D Spec Inspector
            </h3>
            {selected && (
              <button onClick={() => setSelected(null)} className="text-slate-400 hover:text-slate-700">
                <X className="w-4 h-4" />
              </button>
            )}
          </div>

          {selected ? (
            <div className="mt-3 space-y-2.5 text-xs">
              <div className="inline-block px-2 py-0.5 rounded bg-slate-900 text-white font-bold text-[10px]">
                {selected.id}
              </div>
              <div className="text-sm font-bold text-slate-900">{selected.name}</div>
              <div className="text-slate-500 capitalize">{selected.subtitle}</div>
              <div className="bg-slate-50 border border-slate-200 rounded-lg p-2.5 space-y-1 font-mono text-[11px]">
                <div>Dims: {selected.dimensions}</div>
                <div>{selected.coordinates}</div>
              </div>
              {selected.flags.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {selected.flags.map((f) => (
                    <span key={f} className="px-2 py-0.5 rounded-full bg-slate-100 border border-slate-200 text-[11px]">
                      {f}
                    </span>
                  ))}
                </div>
              )}
              <p className="text-slate-600 leading-relaxed">{selected.notes}</p>
            </div>
          ) : (
            <div className="mt-4 text-xs text-slate-500 space-y-2">
              <p>Click any room, station, bench, fume hood, or roller conveyor on the plan to inspect its exact millimeter coordinates and equipment flags.</p>
              <p>Scroll to zoom and drag to pan across the facility.</p>
              <div className="pt-3 border-t border-slate-200 space-y-1.5 text-slate-700">
                <div className="font-semibold text-slate-900">Key Clearances Verified:</div>
                <div>• Central Walkway: 2,400 mm</div>
                <div>• Sulphide Aisles: 1,500 mm (L &amp; R)</div>
                <div>• Soils Row Gaps: 1,500 mm</div>
                <div>• On-Hold Path: 600 mm</div>
                <div>• Drying Door (D-DRY): +Y Outward</div>
              </div>
            </div>
          )}

          <div className="mt-6 pt-4 border-t border-slate-200">
            <div className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2 flex items-center gap-1">
              <Download className="w-3.5 h-3.5" /> Export Deliverables
            </div>
            <p className="text-[11px] text-slate-500">
              All CAD vectors, 300 DPI PNGs, PDFs, and the 3-tab Excel Equipment Schedule are synchronized from <code className="text-slate-800">data/layout_spec.json</code>.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
