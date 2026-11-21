import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import * as THREE from 'three';
import type { OrbitControls as OrbitControlsImpl } from 'three-stdlib';
import {
  Camera,
  Eye,
  Layers,
  Pause,
  Play,
  RotateCcw,
  Route,
  Video,
  Square,
  X,
  CheckCircle2,
  Compass,
} from 'lucide-react';
import type {
  Conveyor,
  Door,
  FlowPath,
  LayoutSpec,
  Room,
  SelectedInspectTarget,
  StationEquipment,
  Wall,
} from '../types/layout';

interface Lab3DViewerProps {
  spec: LayoutSpec;
  onCaptureStills: (stills: Record<number, string>) => void;
}

type WallMode = 'cutaway' | 'full' | 'roof' | 'topdown';

const M = 1 / 1000;

function splitWall(wall: Wall, doors: Door[]): [number, number, number, number][] {
  const { x1, y1, x2, y2 } = wall;
  const vertical = Math.abs(x1 - x2) < 1;
  const wDoors = doors.filter((d) => d.wall_id === wall.id);
  if (wDoors.length === 0) return [[x1, y1, x2, y2]];

  if (vertical) {
    const lo = Math.min(y1, y2);
    const hi = Math.max(y1, y2);
    const cuts = wDoors
      .map((d) => [Math.min(d.y1, d.y2), Math.max(d.y1, d.y2)] as [number, number])
      .sort((a, b) => a[0] - b[0]);
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
  const cuts = wDoors
    .map((d) => [Math.min(d.x1, d.x2), Math.max(d.x1, d.x2)] as [number, number])
    .sort((a, b) => a[0] - b[0]);
  const out: [number, number, number, number][] = [];
  let cur = lo;
  for (const [a, b] of cuts) {
    if (a > cur + 1) out.push([cur, y1, a, y1]);
    cur = Math.max(cur, b);
  }
  if (cur < hi - 1) out.push([cur, y1, hi, y1]);
  return out;
}

function WallMesh({ wall, doors, wallHeightM }: { wall: Wall; doors: Door[]; wallHeightM: number }) {
  if (wall.kind === 'external_enclosure') return null;
  const segs = useMemo(() => splitWall(wall, doors), [wall, doors]);
  const isGlass = wall.kind === 'glazed_partition';
  const t = wall.thickness_mm * M;
  const h = Math.min(wallHeightM, wall.height_mm * M);
  const wDoors = doors.filter((d) => d.wall_id === wall.id);

  return (
    <group>
      {segs.map(([sx1, sy1, sx2, sy2], idx) => {
        const len = Math.hypot(sx2 - sx1, sy2 - sy1) * M;
        const cx = ((sx1 + sx2) * 0.5) * M;
        const cz = ((sy1 + sy2) * 0.5) * M;
        const vertical = Math.abs(sx1 - sx2) < 1;
        return (
          <mesh key={`${wall.id}-${idx}`} position={[cx, h * 0.5, cz]} castShadow receiveShadow>
            <boxGeometry args={[vertical ? t : len, h, vertical ? len : t]} />
            {isGlass ? (
              <meshPhysicalMaterial
                color="#E2E8F0"
                transparent
                opacity={0.42}
                roughness={0.12}
                metalness={0.05}
              />
            ) : (
              <meshStandardMaterial color="#F8FAFC" roughness={0.7} />
            )}
          </mesh>
        );
      })}
      {/* Lintels above doors in full/roof mode */}
      {h > 2.25 &&
        wDoors.map((d) => {
          const dh = d.height_mm * M;
          const lh = h - dh;
          if (lh <= 0.05) return null;
          const vertical = Math.abs(d.x1 - d.x2) < 1;
          const len = Math.hypot(d.x2 - d.x1, d.y2 - d.y1) * M;
          const cx = ((d.x1 + d.x2) * 0.5) * M;
          const cz = ((d.y1 + d.y2) * 0.5) * M;
          return (
            <mesh key={`lintel-${d.id}`} position={[cx, dh + lh * 0.5, cz]} castShadow>
              <boxGeometry args={[vertical ? t : len, lh, vertical ? len : t]} />
              <meshStandardMaterial color={isGlass ? '#E2E8F0' : '#F8FAFC'} roughness={0.65} />
            </mesh>
          );
        })}
    </group>
  );
}

function DoorLeafMesh({ door, wallHeightM }: { door: Door; wallHeightM: number }) {
  if (!door.hinge || door.swing_dir === 'open_passage') return null;
  const [hxMm, hyMm] = door.hinge;
  const w = door.width_mm * M;
  const h = Math.min(wallHeightM - 0.05, door.height_mm * M);
  let cx = hxMm * M;
  let cz = hyMm * M;
  let sx = 0.045;
  let sz = 0.045;
  if (door.swing_dir === '+X') {
    cx += w * 0.5;
    sx = w;
  } else if (door.swing_dir === '-X') {
    cx -= w * 0.5;
    sx = w;
  } else if (door.swing_dir === '+Y') {
    cz += w * 0.5;
    sz = w;
  } else if (door.swing_dir === '-Y') {
    cz -= w * 0.5;
    sz = w;
  }

  return (
    <mesh position={[cx, h * 0.5, cz]} castShadow>
      <boxGeometry args={[sx, h, sz]} />
      <meshStandardMaterial color="#E2E8F0" roughness={0.45} metalness={0.05} />
    </mesh>
  );
}

function ConveyorMesh({
  conv,
  isSelected,
  onSelect,
}: {
  conv: Conveyor;
  isSelected: boolean;
  onSelect: (t: SelectedInspectTarget) => void;
}) {
  const traysRef = useRef<THREE.Group>(null);
  const cx = (conv.x + conv.w * 0.5) * M;
  const cz = (conv.y + conv.h * 0.5) * M;
  const w = conv.w * M;
  const len = conv.h * M;
  const trayCount = 5;

  useFrame((state) => {
    if (!traysRef.current) return;
    const t = state.clock.getElapsedTime();
    const speed = 0.55;
    const span = len - 0.8;
    traysRef.current.children.forEach((child, idx) => {
      const deckIdx = Number(child.userData.deckIdx ?? 0);
      const slot = Number(child.userData.slot ?? idx);
      const offset = ((slot / trayCount + t * speed * 0.09 + deckIdx * 0.12) % 1) * span;
      // Moving south -> north (-Z)
      child.position.z = cz + len * 0.5 - 0.4 - offset;
    });
  });

  const handleSelect = (e: { stopPropagation: () => void }) => {
    e.stopPropagation();
    onSelect({
      kind: 'conveyor',
      id: conv.id,
      name: conv.name,
      subtitle: `${conv.decks.length} Deck Roller Conveyor`,
      dimensions: `${conv.w} × ${conv.h} mm`,
      coordinates: `X=${conv.x}..${conv.x + conv.w} mm, Y=${conv.y}..${conv.y + conv.h} mm`,
      flags: conv.decks.map((d) => `${d.name} @ ${d.z_mm} mm`),
      notes: conv.notes,
    });
  };

  const rollerCount = Math.floor(len / 0.45);

  return (
    <group onClick={handleSelect}>
      {/* Support legs */}
      {[-len * 0.46, 0, len * 0.46].map((dz, i) => (
        <group key={i}>
          <mesh position={[cx - w * 0.42, 0.45, cz + dz]} castShadow>
            <boxGeometry args={[0.05, 0.9, 0.05]} />
            <meshStandardMaterial color="#64748B" metalness={0.65} roughness={0.35} />
          </mesh>
          <mesh position={[cx + w * 0.42, 0.45, cz + dz]} castShadow>
            <boxGeometry args={[0.05, 0.9, 0.05]} />
            <meshStandardMaterial color="#64748B" metalness={0.65} roughness={0.35} />
          </mesh>
        </group>
      ))}

      {/* Decks + side rails + brushed steel rollers */}
      {conv.decks.map((deck, dIdx) => {
        const yPos = deck.z_mm * M;
        return (
          <group key={deck.name}>
            <mesh position={[cx - w * 0.46, yPos, cz]} castShadow receiveShadow>
              <boxGeometry args={[0.04, 0.07, len]} />
              <meshStandardMaterial color={isSelected ? '#1E3A8A' : '#94A3B8'} metalness={0.7} roughness={0.3} />
            </mesh>
            <mesh position={[cx + w * 0.46, yPos, cz]} castShadow receiveShadow>
              <boxGeometry args={[0.04, 0.07, len]} />
              <meshStandardMaterial color={isSelected ? '#1E3A8A' : '#94A3B8'} metalness={0.7} roughness={0.3} />
            </mesh>
            {Array.from({ length: rollerCount }).map((_, rIdx) => (
              <mesh
                key={rIdx}
                position={[cx, yPos, cz - len * 0.48 + rIdx * 0.45]}
                rotation={[0, 0, Math.PI * 0.5]}
              >
                <cylinderGeometry args={[0.022, 0.022, w - 0.09, 8]} />
                <meshStandardMaterial color="#9CA3AF" metalness={0.8} roughness={0.25} />
              </mesh>
            ))}
          </group>
        );
      })}

      {/* Animated Sample Trays */}
      <group ref={traysRef}>
        {conv.decks.flatMap((deck, dIdx) =>
          Array.from({ length: trayCount }).map((_, slot) => (
            <mesh
              key={`tray-${dIdx}-${slot}`}
              position={[cx, deck.z_mm * M + 0.065, cz]}
              userData={{ deckIdx: dIdx, slot }}
              castShadow
            >
              <boxGeometry args={[0.34, 0.09, 0.42]} />
              <meshStandardMaterial
                color={
                  deck.stream === 'soils_dry'
                    ? '#CBD5E1'
                    : deck.stream === 'soils_wet'
                    ? '#475569'
                    : '#E2E8F0'
                }
                roughness={0.4}
              />
            </mesh>
          ))
        )}
      </group>
    </group>
  );
}

function StationMesh({
  item,
  isSelected,
  onSelect,
}: {
  item: StationEquipment;
  isSelected: boolean;
  onSelect: (t: SelectedInspectTarget) => void;
}) {
  const x = (item.x + item.w * 0.5) * M;
  const z = (item.y + item.h * 0.5) * M;
  const w = item.w * M;
  const d = item.h * M;
  const y0 = item.elev_mm * M;
  const h = item.height_mm * M;
  const yTop = y0 + h;
  const cat = item.category;

  const handleSelect = (e: { stopPropagation: () => void }) => {
    e.stopPropagation();
    const flags: string[] = [];
    if (item.retained) flags.push('Retained Equipment');
    if (item.has_pc) flags.push(item.dual_monitor ? 'Dual-Screen PC' : 'Single PC');
    if (item.has_label_printer) flags.push('Label Printer');
    if (item.has_fume_hood) flags.push('Fume Hood LEV');
    if (item.has_shaker) flags.push('Orbital Shaker');
    if (item.has_sink) flags.push('Wash Sink');
    if (item.has_vacuum_pump) flags.push('TOC Vacuum Pump');
    if (item.has_barcode_scanner) flags.push('Barcode Scanner');

    onSelect({
      kind: 'station',
      id: item.id,
      name: item.name,
      subtitle: item.category.replace(/_/g, ' ').toUpperCase(),
      dimensions: `${item.w} × ${item.h} × ${item.height_mm} mm`,
      coordinates: `X=${item.x}..${item.x + item.w}, Y=${item.y}..${item.y + item.h}, Elev=${item.elev_mm} mm`,
      flags,
      notes: item.notes,
    });
  };

  const chairRotY = useMemo(() => {
    if (!item.seat) return 0;
    const map: Record<string, number> = {
      '-Y': Math.PI,
      '+Y': 0,
      '+X': Math.PI * 0.5,
      '-X': -Math.PI * 0.5,
    };
    return map[item.seat.facing] ?? 0;
  }, [item.seat]);

  const highlightColor = isSelected ? '#1E3A8A' : undefined;

  return (
    <group>
      <group onClick={handleSelect}>
        {/* Bench / Desk / Table / Alcove */}
        {[
          'bench',
          'island_bench',
          'waters_station',
          'soils_station',
          'logistics_station',
          'sulphide_scan_pc',
          'office_desk',
          'dining_table',
          'kitchenette',
          'wash_alcove',
        ].includes(cat) && (
          <>
            {cat !== 'dining_table' ? (
              <mesh position={[x, y0 + (h - 0.045) * 0.5, z]} castShadow receiveShadow>
                <boxGeometry args={[w - 0.03, h - 0.045, d - 0.03]} />
                <meshStandardMaterial color={highlightColor ?? '#F1F5F9'} roughness={0.55} />
              </mesh>
            ) : (
              [
                [-w * 0.42, -d * 0.38],
                [w * 0.42, -d * 0.38],
                [-w * 0.42, d * 0.38],
                [w * 0.42, d * 0.38],
              ].map(([lx, lz], i) => (
                <mesh key={i} position={[x + lx, y0 + h * 0.46, z + lz]} castShadow>
                  <boxGeometry args={[0.05, h - 0.04, 0.05]} />
                  <meshStandardMaterial color="#94A3B8" metalness={0.6} roughness={0.35} />
                </mesh>
              ))
            )}
            <mesh position={[x, yTop - 0.022, z]} castShadow receiveShadow>
              <boxGeometry args={[w, 0.045, d]} />
              <meshStandardMaterial color={highlightColor ?? '#D6D9DF'} roughness={0.38} />
            </mesh>
          </>
        )}

        {/* Fume Hoods (frosted glass sash + cabinet) */}
        {(cat === 'fume_hood' || cat === 'benchtop_fume_hood') && (
          <>
            <mesh position={[x, y0 + 0.09, z]} castShadow receiveShadow>
              <boxGeometry args={[w, 0.18, d]} />
              <meshStandardMaterial color={highlightColor ?? '#E2E8F0'} roughness={0.45} />
            </mesh>
            <mesh position={[x, y0 + 0.18 + (h - 0.28) * 0.5, z]} castShadow>
              <boxGeometry args={[w - 0.03, h - 0.28, d - 0.03]} />
              <meshPhysicalMaterial color="#E2E8F0" transparent opacity={0.48} roughness={0.14} />
            </mesh>
            <mesh position={[x, yTop - 0.05, z]} castShadow>
              <boxGeometry args={[w, 0.1, d]} />
              <meshStandardMaterial color={highlightColor ?? '#CBD5E1'} roughness={0.4} />
            </mesh>
          </>
        )}

        {/* Ovens, Grinders, 500L Fridge */}
        {(cat === 'drying_oven' || cat === 'grinder' || cat === 'fridge') && (
          <group>
            <mesh position={[x, y0 + h * 0.5, z]} castShadow receiveShadow>
              <boxGeometry args={[w, h, d]} />
              <meshStandardMaterial color={highlightColor ?? '#CBD5E1'} metalness={0.68} roughness={0.32} />
            </mesh>
            <mesh position={[x, y0 + h * 0.55, z + d * 0.505]}>
              <boxGeometry args={[w * 0.72, h * 0.55, 0.02]} />
              <meshStandardMaterial color="#94A3B8" metalness={0.82} roughness={0.25} />
            </mesh>
          </group>
        )}

        {/* Multi-Tier Racks (6-tier On-Hold & 5-tier Logistics) */}
        {cat === 'storage_rack' && (
          <group>
            {[
              [-w * 0.48, -d * 0.45],
              [w * 0.48, -d * 0.45],
              [-w * 0.48, d * 0.45],
              [w * 0.48, d * 0.45],
            ].map(([px, pz], idx) => (
              <mesh key={idx} position={[x + px, y0 + h * 0.5, z + pz]} castShadow>
                <boxGeometry args={[0.04, h, 0.04]} />
                <meshStandardMaterial color="#64748B" metalness={0.7} roughness={0.35} />
              </mesh>
            ))}
            {Array.from({ length: item.tiers ?? 5 }).map((_, tIdx, arr) => {
              const sy = y0 + 0.12 + ((h - 0.22) * tIdx) / Math.max(1, arr.length - 1);
              return (
                <group key={tIdx}>
                  <mesh position={[x, sy, z]} castShadow receiveShadow>
                    <boxGeometry args={[w, 0.03, d]} />
                    <meshStandardMaterial color={highlightColor ?? '#CBD5E1'} roughness={0.45} />
                  </mesh>
                  {tIdx < arr.length - 1 && (
                    <mesh position={[x - w * 0.22, sy + 0.11, z]} castShadow>
                      <boxGeometry args={[w * 0.35, 0.18, d * 0.7]} />
                      <meshStandardMaterial color="#E2E8F0" roughness={0.6} />
                    </mesh>
                  )}
                </group>
              );
            })}
          </group>
        )}

        {/* WC Cubicles */}
        {cat === 'wc_cubicle' && (
          <mesh position={[x, y0 + h * 0.5, z]} castShadow receiveShadow>
            <boxGeometry args={[w, h, d]} />
            <meshStandardMaterial color={highlightColor ?? '#F8FAFC'} roughness={0.6} />
          </mesh>
        )}

        {/* Benchtop Shakers, Sinks, TOC Pump, Sulphide PC pads */}
        {(cat === 'shaker' || cat === 'sink' || cat === 'toc_station' || cat === 'sulphide_pc') && (
          <mesh position={[x, y0 + 0.11, z]} castShadow>
            <boxGeometry args={[w - 0.08, 0.2, d - 0.08]} />
            <meshStandardMaterial
              color={highlightColor ?? (cat === 'sink' ? '#9CA3AF' : '#E2E8F0')}
              metalness={cat === 'sink' ? 0.85 : 0.2}
              roughness={cat === 'sink' ? 0.25 : 0.5}
            />
          </mesh>
        )}

        {/* Monitors (Single or Dual-Screen) */}
        {item.has_pc &&
          (item.dual_monitor ? (
            <group position={[x, yTop, z]}>
              {[-0.27, 0.27].map((dx, i) => (
                <group key={i} position={[dx, 0.26, -0.05]}>
                  <mesh castShadow>
                    <boxGeometry args={[0.48, 0.29, 0.03]} />
                    <meshStandardMaterial color="#1E293B" roughness={0.35} />
                  </mesh>
                  <mesh position={[0, -0.17, 0]}>
                    <boxGeometry args={[0.05, 0.16, 0.05]} />
                    <meshStandardMaterial color="#475569" />
                  </mesh>
                </group>
              ))}
            </group>
          ) : (
            <group position={[x, yTop + 0.24, z]} rotation={[0, d > w && cat === 'waters_station' ? Math.PI * 0.5 : 0, 0]}>
              <mesh castShadow>
                <boxGeometry args={[0.46, 0.28, 0.03]} />
                <meshStandardMaterial color="#1E293B" roughness={0.35} />
              </mesh>
              <mesh position={[0, -0.17, 0]}>
                <boxGeometry args={[0.04, 0.15, 0.04]} />
                <meshStandardMaterial color="#475569" />
              </mesh>
            </group>
          ))}

        {/* Thermal Label Printer */}
        {item.has_label_printer && (
          <mesh position={[x - w * 0.32, yTop + 0.085, z - d * 0.24]} castShadow>
            <boxGeometry args={[0.18, 0.17, 0.2]} />
            <meshStandardMaterial color="#94A3B8" roughness={0.4} />
          </mesh>
        )}
      </group>

      {/* Matte Charcoal Ergonomic Chair */}
      {item.seat && (
        <group position={[item.seat.x * M, 0, item.seat.y * M]} rotation={[0, chairRotY, 0]}>
          <mesh position={[0, 0.22, 0]} castShadow>
            <cylinderGeometry args={[0.04, 0.22, 0.42, 10]} />
            <meshStandardMaterial color="#64748B" metalness={0.5} roughness={0.4} />
          </mesh>
          <mesh position={[0, 0.46, 0]} castShadow>
            <boxGeometry args={[0.4, 0.06, 0.4]} />
            <meshStandardMaterial color="#334155" roughness={0.6} />
          </mesh>
          <mesh position={[0, 0.72, -0.18]} castShadow>
            <boxGeometry args={[0.38, 0.44, 0.05]} />
            <meshStandardMaterial color="#334155" roughness={0.6} />
          </mesh>
        </group>
      )}
    </group>
  );
}

function FlowPathOverlay({ paths }: { paths: FlowPath[] }) {
  const dotsRef = useRef<THREE.Group>(null);

  const curves = useMemo(() => {
    return paths.map((fp) => {
      const vecs = fp.points.map(([px, py]) => new THREE.Vector3(px * M, 0.045, py * M));
      const curve = new THREE.CatmullRomCurve3(vecs, false, 'catmullrom', 0.08);
      const tubeGeo = new THREE.TubeGeometry(curve, 64, 0.045, 8, false);
      return { fp, tubeGeo, curve };
    });
  }, [paths]);

  useFrame((state) => {
    if (!dotsRef.current) return;
    const t = state.clock.getElapsedTime();
    dotsRef.current.children.forEach((mesh, idx) => {
      const cIdx = Number(mesh.userData.cIdx ?? 0);
      const pIdx = Number(mesh.userData.pIdx ?? idx);
      const u = (t * 0.22 + pIdx * 0.25) % 1;
      const pt = curves[cIdx]?.curve.getPointAt(u);
      if (pt) mesh.position.copy(pt);
    });
  });

  return (
    <group>
      {curves.map(({ fp, tubeGeo }) => (
        <mesh key={fp.id} geometry={tubeGeo}>
          <meshStandardMaterial
            color={fp.stream === 'waters' ? '#2563EB' : fp.stream === 'soils' ? '#334155' : '#64748B'}
            emissive={fp.stream === 'waters' ? '#1E40AF' : '#1E293B'}
            emissiveIntensity={0.35}
            roughness={0.35}
          />
        </mesh>
      ))}
      <group ref={dotsRef}>
        {curves.flatMap(({ fp }, cIdx) =>
          [0, 1, 2, 3].map((pIdx) => (
            <mesh key={`${fp.id}-orb-${pIdx}`} userData={{ cIdx, pIdx }}>
              <sphereGeometry args={[0.13, 12, 12]} />
              <meshStandardMaterial
                color={fp.stream === 'waters' ? '#2563EB' : '#0F172A'}
                emissive={fp.stream === 'waters' ? '#2563EB' : '#334155'}
                emissiveIntensity={0.65}
              />
            </mesh>
          ))
        )}
      </group>
    </group>
  );
}

interface SceneControllerProps {
  spec: LayoutSpec;
  wallMode: WallMode;
  tourPlaying: boolean;
  tourProgress: number;
  setTourProgress: (v: number) => void;
  setActiveChapter: (id: number) => void;
  onTourComplete: () => void;
  controlsRef: React.RefObject<OrbitControlsImpl | null>;
  captureTrigger: number;
  onCapturedFrames: (stills: Record<number, string>) => void;
  resetSignal: number;
}

function SceneRig({
  spec,
  wallMode,
  tourPlaying,
  tourProgress,
  setTourProgress,
  setActiveChapter,
  onTourComplete,
  controlsRef,
  captureTrigger,
  onCapturedFrames,
  resetSignal,
}: SceneControllerProps) {
  const { camera, gl, scene } = useThree();

  const { camCurve, tgtCurve, totalSec, chapterBreaks } = useMemo(() => {
    const chs = spec.tour_chapters;
    const camPts = chs.map((c) => new THREE.Vector3(c.camera_mm[0] * M, c.camera_mm[2] * M, c.camera_mm[1] * M));
    const tgtPts = chs.map((c) => new THREE.Vector3(c.target_mm[0] * M, c.target_mm[2] * M, c.target_mm[1] * M));
    const tot = chs.reduce((acc, c) => acc + c.duration_sec, 0);
    let acc = 0;
    const breaks = chs.map((c) => {
      const start = acc / tot;
      acc += c.duration_sec;
      return { id: c.id, start, end: acc / tot };
    });
    return {
      camCurve: new THREE.CatmullRomCurve3(camPts, false, 'catmullrom', 0.4),
      tgtCurve: new THREE.CatmullRomCurve3(tgtPts, false, 'catmullrom', 0.4),
      totalSec: tot,
      chapterBreaks: breaks,
    };
  }, [spec.tour_chapters]);

  // Apply view mode camera jump
  useEffect(() => {
    if (tourPlaying) return;
    if (wallMode === 'topdown') {
      camera.position.set(9.1, 32.0, 10.8);
      if (controlsRef.current) {
        controlsRef.current.target.set(9.1, 0, 10.8);
        controlsRef.current.update();
      }
    } else {
      camera.position.set(17.5, 13.5, 25.5);
      if (controlsRef.current) {
        controlsRef.current.target.set(9.0, 0.8, 10.2);
        controlsRef.current.update();
      }
    }
  }, [wallMode, resetSignal, camera, controlsRef, tourPlaying]);

  // Capture all 8 stills programmatically via gl.render
  const lastCapture = useRef(0);
  useEffect(() => {
    if (captureTrigger <= lastCapture.current) return;
    lastCapture.current = captureTrigger;

    const prevPos = camera.position.clone();
    const prevQuat = camera.quaternion.clone();
    const out: Record<number, string> = {};

    for (const ch of spec.tour_chapters) {
      camera.position.set(ch.camera_mm[0] * M, ch.camera_mm[2] * M, ch.camera_mm[1] * M);
      camera.lookAt(ch.target_mm[0] * M, ch.target_mm[2] * M, ch.target_mm[1] * M);
      camera.updateMatrixWorld();
      gl.render(scene, camera);
      out[ch.id] = gl.domElement.toDataURL('image/png');
    }

    camera.position.copy(prevPos);
    camera.quaternion.copy(prevQuat);
    camera.updateMatrixWorld();
    gl.render(scene, camera);
    onCapturedFrames(out);
  }, [captureTrigger, camera, gl, scene, spec.tour_chapters, onCapturedFrames]);

  useFrame((_, delta) => {
    if (!tourPlaying) return;
    const next = Math.min(1, tourProgress + delta / totalSec);
    const camPos = camCurve.getPointAt(next);
    const tgtPos = tgtCurve.getPointAt(next);
    camera.position.copy(camPos);
    camera.lookAt(tgtPos);
    if (controlsRef.current) {
      controlsRef.current.target.copy(tgtPos);
    }
    setTourProgress(next);
    const found = chapterBreaks.find((b) => next >= b.start && next <= b.end);
    if (found) setActiveChapter(found.id);
    if (next >= 1) onTourComplete();
  });

  // Jump camera when chapter manually selected while paused
  return null;
}

export default function Lab3DViewer({ spec, onCaptureStills }: Lab3DViewerProps) {
  const [wallMode, setWallMode] = useState<WallMode>('cutaway');
  const [showFlow, setShowFlow] = useState(true);
  const [selected, setSelected] = useState<SelectedInspectTarget | null>(null);
  const [tourPlaying, setTourPlaying] = useState(false);
  const [tourProgress, setTourProgress] = useState(0);
  const [activeChapterId, setActiveChapterId] = useState(1);
  const [recording, setRecording] = useState(false);
  const [captureTrigger, setCaptureTrigger] = useState(0);
  const [captureBanner, setCaptureBanner] = useState<string | null>(null);
  const [resetSignal, setResetSignal] = useState(0);

  const controlsRef = useRef<OrbitControlsImpl | null>(null);
  const canvasWrapRef = useRef<HTMLDivElement>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const wallHeightM = wallMode === 'cutaway' ? 2.2 : spec.meta.coordinate_system.ceiling_height_mm * M;
  const currentChapter = spec.tour_chapters.find((c) => c.id === activeChapterId) ?? spec.tour_chapters[0];

  const handleSelectChapter = (chId: number) => {
    const idx = spec.tour_chapters.findIndex((c) => c.id === chId);
    if (idx < 0) return;
    const tot = spec.tour_chapters.reduce((a, c) => a + c.duration_sec, 0);
    const before = spec.tour_chapters.slice(0, idx).reduce((a, c) => a + c.duration_sec, 0);
    setActiveChapterId(chId);
    setTourProgress(Math.min(0.99, (before + 0.25) / tot));
    setTourPlaying(true);
  };

  const stopRecording = useCallback(() => {
    if (recorderRef.current && recorderRef.current.state !== 'inactive') {
      recorderRef.current.stop();
    }
    setRecording(false);
  }, []);

  const startRecording = () => {
    const canvas = canvasWrapRef.current?.querySelector('canvas');
    if (!canvas || typeof MediaRecorder === 'undefined') {
      setCaptureBanner('MediaRecorder is unavailable in this browser.');
      return;
    }
    const stream = canvas.captureStream(60);
    const mime = MediaRecorder.isTypeSupported('video/webm;codecs=vp9') ? 'video/webm;codecs=vp9' : 'video/webm';
    const rec = new MediaRecorder(stream, { mimeType: mime, videoBitsPerSecond: 8_000_000 });
    chunksRef.current = [];
    rec.ondataavailable = (ev) => {
      if (ev.data.size > 0) chunksRef.current.push(ev.data);
    };
    rec.onstop = () => {
      const blob = new Blob(chunksRef.current, { type: mime });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'Project_Vol_3D_Tour.webm';
      a.click();
      URL.revokeObjectURL(url);
      setCaptureBanner('Downloaded 60fps 3D Tour video (Project_Vol_3D_Tour.webm)');
    };
    recorderRef.current = rec;
    rec.start();
    setRecording(true);
    setTourProgress(0);
    setActiveChapterId(1);
    setTourPlaying(true);
  };

  const handleTourComplete = useCallback(() => {
    setTourPlaying(false);
    if (recording) stopRecording();
  }, [recording, stopRecording]);

  const handleCapturedFrames = useCallback(
    (stills: Record<number, string>) => {
      onCaptureStills(stills);
      setCaptureBanner(`Captured ${Object.keys(stills).length}/8 architectural stills into Photo Gallery.`);
    },
    [onCaptureStills]
  );

  const handleRoomClick = (rm: Room) => {
    setSelected({
      kind: 'room',
      id: rm.id,
      name: rm.name,
      subtitle: `${rm.wing} • ${rm.phase}`,
      dimensions: `${rm.w} × ${rm.h} mm (${((rm.w * rm.h) / 1e6).toFixed(1)} m²)`,
      coordinates: `X=${rm.x}..${rm.x + rm.w} mm, Y=${rm.y}..${rm.y + rm.h} mm`,
      flags: [`Status: ${rm.status.replace(/_/g, ' ')}`],
      notes: rm.notes,
    });
  };

  return (
    <div className="flex flex-col h-[calc(100vh-4.25rem)] bg-slate-100">
      {/* Control Toolbar */}
      <div className="bg-white border-b border-slate-200 px-4 py-2.5 flex flex-wrap items-center justify-between gap-2 shadow-sm z-10">
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 mr-1 flex items-center gap-1">
            <Layers className="w-3.5 h-3.5" /> View:
          </span>
          {(['cutaway', 'full', 'roof', 'topdown'] as WallMode[]).map((mode) => (
            <button
              key={mode}
              onClick={() => {
                setTourPlaying(false);
                setWallMode(mode);
              }}
              className={`px-2.5 py-1 rounded-md text-xs font-medium transition ${
                wallMode === mode
                  ? 'bg-slate-900 text-white'
                  : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
              }`}
            >
              {mode === 'cutaway'
                ? 'Cutaway Walls'
                : mode === 'full'
                ? 'Full Height'
                : mode === 'roof'
                ? 'Roof + Linear LEDs'
                : 'Top-Down Plan'}
            </button>
          ))}

          <button
            onClick={() => setShowFlow((v) => !v)}
            className={`ml-2 px-2.5 py-1 rounded-md text-xs font-medium flex items-center gap-1.5 transition border ${
              showFlow
                ? 'bg-blue-900 text-white border-blue-900'
                : 'bg-white text-slate-700 border-slate-300 hover:bg-slate-50'
            }`}
          >
            <Route className="w-3.5 h-3.5" />
            Sample Segregation Overlay
          </button>

          <button
            onClick={() => {
              setTourPlaying(false);
              setResetSignal((s) => s + 1);
            }}
            className="px-2.5 py-1 rounded-md text-xs font-medium bg-slate-100 text-slate-700 hover:bg-slate-200 flex items-center gap-1"
          >
            <Compass className="w-3.5 h-3.5" /> Reset Camera
          </button>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={() => {
              if (tourPlaying) {
                setTourPlaying(false);
              } else {
                if (tourProgress >= 0.99) setTourProgress(0);
                setTourPlaying(true);
              }
            }}
            className="px-3 py-1.5 rounded-md text-xs font-semibold bg-blue-900 text-white hover:bg-blue-800 flex items-center gap-1.5 shadow-sm"
          >
            {tourPlaying ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
            {tourPlaying ? 'Pause Tour' : 'Play Guided Tour'}
          </button>

          <button
            onClick={() => {
              setTourProgress(0);
              setActiveChapterId(1);
              setTourPlaying(true);
            }}
            className="px-2.5 py-1.5 rounded-md text-xs font-medium bg-slate-100 text-slate-700 hover:bg-slate-200 flex items-center gap-1"
            title="Restart Guided Tour"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>

          <button
            onClick={recording ? stopRecording : startRecording}
            className={`px-3 py-1.5 rounded-md text-xs font-semibold flex items-center gap-1.5 shadow-sm transition ${
              recording
                ? 'bg-red-600 text-white hover:bg-red-700'
                : 'bg-slate-900 text-white hover:bg-slate-800'
            }`}
          >
            {recording ? <Square className="w-3.5 h-3.5" /> : <Video className="w-3.5 h-3.5" />}
            {recording ? 'Stop & Save Video' : 'Record Tour Video'}
          </button>

          <button
            onClick={() => setCaptureTrigger((n) => n + 1)}
            className="px-3 py-1.5 rounded-md text-xs font-semibold bg-white border border-slate-300 text-slate-800 hover:bg-slate-50 flex items-center gap-1.5 shadow-sm"
          >
            <Camera className="w-3.5 h-3.5" />
            Capture Gallery Stills
          </button>
        </div>
      </div>

      {/* Main 3D Canvas + Floating HUDs */}
      <div ref={canvasWrapRef} className="relative flex-1 overflow-hidden">
        <Canvas
          shadows
          dpr={[1, 2]}
          gl={{ preserveDrawingBuffer: true, antialias: true }}
          camera={{ position: [17.5, 13.5, 25.5], fov: 45, near: 0.1, far: 150 }}
        >
          <color attach="background" args={['#F1F5F9']} />
          <ambientLight intensity={0.78} />
          <hemisphereLight args={['#FFFFFF', '#CBD5E1', 0.45]} />
          <directionalLight
            position={[18, 22, 16]}
            intensity={1.15}
            castShadow
            shadow-mapSize={[2048, 2048]}
            shadow-camera-left={-15}
            shadow-camera-right={25}
            shadow-camera-top={25}
            shadow-camera-bottom={-15}
          />
          <directionalLight position={[-12, 16, -10]} intensity={0.4} />

          {/* Floor slabs & Room click targets */}
          {spec.rooms.map((rm) => {
            const cx = (rm.x + rm.w * 0.5) * M;
            const cz = (rm.y + rm.h * 0.5) * M;
            const isExt = rm.id === 'external_cold_storage';
            return (
              <mesh
                key={rm.id}
                position={[cx, isExt ? 1.4 : -0.04, cz]}
                receiveShadow
                castShadow={isExt}
                onClick={(e) => {
                  e.stopPropagation();
                  handleRoomClick(rm);
                }}
              >
                <boxGeometry args={[rm.w * M, isExt ? 2.8 : 0.08, rm.h * M]} />
                <meshStandardMaterial color={isExt ? '#E2E8F0' : '#CBD5E1'} roughness={0.62} />
              </mesh>
            );
          })}

          {/* Charcoal Zone Striping */}
          {spec.zones.map((zn) => (
            <mesh
              key={zn.id}
              position={[(zn.x + zn.w * 0.5) * M, 0.005, (zn.y + zn.h * 0.5) * M]}
              receiveShadow
            >
              <boxGeometry args={[zn.w * M, 0.01, zn.h * M]} />
              <meshStandardMaterial
                color={zn.id === 'Z-SORTING' ? '#94A3B8' : '#B8C4D4'}
                roughness={0.55}
              />
            </mesh>
          ))}

          {/* Walls & Door Leaves */}
          {spec.walls.map((wall) => (
            <WallMesh key={wall.id} wall={wall} doors={spec.doors} wallHeightM={wallHeightM} />
          ))}
          {spec.doors.map((door) => (
            <DoorLeafMesh key={door.id} door={door} wallHeightM={wallHeightM} />
          ))}

          {/* Roof + Recessed Linear White LED Ceiling Panels */}
          {wallMode === 'roof' && (
            <group>
              <mesh position={[9.15, 3.24, 9.07]} receiveShadow>
                <boxGeometry args={[18.3, 0.08, 18.14]} />
                <meshStandardMaterial color="#FFFFFF" transparent opacity={0.42} roughness={0.8} />
              </mesh>
              <mesh position={[7.01, 3.24, 19.85]} receiveShadow>
                <boxGeometry args={[14.03, 0.08, 3.44]} />
                <meshStandardMaterial color="#FFFFFF" transparent opacity={0.42} roughness={0.8} />
              </mesh>
            </group>
          )}
          {(wallMode === 'full' || wallMode === 'roof') &&
            [2, 6, 10, 14, 17].flatMap((lx) =>
              [3, 7, 11, 15].map((lz) => (
                <mesh key={`led-${lx}-${lz}`} position={[lx, 3.16, lz]}>
                  <boxGeometry args={[1.2, 0.03, 0.25]} />
                  <meshStandardMaterial color="#FFFFFF" emissive="#FFFFFF" emissiveIntensity={1.6} />
                </mesh>
              ))
            )}

          {/* Conveyors */}
          {spec.conveyors.map((conv) => (
            <ConveyorMesh
              key={conv.id}
              conv={conv}
              isSelected={selected?.id === conv.id}
              onSelect={setSelected}
            />
          ))}

          {/* Workstations & Equipment */}
          {spec.stations_and_equipment.map((it) => (
            <StationMesh
              key={it.id}
              item={it}
              isSelected={selected?.id === it.id}
              onSelect={setSelected}
            />
          ))}

          {/* Toggleable Sample Segregation Flow Overlay */}
          {showFlow && <FlowPathOverlay paths={spec.flow_paths} />}

          <OrbitControls
            ref={controlsRef}
            makeDefault
            enabled={!tourPlaying}
            enableDamping
            dampingFactor={0.08}
            maxPolarAngle={Math.PI * 0.48}
          />

          <SceneRig
            spec={spec}
            wallMode={wallMode}
            tourPlaying={tourPlaying}
            tourProgress={tourProgress}
            setTourProgress={setTourProgress}
            setActiveChapter={setActiveChapterId}
            onTourComplete={handleTourComplete}
            controlsRef={controlsRef}
            captureTrigger={captureTrigger}
            onCapturedFrames={handleCapturedFrames}
            resetSignal={resetSignal}
          />
        </Canvas>

        {/* Capture Confirmation Banner */}
        {captureBanner && (
          <div className="absolute top-3 left-1/2 -translate-x-1/2 bg-slate-900/95 text-white text-xs px-4 py-2 rounded-full shadow-lg flex items-center gap-2 z-20">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            <span>{captureBanner}</span>
            <button onClick={() => setCaptureBanner(null)} className="ml-1 text-slate-400 hover:text-white">
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        )}

        {/* Click Inspection Glassmorphic HUD */}
        {selected && (
          <div className="absolute top-4 right-4 w-80 bg-white/95 backdrop-blur-md border border-slate-200 rounded-xl shadow-lg p-4 z-20">
            <div className="flex items-start justify-between gap-2">
              <div>
                <span className="inline-block text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-slate-900 text-white">
                  {selected.id} • {selected.kind}
                </span>
                <h3 className="text-sm font-bold text-slate-900 mt-1.5">{selected.name}</h3>
                <p className="text-xs text-slate-500">{selected.subtitle}</p>
              </div>
              <button
                onClick={() => setSelected(null)}
                className="text-slate-400 hover:text-slate-700 p-1 rounded"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="mt-3 space-y-1.5 text-xs border-t border-slate-200 pt-2.5">
              <div>
                <span className="font-semibold text-slate-700">Dimensions: </span>
                <span className="text-slate-900 font-mono">{selected.dimensions}</span>
              </div>
              <div>
                <span className="font-semibold text-slate-700">Coords: </span>
                <span className="text-slate-600 font-mono">{selected.coordinates}</span>
              </div>
              {selected.flags.length > 0 && (
                <div className="flex flex-wrap gap-1 pt-1">
                  {selected.flags.map((f) => (
                    <span
                      key={f}
                      className="px-2 py-0.5 rounded-full bg-slate-100 border border-slate-200 text-[11px] font-medium text-slate-700"
                    >
                      {f}
                    </span>
                  ))}
                </div>
              )}
              <p className="text-slate-600 pt-1 leading-relaxed">{selected.notes}</p>
            </div>
          </div>
        )}

        {/* Bottom Guided Tour Caption & 8-Chapter Strip */}
        <div className="absolute bottom-4 left-4 right-4 flex flex-col gap-2 pointer-events-none z-20">
          <div className="max-w-2xl bg-slate-900/90 backdrop-blur-md text-white rounded-xl p-3.5 shadow-lg pointer-events-auto border border-slate-700">
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <Eye className="w-4 h-4 text-slate-300" />
                <span className="text-[11px] font-bold uppercase tracking-wider text-slate-300">
                  Chapter {currentChapter.id} / 8
                </span>
                <span className="text-sm font-bold text-white">{currentChapter.title}</span>
              </div>
              <span className="text-[11px] font-mono text-slate-300">
                {Math.round(tourProgress * 100)}%
              </span>
            </div>
            <p className="text-xs text-slate-200 mt-1">{currentChapter.subtitle} — {currentChapter.description}</p>
            <div className="w-full h-1 bg-slate-700 rounded-full mt-2 overflow-hidden">
              <div
                className="h-full bg-white transition-all duration-150"
                style={{ width: `${Math.round(tourProgress * 100)}%` }}
              />
            </div>
          </div>

          <div className="flex flex-wrap gap-1.5 pointer-events-auto">
            {spec.tour_chapters.map((ch) => (
              <button
                key={ch.id}
                onClick={() => handleSelectChapter(ch.id)}
                className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition shadow-sm border ${
                  activeChapterId === ch.id
                    ? 'bg-slate-900 text-white border-slate-900'
                    : 'bg-white/90 text-slate-700 border-slate-300 hover:bg-white'
                }`}
              >
                {ch.id}. {ch.title}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
