import { useCallback, useState } from 'react';
import { Box, Images, Map, Presentation } from 'lucide-react';
import rawSpec from '@data/layout_spec.json';
import type { LayoutSpec } from './types/layout';
import Lab3DViewer from './components/Lab3DViewer';
import FloorPlan2DView from './components/FloorPlan2DView';
import PhotoGallery, { DEFAULT_GALLERY_IMAGES } from './components/PhotoGallery';
import SlideDeckViewer from './components/SlideDeckViewer';

type TabKey = '3d' | '2d' | 'gallery' | 'slides';

export default function App() {
  const spec = rawSpec as unknown as LayoutSpec;
  const [tab, setTab] = useState<TabKey>('3d');
  const [capturedStills, setCapturedStills] = useState<Record<number, string>>(
    () => ({ ...DEFAULT_GALLERY_IMAGES })
  );

  const handleCaptureStills = useCallback((stills: Record<number, string>) => {
    setCapturedStills((prev) => ({ ...prev, ...stills }));
  }, []);

  const handleUploadStill = useCallback((id: number, dataUrl: string) => {
    setCapturedStills((prev) => ({ ...prev, [id]: dataUrl }));
  }, []);

  const totalPcs = spec.stations_and_equipment.filter((i) => i.has_pc).length;

  const navItems: { key: TabKey; label: string; icon: JSX.Element }[] = [
    { key: '3d', label: '3D Model & Tour', icon: <Box className="w-4 h-4" /> },
    { key: '2d', label: '2D Spec', icon: <Map className="w-4 h-4" /> },
    { key: 'gallery', label: 'Photo Gallery', icon: <Images className="w-4 h-4" /> },
    { key: 'slides', label: 'Slideshow', icon: <Presentation className="w-4 h-4" /> },
  ];

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 text-slate-900">
      <header className="bg-slate-900 text-white border-b border-slate-800 px-4 py-2.5 flex flex-wrap items-center justify-between gap-3 h-auto min-h-[4.25rem]">
        <div className="flex items-center gap-3">
          <div className="w-2.5 h-8 rounded-full bg-blue-600" />
          <div>
            <div className="text-[11px] font-bold uppercase tracking-widest text-slate-400">
              {spec.meta.project_name} • {spec.meta.address}
            </div>
            <h1 className="text-sm md:text-base font-bold leading-tight">
              {spec.meta.facility_title}
            </h1>
          </div>
        </div>

        <nav className="flex items-center gap-1 bg-slate-800/80 p-1 rounded-lg">
          {navItems.map((n) => (
            <button
              key={n.key}
              onClick={() => setTab(n.key)}
              className={`px-3 py-1.5 rounded-md text-xs font-semibold flex items-center gap-1.5 transition ${
                tab === n.key
                  ? 'bg-white text-slate-900 shadow-sm'
                  : 'text-slate-300 hover:text-white hover:bg-slate-700/60'
              }`}
            >
              {n.icon}
              {n.label}
            </button>
          ))}
        </nav>

        <div className="hidden xl:flex items-center gap-2 text-[11px] font-mono text-slate-300 bg-slate-800 px-3 py-1.5 rounded-full border border-slate-700">
          <span>380.0 m² GIA</span>
          <span className="text-slate-500">•</span>
          <span>{totalPcs} PCs</span>
          <span className="text-slate-500">•</span>
          <span>0 Cross-Flow</span>
        </div>
      </header>

      <main className="flex-1">
        {tab === '3d' && <Lab3DViewer spec={spec} onCaptureStills={handleCaptureStills} />}
        {tab === '2d' && <FloorPlan2DView spec={spec} />}
        {tab === 'gallery' && (
          <PhotoGallery capturedStills={capturedStills} onUploadStill={handleUploadStill} />
        )}
        {tab === 'slides' && (
          <SlideDeckViewer
            spec={spec}
            capturedStills={capturedStills}
            onOpen3DTour={() => setTab('3d')}
          />
        )}
      </main>
    </div>
  );
}
