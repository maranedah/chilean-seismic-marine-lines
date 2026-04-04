import type { PaperFilters, PaperSummary } from '../types/paper'

export interface FilterOptions {
  authors: string[]
  keywords: string[]
  vessels: string[]
  source_types: string[]
  data_formats: string[]
  repositories: string[]
}

export function computeFilterOptions(papers: PaperSummary[]): FilterOptions {
  const uniq = <T>(arr: T[]): T[] => [...new Set(arr)].filter(Boolean) as T[]
  return {
    authors: uniq(papers.flatMap((p) => p.authors.map((a) => a.split(',')[0].trim()))).sort(),
    keywords: uniq(papers.flatMap((p) => p.keywords)).sort(),
    vessels: uniq(papers.map((p) => p.vessel ?? '')).filter(Boolean).sort(),
    source_types: uniq(papers.map((p) => p.source_type ?? '')).filter(Boolean).sort(),
    data_formats: uniq(papers.flatMap((p) => p.data_formats)).sort(),
    repositories: uniq(papers.flatMap((p) => p.repositories)).sort(),
  }
}

function includesCI(haystack: string | null | undefined, needle: string): boolean {
  return (haystack ?? '').toLowerCase().includes(needle.toLowerCase())
}

export function applyFilters(papers: PaperSummary[], filters: PaperFilters): PaperSummary[] {
  return papers.filter((p) => {
    // ── Text search ──────────────────────────────────────────────────────────────
    if (filters.q) {
      const q = filters.q.toLowerCase()
      const matched =
        p.title.toLowerCase().includes(q) ||
        p.authors.some((a) => a.toLowerCase().includes(q)) ||
        p.keywords.some((k) => k.toLowerCase().includes(q)) ||
        p.city.toLowerCase().includes(q) ||
        p.journal.toLowerCase().includes(q)
      if (!matched) return false
    }

    // ── Basic ────────────────────────────────────────────────────────────────
    if (filters.region && p.geographic_region !== filters.region) return false
    if (filters.year_min && p.year < filters.year_min) return false
    if (filters.year_max && p.year > filters.year_max) return false
    if (filters.access && !p.access_types.includes(filters.access)) return false
    if (filters.classification && !p.classifications.includes(filters.classification)) return false
    if (filters.open_only && !p.has_open_data) return false

    // ── Advanced ─────────────────────────────────────────────────────────────
    if (filters.author) {
      const q = filters.author.toLowerCase()
      if (!p.authors.some((a) => a.toLowerCase().includes(q))) return false
    }

    if (filters.keyword) {
      const q = filters.keyword.toLowerCase()
      if (!p.keywords.some((k) => k.toLowerCase().includes(q))) return false
    }

    if (filters.data_types?.length) {
      if (!filters.data_types.some((dt) => p.data_types.includes(dt))) return false
    }

    if (filters.data_format) {
      if (!p.data_formats.some((f) => includesCI(f, filters.data_format!))) return false
    }

    if (filters.repository) {
      if (!p.repositories.some((r) => includesCI(r, filters.repository!))) return false
    }

    if (filters.vessel && !includesCI(p.vessel, filters.vessel)) return false
    if (filters.source_type && !includesCI(p.source_type, filters.source_type)) return false

    if (filters.acq_year_min && (p.acq_year == null || p.acq_year < filters.acq_year_min))
      return false
    if (filters.acq_year_max && (p.acq_year == null || p.acq_year > filters.acq_year_max))
      return false

    // ── Bounding box ─────────────────────────────────────────────────────────
    if (filters.lat_min != null && (p.latitude == null || p.latitude < filters.lat_min))
      return false
    if (filters.lat_max != null && (p.latitude == null || p.latitude > filters.lat_max))
      return false
    if (filters.lon_min != null && (p.longitude == null || p.longitude < filters.lon_min))
      return false
    if (filters.lon_max != null && (p.longitude == null || p.longitude > filters.lon_max))
      return false

    return true
  })
}

export const REGIONS = [
  'North Chile (17°–30°S)',
  'Central Chile (30°–40°S)',
  'South Chile (40°–57°S)',
]

export const DATA_TYPE_LABELS: Record<string, string> = {
  seismic_reflection_mcs: 'MCS Reflection',
  seismic_refraction_obs: 'OBS Refraction',
  obh: 'OBH',
  bathymetry: 'Bathymetry',
  backscatter: 'Backscatter',
  gravity: 'Gravity',
  magnetics: 'Magnetics',
  navigation: 'Navigation',
  subbottom: 'Sub-bottom',
  velocity_sound: 'Sound Velocity',
}

export function hasAdvancedFilters(f: PaperFilters): boolean {
  return !!(
    f.author ||
    f.keyword ||
    f.data_types?.length ||
    f.data_format ||
    f.repository ||
    f.vessel ||
    f.source_type ||
    f.acq_year_min ||
    f.acq_year_max ||
    f.lat_min != null ||
    f.lat_max != null ||
    f.lon_min != null ||
    f.lon_max != null
  )
}
