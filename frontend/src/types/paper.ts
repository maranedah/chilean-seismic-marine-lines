export interface BoundingBox {
  lat_min: number
  lat_max: number
  lon_min: number
  lon_max: number
}

export interface SeismicLine {
  name: string
  lat_start: number | null
  lon_start: number | null
  lat_end: number | null
  lon_end: number | null
  length_km: number | null
  depth_km: number | null
  profile_orientation: string | null
}

export interface Location {
  latitude: number | null
  longitude: number | null
  city: string
  region: string
  country: string
  description: string
  bounding_box: BoundingBox | null
  seismic_lines: SeismicLine[]
}

export interface Acquisition {
  vessel: string[] | null
  expeditions: string[] | null
  year_acquired: number | null
  source_type: string[] | null
  source_volume_cui: number | null
  streamer_length_m: number | null
  channel_count: number | null
  sample_rate_ms: number | null
  record_length_s: number | null
  fold: number | null
  line_spacing_km: number | null
  shot_interval_m: number | null
  group_interval_m: number | null
  obs_spacing_km: number | null
  nearest_offset_m: number | null
  frequency_range_hz: number[] | null
  depth_penetration_km: number | null
}

export interface Dataset {
  data_type: string
  name: string
  classification: string
  format: string[] | null
  url: string | null
  doi: string | null
  repository: string[] | null
  size_gb: number | null
  access: string
  download_command: string | null
  description: string
  cdp_spacing_m: number | null
}

export interface Processing {
  classification: string
  summary: string
  workflow: string[]
  software: string[]
  notes: string | null
  migration_type: string | null
}

export interface Paper {
  id: string
  title: string
  authors: string[]
  year: number
  journal: string
  doi: string | null
  url: string | null
  open_access_url: string | null
  abstract: string | null
  keywords: string[]
  location: Location | null
  acquisition: Acquisition | null
  data: Dataset[]
  processing: Processing | null
  analysis_confidence: string | null
  analysis_notes: string | null
  tectonic_setting: string | null
  associated_earthquakes: string[]
  // computed by API
  geographic_region: string
  paper_url: string | null
  has_open_data: boolean
  access_types: string[]
  data_types: string[]
  classifications: string[]
  completeness: number
}

export interface PaperSummary {
  id: string
  title: string
  authors_short: string
  authors: string[]
  year: number
  journal: string
  latitude: number | null
  longitude: number | null
  city: string
  geographic_region: string
  paper_url: string | null
  open_access_paper: boolean
  has_open_data: boolean
  access_types: string[]
  data_types: string[]
  classifications: string[]
  num_datasets: number
  keywords: string[]
  vessel: string[] | null
  acq_year: number | null
  source_type: string[] | null
  data_formats: string[]
  repositories: string[]
  seismic_lines: SeismicLine[]
  completeness: number
  preview_figures: string[]
}

export interface Stats {
  total_papers: number
  total_datasets: number
  open_access_count: number
  restricted_count: number
  unknown_count: number
  by_region: Record<string, number>
  by_year: Record<string, number>
  by_data_type: Record<string, number>
  by_classification: Record<string, number>
  year_range: [number, number]
  keyword_frequency: Record<string, number>
  by_data_format: Record<string, number>
  by_source_type: Record<string, number>
  by_vessel: Record<string, number>
  by_acq_year: Record<string, number>
  by_repository: Record<string, number>
  completeness_buckets: Record<string, number>
  avg_completeness: number
  size_gb_by_type: Record<string, number>
  datasets_by_format: Record<string, number>
  size_known_count: number
  size_unknown_count: number
  paper_field_fill: Record<string, number>
  dataset_field_fill: Record<string, number>
  pdfs_analyzed: number
  figures_total: number
  figures_per_paper: Record<string, number>
}

export interface FigureEntry {
  filename: string
  path: string
  page: number
  type: string
  figure_label: string | null
  caption: string | null
  description: string | null
}

export interface FiguresManifest {
  paper_id: string
  total_figures: number
  figures: FigureEntry[]
}

export interface PaperFilters {
  q?: string
  // basic
  region?: string
  year_min?: number
  year_max?: number
  access?: string
  paper_access?: string
  classification?: string
  open_only?: boolean
  // advanced
  author?: string
  keyword?: string
  data_types?: string[]
  data_format?: string
  repository?: string
  vessel?: string
  source_type?: string
  acq_year_min?: number
  acq_year_max?: number
  lat_min?: number
  lat_max?: number
  lon_min?: number
  lon_max?: number
}
