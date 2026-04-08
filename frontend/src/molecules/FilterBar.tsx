'use client'

import { useState } from 'react'
import type { PaperFilters } from '../types/paper'
import { DATA_TYPE_LABELS, REGIONS, hasAdvancedFilters, type FilterOptions } from '../utils/filters'

interface Props {
  filters: PaperFilters
  onChange: (f: PaperFilters) => void
  options?: FilterOptions
}

// ── Primitives ────────────────────────────────────────────────────────────────

function Label({ children }: { children: React.ReactNode }) {
  return <label className="block text-xs font-medium text-gray-500 mb-1">{children}</label>
}

const INPUT_CLS =
  'border border-gray-300 rounded-md text-sm px-2.5 py-1.5 w-full bg-white focus:outline-none focus:ring-2 focus:ring-blue-500'

function SelectInput({
  value,
  onChange,
  children,
}: {
  value: string
  onChange: (v: string) => void
  children: React.ReactNode
}) {
  return (
    <select className={INPUT_CLS} value={value} onChange={(e) => onChange(e.target.value)}>
      {children}
    </select>
  )
}

/** Text input with native <datalist> suggestions sourced from actual DB values. */
function SuggestInput({
  listId,
  value,
  onChange,
  placeholder,
  suggestions = [],
}: {
  listId: string
  value: string
  onChange: (v: string) => void
  placeholder?: string
  suggestions?: string[]
}) {
  return (
    <>
      <input
        type="text"
        list={listId}
        className={INPUT_CLS}
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
      <datalist id={listId}>
        {suggestions.map((s) => (
          <option key={s} value={s} />
        ))}
      </datalist>
    </>
  )
}

function NumberInput({
  value,
  onChange,
  placeholder,
}: {
  value: number | undefined
  onChange: (v: number | undefined) => void
  placeholder?: string
}) {
  return (
    <input
      type="number"
      className={INPUT_CLS}
      placeholder={placeholder}
      value={value ?? ''}
      onChange={(e) => onChange(e.target.value ? Number(e.target.value) : undefined)}
    />
  )
}

// ── FilterBar ─────────────────────────────────────────────────────────────────

export default function FilterBar({ filters, onChange, options }: Props) {
  const [showAdvanced, setShowAdvanced] = useState(() => hasAdvancedFilters(filters))

  const set = <K extends keyof PaperFilters>(key: K, val: PaperFilters[K]) =>
    onChange({ ...filters, [key]: val || undefined })

  const hasBasic = !!(
    filters.q ||
    filters.region ||
    filters.year_min ||
    filters.year_max ||
    filters.access ||
    filters.paper_access ||
    filters.classification
  )
  const hasAdv = hasAdvancedFilters(filters)
  const advCount = [
    filters.author,
    filters.keyword,
    filters.data_types?.length,
    filters.data_format,
    filters.vessel,
    filters.source_type,
    filters.acq_year_min,
    filters.acq_year_max,
    filters.lat_min,
    filters.lat_max,
    filters.lon_min,
    filters.lon_max,
  ].filter(Boolean).length

  return (
    <div className="space-y-3">
      {/* ── Search ──────────────────────────────────────────────────────── */}
      <div className="relative">
        <input
          type="search"
          className="border border-gray-300 rounded-md text-sm px-3 py-2 w-full bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 pr-8"
          placeholder="Search title, authors, keywords, location…"
          value={filters.q ?? ''}
          onChange={(e) => set('q', e.target.value || undefined)}
        />
        {filters.q && (
          <button
            className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 text-lg leading-none"
            onClick={() => set('q', undefined)}
            aria-label="Clear search"
          >
            ×
          </button>
        )}
      </div>

      {/* ── Basic ────────────────────────────────────────────────────────── */}
      <div className="flex flex-wrap items-end gap-3">
        <div className="min-w-[180px]">
          <Label>Region</Label>
          <SelectInput value={filters.region ?? ''} onChange={(v) => set('region', v || undefined)}>
            <option value="">All regions</option>
            {REGIONS.map((r) => (
              <option key={r} value={r}>{r}</option>
            ))}
          </SelectInput>
        </div>

        <div className="w-24">
          <Label>Year from</Label>
          <NumberInput value={filters.year_min} onChange={(v) => set('year_min', v)} placeholder="1987" />
        </div>

        <div className="w-24">
          <Label>Year to</Label>
          <NumberInput value={filters.year_max} onChange={(v) => set('year_max', v)} placeholder="2025" />
        </div>

        <div className="min-w-[120px]">
          <Label>Dataset access</Label>
          <SelectInput value={filters.access ?? ''} onChange={(v) => set('access', v || undefined)}>
            <option value="">All</option>
            <option value="open">Open</option>
            <option value="restricted">Restricted</option>
            <option value="unknown">Unknown</option>
          </SelectInput>
        </div>

        <div className="min-w-[120px]">
          <Label>Paper access</Label>
          <SelectInput value={filters.paper_access ?? ''} onChange={(v) => set('paper_access', v || undefined)}>
            <option value="">All</option>
            <option value="open">Open</option>
            <option value="restricted">Restricted</option>
          </SelectInput>
        </div>

        <div className="min-w-[155px]">
          <Label>Processing status</Label>
          <SelectInput value={filters.classification ?? ''} onChange={(v) => set('classification', v || undefined)}>
            <option value="">All</option>
            <option value="RAW">RAW</option>
            <option value="SEMI_PROCESSED">Semi-processed</option>
            <option value="PROCESSED">Processed</option>
          </SelectInput>
        </div>

        <div className="min-w-[160px]">
          <Label>Repository</Label>
          <SelectInput value={filters.repository ?? ''} onChange={(v) => set('repository', v || undefined)}>
            <option value="">All repositories</option>
            {options?.repositories.map((r) => (
              <option key={r} value={r}>{r}</option>
            ))}
          </SelectInput>
        </div>

        {/* Advanced toggle */}
        <button
          className={`pb-1.5 text-xs font-medium transition-colors ${
            hasAdv ? 'text-blue-600 hover:text-blue-800' : 'text-gray-400 hover:text-gray-600'
          }`}
          onClick={() => setShowAdvanced((v) => !v)}
        >
          {showAdvanced ? '▲ Less filters' : '▼ More filters'}
          {hasAdv && !showAdvanced && (
            <span className="ml-1 bg-blue-600 text-white rounded-full px-1.5">{advCount}</span>
          )}
        </button>

        {(hasBasic || hasAdv) && (
          <button
            className="text-xs text-red-500 hover:text-red-700 hover:underline pb-1.5"
            onClick={() => { onChange({}); setShowAdvanced(false) }}
          >
            ✕ Clear all
          </button>
        )}
      </div>

      {/* ── Advanced ─────────────────────────────────────────────────────── */}
      {showAdvanced && (
        <div className="border border-gray-200 rounded-lg p-4 bg-gray-50/60 space-y-4">
          {/* Row 1: Author · Keyword · Data type */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <Label>Author</Label>
              <SuggestInput
                listId="fb-authors"
                value={filters.author ?? ''}
                onChange={(v) => set('author', v || undefined)}
                placeholder="e.g. Contreras-Reyes"
                suggestions={options?.authors}
              />
            </div>
            <div>
              <Label>Keyword</Label>
              <SuggestInput
                listId="fb-keywords"
                value={filters.keyword ?? ''}
                onChange={(v) => set('keyword', v || undefined)}
                placeholder="e.g. megathrust"
                suggestions={options?.keywords}
              />
            </div>
            <div>
              <Label>Data type</Label>
              <SelectInput
                value={filters.data_types?.[0] ?? ''}
                onChange={(v) => onChange({ ...filters, data_types: v ? [v] : undefined })}
              >
                <option value="">All types</option>
                {Object.entries(DATA_TYPE_LABELS).map(([k, label]) => (
                  <option key={k} value={k}>{label}</option>
                ))}
              </SelectInput>
            </div>
          </div>

          {/* Row 2: Format · Source type */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <Label>Data format</Label>
              <SuggestInput
                listId="fb-formats"
                value={filters.data_format ?? ''}
                onChange={(v) => set('data_format', v || undefined)}
                placeholder="e.g. SEG-Y, NetCDF"
                suggestions={options?.data_formats}
              />
            </div>
            <div>
              <Label>Source type</Label>
              <SuggestInput
                listId="fb-source"
                value={filters.source_type ?? ''}
                onChange={(v) => set('source_type', v || undefined)}
                placeholder="e.g. airgun array"
                suggestions={options?.source_types}
              />
            </div>
          </div>

          {/* Row 3: Vessel · Acq year */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <Label>Vessel</Label>
              <SuggestInput
                listId="fb-vessels"
                value={filters.vessel ?? ''}
                onChange={(v) => set('vessel', v || undefined)}
                placeholder="e.g. Langseth, Sonne"
                suggestions={options?.vessels}
              />
            </div>
            <div>
              <Label>Acquisition year from</Label>
              <NumberInput value={filters.acq_year_min} onChange={(v) => set('acq_year_min', v)} placeholder="1990" />
            </div>
            <div>
              <Label>Acquisition year to</Label>
              <NumberInput value={filters.acq_year_max} onChange={(v) => set('acq_year_max', v)} placeholder="2025" />
            </div>
          </div>

          {/* Row 4: Bounding box */}
          <div>
            <Label>Geographic bounding box</Label>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div>
                <span className="text-xs text-gray-400">Lat min</span>
                <NumberInput value={filters.lat_min} onChange={(v) => onChange({ ...filters, lat_min: v })} placeholder="-57" />
              </div>
              <div>
                <span className="text-xs text-gray-400">Lat max</span>
                <NumberInput value={filters.lat_max} onChange={(v) => onChange({ ...filters, lat_max: v })} placeholder="-17" />
              </div>
              <div>
                <span className="text-xs text-gray-400">Lon min</span>
                <NumberInput value={filters.lon_min} onChange={(v) => onChange({ ...filters, lon_min: v })} placeholder="-80" />
              </div>
              <div>
                <span className="text-xs text-gray-400">Lon max</span>
                <NumberInput value={filters.lon_max} onChange={(v) => onChange({ ...filters, lon_max: v })} placeholder="-68" />
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
