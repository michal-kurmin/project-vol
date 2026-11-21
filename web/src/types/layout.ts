export interface Rect {
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface Room extends Rect {
  id: string;
  name: string;
  wing: string;
  exclude_subrect?: Rect;
  status: string;
  phase: string;
  notes: string;
}

export interface Wall {
  id: string;
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  thickness_mm: number;
  height_mm: number;
  kind: 'exterior' | 'interior' | 'glazed_partition' | 'external_enclosure';
}

export interface Door {
  id: string;
  name: string;
  wall_id: string;
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  width_mm: number;
  height_mm: number;
  hinge: [number, number] | null;
  swing_dir: '+X' | '-X' | '+Y' | '-Y' | 'open_passage';
  role: string;
  note: string;
}

export interface Zone extends Rect {
  id: string;
  name: string;
  room_id: string;
  clear_corridor_width_mm?: number;
  kind: string;
  notes: string;
}

export interface ConveyorDeck {
  name: string;
  stream: string;
  z_mm: number;
}

export interface Conveyor extends Rect {
  id: string;
  name: string;
  room_id: string;
  flow_dir: string;
  decks: ConveyorDeck[];
  notes: string;
}

export interface SeatSpec {
  side: string;
  facing: '+X' | '-X' | '+Y' | '-Y';
  x: number;
  y: number;
}

export interface StationEquipment extends Rect {
  id: string;
  name: string;
  room_id: string;
  category: string;
  parent_id: string | null;
  elev_mm: number;
  height_mm: number;
  tiers?: number;
  retained: boolean;
  has_pc: boolean;
  dual_monitor: boolean;
  has_label_printer: boolean;
  has_fume_hood: boolean;
  has_shaker: boolean;
  has_sink: boolean;
  has_vacuum_pump: boolean;
  has_barcode_scanner: boolean;
  seat: SeatSpec | null;
  notes: string;
}

export interface FlowPath {
  id: string;
  name: string;
  stream: string;
  color: string;
  points: [number, number][];
}

export interface DimensionAnnotation {
  id: string;
  label: string;
  x1: number;
  y1: number;
  x2: number;
  y2: number;
}

export interface TourChapter {
  id: number;
  title: string;
  subtitle: string;
  description: string;
  camera_mm: [number, number, number];
  target_mm: [number, number, number];
  duration_sec: number;
}

export interface LayoutSpec {
  meta: {
    project_name: string;
    facility_title: string;
    address: string;
    version: string;
    units: string;
    coordinate_system: {
      ceiling_height_mm: number;
    };
    palette: {
      physical: Record<string, string>;
      ui_and_overlays: Record<string, string>;
    };
    strategic_narrative: {
      summary: string;
      consolidated_phases: { phase: string; name: string; description: string }[];
      lean_principles: string[];
      scope_changes: {
        demolished: string[];
        retained: string[];
        upgraded_and_new: string[];
      };
    };
  };
  shell: {
    main_building: Rect;
    front_extension: Rect;
    external_cold_storage: Rect;
    left_wing_width_mm: number;
    main_hall_width_mm: number;
    exterior_wall_thickness_mm: number;
    interior_wall_thickness_mm: number;
  };
  rooms: Room[];
  walls: Wall[];
  doors: Door[];
  zones: Zone[];
  conveyors: Conveyor[];
  stations_and_equipment: StationEquipment[];
  flow_paths: FlowPath[];
  dimensions: DimensionAnnotation[];
  tour_chapters: TourChapter[];
}

export interface GalleryPrompt {
  id: number;
  filename: string;
  title: string;
  subtitle: string;
  category: string;
  camera_mm: [number, number, number];
  target_mm: [number, number, number];
  focal_length_mm: number;
  dimensions_callout: string;
  before_after_note: string;
  prompt: string;
  negative_prompt: string;
}

export interface SelectedInspectTarget {
  kind: 'station' | 'conveyor' | 'room';
  id: string;
  name: string;
  subtitle: string;
  dimensions: string;
  coordinates: string;
  flags: string[];
  notes: string;
}
