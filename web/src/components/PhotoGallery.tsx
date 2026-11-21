import { useEffect, useState } from 'react';
import {
  ChevronLeft,
  ChevronRight,
  Code2,
  Maximize2,
  Ruler,
  Upload,
  X,
} from 'lucide-react';
import promptsData from '../assets/gallery_prompts.json';
import type { GalleryPrompt } from '../types/layout';

import view01 from '../assets/gallery/view_01.png';
import view02 from '../assets/gallery/view_02.png';
import view03 from '../assets/gallery/view_03.png';
import view04 from '../assets/gallery/view_04.png';
import view05 from '../assets/gallery/view_05.png';
import view06 from '../assets/gallery/view_06.png';
import view07 from '../assets/gallery/view_07.png';
import view08 from '../assets/gallery/view_08.png';

export const DEFAULT_GALLERY_IMAGES: Record<number, string> = {
  1: view01,
  2: view02,
  3: view03,
  4: view04,
  5: view05,
  6: view06,
  7: view07,
  8: view08,
};

interface PhotoGalleryProps {
  capturedStills: Record<number, string>;
  onUploadStill: (id: number, dataUrl: string) => void;
}

export default function PhotoGallery({ capturedStills, onUploadStill }: PhotoGalleryProps) {
  const prompts = promptsData as GalleryPrompt[];
  const categories = ['All', ...Array.from(new Set(prompts.map((p) => p.category)))];

  const [category, setCategory] = useState('All');
  const [showDimensions, setShowDimensions] = useState(true);
  const [lightboxId, setLightboxId] = useState<number | null>(null);
  const [showPromptId, setShowPromptId] = useState<number | null>(null);

  const filtered = category === 'All' ? prompts : prompts.filter((p) => p.category === category);
  const lightboxItem = prompts.find((p) => p.id === lightboxId) ?? null;

  useEffect(() => {
    if (lightboxId === null) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setLightboxId(null);
      if (e.key === 'ArrowRight') setLightboxId((id) => (id ? (id % prompts.length) + 1 : 1));
      if (e.key === 'ArrowLeft') setLightboxId((id) => (id ? ((id - 2 + prompts.length) % prompts.length) + 1 : 1));
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [lightboxId, prompts.length]);

  const handleFileUpload = (id: number, file: File | undefined) => {
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      if (typeof reader.result === 'string') {
        onUploadStill(id, reader.result);
      }
    };
    reader.readAsDataURL(file);
  };

  return (
    <div className="min-h-[calc(100vh-4.25rem)] bg-slate-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header & Filters */}
        <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
          <div>
            <h2 className="text-xl font-bold text-slate-900">
              Architectural White &amp; Grey Photo Gallery
            </h2>
            <p className="text-xs text-slate-600 mt-0.5">
              8 camera-locked viewpoints synchronized to <code className="text-slate-800">data/layout_spec.json</code> — replace any frame with Blender Cycles or AI photorealistic renders.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {categories.map((cat) => (
              <button
                key={cat}
                onClick={() => setCategory(cat)}
                className={`px-3 py-1.5 rounded-full text-xs font-medium transition border ${
                  category === cat
                    ? 'bg-slate-900 text-white border-slate-900'
                    : 'bg-white text-slate-700 border-slate-300 hover:bg-slate-100'
                }`}
              >
                {cat}
              </button>
            ))}
            <button
              onClick={() => setShowDimensions((v) => !v)}
              className={`ml-2 px-3 py-1.5 rounded-full text-xs font-medium flex items-center gap-1.5 border ${
                showDimensions
                  ? 'bg-blue-900 text-white border-blue-900'
                  : 'bg-white text-slate-700 border-slate-300'
              }`}
            >
              <Ruler className="w-3.5 h-3.5" /> Dimension Callouts
            </button>
          </div>
        </div>

        {/* Gallery Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {filtered.map((item) => {
            const imgSrc = capturedStills[item.id] ?? DEFAULT_GALLERY_IMAGES[item.id];
            const promptOpen = showPromptId === item.id;
            return (
              <div
                key={item.id}
                className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm hover:shadow-md transition flex flex-col"
              >
                <div className="relative bg-slate-100 aspect-video overflow-hidden group">
                  <img
                    src={imgSrc}
                    alt={item.title}
                    className="w-full h-full object-cover cursor-pointer"
                    onClick={() => setLightboxId(item.id)}
                  />
                  {showDimensions && (
                    <div className="absolute top-3 left-3 bg-slate-900/85 backdrop-blur-sm text-white text-[11px] font-mono px-2.5 py-1 rounded-md">
                      {item.dimensions_callout}
                    </div>
                  )}
                  <button
                    onClick={() => setLightboxId(item.id)}
                    className="absolute top-3 right-3 bg-white/90 hover:bg-white text-slate-900 p-1.5 rounded-lg shadow opacity-85 group-hover:opacity-100 transition"
                    title="Fullscreen Lightbox"
                  >
                    <Maximize2 className="w-4 h-4" />
                  </button>
                </div>

                <div className="p-4 flex-1 flex flex-col justify-between gap-3">
                  <div>
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-[11px] font-bold uppercase tracking-wider text-blue-900">
                        View 0{item.id} • {item.category}
                      </span>
                      <span className="text-[11px] text-slate-400 font-mono">
                        {item.focal_length_mm}mm Lens
                      </span>
                    </div>
                    <h3 className="text-base font-bold text-slate-900 mt-1">{item.title}</h3>
                    <p className="text-xs text-slate-500">{item.subtitle}</p>
                    <p className="text-xs text-slate-700 mt-2 bg-slate-50 border border-slate-200 rounded-lg p-2.5 leading-relaxed">
                      {item.before_after_note}
                    </p>
                  </div>

                  <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-slate-100">
                    <button
                      onClick={() => setShowPromptId(promptOpen ? null : item.id)}
                      className="text-xs font-medium text-slate-700 hover:text-slate-900 flex items-center gap-1"
                    >
                      <Code2 className="w-3.5 h-3.5" />
                      {promptOpen ? 'Hide Render Prompt' : 'View Render Prompt'}
                    </button>

                    <label className="text-xs font-medium text-blue-900 hover:text-blue-700 cursor-pointer flex items-center gap-1">
                      <Upload className="w-3.5 h-3.5" />
                      Replace with Cycles / AI Render
                      <input
                        type="file"
                        accept="image/png,image/jpeg,image/webp"
                        className="hidden"
                        onChange={(e) => handleFileUpload(item.id, e.target.files?.[0])}
                      />
                    </label>
                  </div>

                  {promptOpen && (
                    <div className="bg-slate-900 text-slate-100 rounded-lg p-3 text-[11px] font-mono leading-relaxed">
                      <div className="text-slate-400 mb-1 font-sans font-semibold">
                        Locked White &amp; Grey Photorealism Prompt:
                      </div>
                      {item.prompt}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Fullscreen Lightbox */}
      {lightboxItem && (
        <div
          className="fixed inset-0 bg-slate-950/95 backdrop-blur-sm z-50 flex flex-col items-center justify-center p-6"
          onClick={() => setLightboxId(null)}
        >
          <div
            className="max-w-6xl w-full flex flex-col gap-3"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between text-white">
              <div>
                <span className="text-xs font-mono text-slate-400">VIEW 0{lightboxItem.id} / 08</span>
                <h3 className="text-lg font-bold">{lightboxItem.title} — {lightboxItem.subtitle}</h3>
              </div>
              <button
                onClick={() => setLightboxId(null)}
                className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="relative bg-black rounded-xl overflow-hidden border border-slate-700">
              <img
                src={capturedStills[lightboxItem.id] ?? DEFAULT_GALLERY_IMAGES[lightboxItem.id]}
                alt={lightboxItem.title}
                className="w-full max-h-[74vh] object-contain mx-auto"
              />
              <button
                onClick={() =>
                  setLightboxId(((lightboxItem.id - 2 + prompts.length) % prompts.length) + 1)
                }
                className="absolute left-3 top-1/2 -translate-y-1/2 p-2.5 rounded-full bg-slate-900/80 hover:bg-slate-800 text-white"
              >
                <ChevronLeft className="w-5 h-5" />
              </button>
              <button
                onClick={() => setLightboxId((lightboxItem.id % prompts.length) + 1)}
                className="absolute right-3 top-1/2 -translate-y-1/2 p-2.5 rounded-full bg-slate-900/80 hover:bg-slate-800 text-white"
              >
                <ChevronRight className="w-5 h-5" />
              </button>
            </div>

            <div className="text-xs text-slate-300 flex flex-wrap justify-between gap-2">
              <span>{lightboxItem.before_after_note}</span>
              <span className="font-mono text-slate-400">{lightboxItem.dimensions_callout}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
