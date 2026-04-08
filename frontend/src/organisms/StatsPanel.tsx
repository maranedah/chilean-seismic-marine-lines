'use client'

import { useState } from 'react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from 'recharts'
import type { Stats } from '../types/paper'
import { DATA_TYPE_LABELS } from '../utils/filters'

interface Props {
  stats: Stats
}

const REGION_COLORS = ['#0284c7', '#0d9488', '#7c3aed']
const CLASS_COLORS: Record<string, string> = {
  RAW: '#3b82f6',
  SEMI_PROCESSED: '#f59e0b',
  PROCESSED: '#8b5cf6',
}

type Tab = 'papers' | 'datasets' | 'quality'

export default function StatsPanel({ stats }: Props) {
  const [activeTab, setActiveTab] = useState<Tab>('papers')

  return (
    <div className="space-y-6">
      {/* ── Tab bar ──────────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-3 gap-4">
        <TabCard
          label="Papers"
          value={stats.total_papers}
          subtitle={`${stats.year_range[0]}–${stats.year_range[1]}`}
          active={activeTab === 'papers'}
          activeColor="border-blue-500 bg-blue-50"
          activeText="text-blue-700"
          onClick={() => setActiveTab('papers')}
        />
        <TabCard
          label="Datasets"
          value={stats.total_datasets}
          subtitle={`${stats.open_access_count} open · ${stats.restricted_count} restricted · ${stats.unknown_count} unknown`}
          active={activeTab === 'datasets'}
          activeColor="border-purple-500 bg-purple-50"
          activeText="text-purple-700"
          onClick={() => setActiveTab('datasets')}
        />
        <TabCard
          label="Avg. Completeness"
          value={stats.avg_completeness}
          subtitle={`${stats.completeness_buckets.high ?? 0} high · ${stats.completeness_buckets.medium ?? 0} medium · ${stats.completeness_buckets.low ?? 0} low`}
          active={activeTab === 'quality'}
          activeColor="border-emerald-500 bg-emerald-50"
          activeText="text-emerald-700"
          onClick={() => setActiveTab('quality')}
          valueSuffix="%"
        />
      </div>

      {/* ── Papers tab ───────────────────────────────────────────────────────── */}
      {activeTab === 'papers' && <PapersTab stats={stats} />}

      {/* ── Datasets tab ─────────────────────────────────────────────────────── */}
      {activeTab === 'datasets' && <DatasetsTab stats={stats} />}

      {/* ── Quality tab ──────────────────────────────────────────────────────── */}
      {activeTab === 'quality' && <QualityTab stats={stats} />}
    </div>
  )
}

// ── Tab card button ───────────────────────────────────────────────────────────

function TabCard({
  label,
  value,
  subtitle,
  active,
  activeColor,
  activeText,
  onClick,
  valueSuffix = '',
}: {
  label: string
  value: number
  subtitle: string
  active: boolean
  activeColor: string
  activeText: string
  onClick: () => void
  valueSuffix?: string
}) {
  return (
    <button
      onClick={onClick}
      className={`text-left rounded-xl p-5 border-2 transition-colors shadow-sm w-full
        ${active ? activeColor : 'border-gray-100 bg-white hover:bg-gray-50'}`}
    >
      <div className="text-xs font-semibold uppercase tracking-wide text-gray-500 mb-1">
        {label}
      </div>
      <div className={`text-3xl font-bold ${active ? activeText : 'text-gray-800'}`}>
        {value}{valueSuffix}
      </div>
      <div className="text-xs text-gray-400 mt-1">{subtitle}</div>
    </button>
  )
}

// ── Papers tab content ────────────────────────────────────────────────────────

function PapersTab({ stats }: { stats: Stats }) {
  const yearData = Object.entries(stats.by_year)
    .map(([year, count]) => ({ year: Number(year), count }))
    .sort((a, b) => a.year - b.year)

  const regionData = Object.entries(stats.by_region).map(([name, value], i) => ({
    name: name.split(' (')[0],
    value,
    fill: REGION_COLORS[i % REGION_COLORS.length],
  }))

  return (
    <div className="space-y-6">
      {/* Row 1: Data Acquisition + Vessel */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <HorizontalBar
          title="Data Acquisition (Source Type)"
          data={sortedEntries(stats.by_source_type)}
          color="#0d9488"
          valueLabel="Papers"
        />
        <HorizontalBar
          title="Vessel"
          data={sortedEntries(stats.by_vessel)}
          color="#7c3aed"
          valueLabel="Papers"
          labelWidth={160}
        />
      </div>

      {/* Row 2: Papers by Region + Papers per Year */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl p-6 border border-gray-100 shadow-sm">
          <h3 className="text-sm font-semibold text-gray-700 mb-4 uppercase tracking-wide">
            Papers by Region
          </h3>
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie
                data={regionData}
                cx="50%"
                cy="50%"
                outerRadius={70}
                dataKey="value"
                label={({ name, percent }: { name: string; percent: number }) =>
                  `${name} ${(percent * 100).toFixed(0)}%`
                }
                labelLine={false}
                fontSize={11}
              >
                {regionData.map((entry, i) => (
                  <Cell key={i} fill={entry.fill} />
                ))}
              </Pie>
              <Tooltip contentStyle={{ fontSize: 12 }} />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-white rounded-xl p-6 border border-gray-100 shadow-sm">
          <h3 className="text-sm font-semibold text-gray-700 mb-4 uppercase tracking-wide">
            Papers per Year
          </h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={yearData} barCategoryGap="4%">
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis
                dataKey="year"
                tick={{ fontSize: 11 }}
                tickFormatter={(v: number) => (v % 5 === 0 ? String(v) : '')}
              />
              <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
              <Tooltip
                contentStyle={{ fontSize: 12 }}
                labelFormatter={(v) => `Year: ${v}`}
                formatter={(v: number) => [v, 'Papers']}
              />
              <Bar dataKey="count" fill="#0284c7" radius={[2, 2, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Row 3: Year Acquired */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl p-6 border border-gray-100 shadow-sm">
          <h3 className="text-sm font-semibold text-gray-700 mb-4 uppercase tracking-wide">
            Year Acquired
          </h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={sortedAcqYear(stats.by_acq_year)} barCategoryGap="4%">
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis
                dataKey="year"
                tick={{ fontSize: 11 }}
                tickFormatter={(v: number) => (v % 5 === 0 ? String(v) : '')}
              />
              <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
              <Tooltip
                contentStyle={{ fontSize: 12 }}
                labelFormatter={(v) => `Year: ${v}`}
                formatter={(v: number) => [v, 'Surveys']}
              />
              <Bar dataKey="count" fill="#f59e0b" radius={[2, 2, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  )
}

// ── Datasets tab content ──────────────────────────────────────────────────────

function DatasetsTab({ stats }: { stats: Stats }) {
  const dataTypeData = Object.entries(stats.by_data_type)
    .map(([key, count]) => ({ name: DATA_TYPE_LABELS[key] ?? key, count }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 10)

  const classData = Object.entries(stats.by_classification).map(([name, value]) => ({
    name,
    value,
    fill: CLASS_COLORS[name] ?? '#6b7280',
  }))

  const sizeByTypeData = Object.entries(stats.size_gb_by_type ?? {})
    .map(([key, gb]) => ({ name: DATA_TYPE_LABELS[key] ?? key, gb }))
    .sort((a, b) => b.gb - a.gb)

  const formatData = sortedEntries(stats.datasets_by_format ?? {})

  const sizeKnown = stats.size_known_count ?? 0
  const sizeUnknown = stats.size_unknown_count ?? 0
  const sizeTotal = sizeKnown + sizeUnknown
  const sizePieData = [
    { name: 'Known size', value: sizeKnown, fill: '#0d9488' },
    { name: 'Unknown size', value: sizeUnknown, fill: '#e5e7eb' },
  ]
  const totalGb = Object.values(stats.size_gb_by_type ?? {}).reduce((a, b) => a + b, 0)

  return (
    <div className="space-y-6">
      {/* Type + Format */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl p-6 border border-gray-100 shadow-sm">
          <h3 className="text-sm font-semibold text-gray-700 mb-4 uppercase tracking-wide">
            Datasets by Type
          </h3>
          <ResponsiveContainer width="100%" height={Math.max(dataTypeData.length * 28 + 20, 80)}>
            <BarChart data={dataTypeData} layout="vertical" barCategoryGap="4%">
              <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f0f0f0" />
              <XAxis type="number" tick={{ fontSize: 11 }} allowDecimals={false} />
              <YAxis type="category" dataKey="name" tick={{ fontSize: 11 }} width={110} />
              <Tooltip contentStyle={{ fontSize: 12 }} formatter={(v: number) => [v, 'Datasets']} />
              <Bar dataKey="count" fill="#0d9488" radius={[0, 2, 2, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <HorizontalBar
          title="Data Format"
          data={formatData}
          color="#0284c7"
          valueLabel="Datasets"
        />
      </div>

      {/* Repository */}
      <HorizontalBar
        title="Repository"
        data={sortedEntries(stats.by_repository ?? {})}
        color="#0284c7"
        valueLabel="Datasets"
        labelWidth={180}
      />

      {/* Size stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* GB by type bar */}
        <div className="md:col-span-2 bg-white rounded-xl p-6 border border-gray-100 shadow-sm">
          <div className="flex items-baseline justify-between mb-4">
            <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">
              Volume by Data Type
            </h3>
            <span className="text-xs text-gray-400">{totalGb.toFixed(1)} GB total (known)</span>
          </div>
          {sizeByTypeData.length > 0 ? (
            <ResponsiveContainer width="100%" height={Math.max(sizeByTypeData.length * 32 + 20, 80)}>
              <BarChart data={sizeByTypeData} layout="vertical" barCategoryGap="6%" margin={{ left: 8, right: 40 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f0f0f0" />
                <XAxis type="number" tick={{ fontSize: 11 }} unit=" GB" />
                <YAxis type="category" dataKey="name" tick={{ fontSize: 11 }} width={120} />
                <Tooltip
                  contentStyle={{ fontSize: 12 }}
                  formatter={(v: number) => [`${v.toFixed(1)} GB`, 'Size']}
                />
                <Bar dataKey="gb" fill="#7c3aed" radius={[0, 3, 3, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-sm text-gray-400 italic">No size data available.</p>
          )}
        </div>

        {/* Known vs unknown pie */}
        <div className="bg-white rounded-xl p-6 border border-gray-100 shadow-sm flex flex-col">
          <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-4">
            Size Coverage
          </h3>
          <div className="flex-1 flex flex-col items-center justify-center gap-4">
            <ResponsiveContainer width="100%" height={160}>
              <PieChart>
                <Pie
                  data={sizePieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={45}
                  outerRadius={70}
                  dataKey="value"
                  startAngle={90}
                  endAngle={-270}
                >
                  {sizePieData.map((entry, i) => (
                    <Cell key={i} fill={entry.fill} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ fontSize: 12 }} formatter={(v: number) => [v, 'Datasets']} />
              </PieChart>
            </ResponsiveContainer>
            <div className="w-full space-y-2 text-xs">
              <div className="flex items-center justify-between">
                <span className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-teal-600 inline-block" />
                  Known
                </span>
                <span className="font-medium text-gray-700">
                  {sizeKnown} ({sizeTotal > 0 ? Math.round(100 * sizeKnown / sizeTotal) : 0}%)
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-gray-200 inline-block" />
                  Unknown
                </span>
                <span className="font-medium text-gray-700">
                  {sizeUnknown} ({sizeTotal > 0 ? Math.round(100 * sizeUnknown / sizeTotal) : 0}%)
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Classification pie */}
      <div className="bg-white rounded-xl p-6 border border-gray-100 shadow-sm">
        <h3 className="text-sm font-semibold text-gray-700 mb-4 uppercase tracking-wide">
          Dataset Classification
        </h3>
        <ResponsiveContainer width="100%" height={220}>
          <PieChart>
            <Pie
              data={classData}
              cx="50%"
              cy="50%"
              outerRadius={80}
              dataKey="value"
              label={({ name, value }: { name: string; value: number }) => `${name}: ${value}`}
              labelLine={false}
              fontSize={11}
            >
              {classData.map((entry, i) => (
                <Cell key={i} fill={entry.fill} />
              ))}
            </Pie>
            <Tooltip contentStyle={{ fontSize: 12 }} />
            <Legend iconSize={10} wrapperStyle={{ fontSize: 12 }} />
          </PieChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

// ── Quality tab content ───────────────────────────────────────────────────────

function QualityTab({ stats }: { stats: Stats }) {
  const buckets = stats.completeness_buckets
  const total = (buckets.high ?? 0) + (buckets.medium ?? 0) + (buckets.low ?? 0)

  const pieData = [
    { name: 'High (≥80%)', value: buckets.high ?? 0, fill: '#16a34a' },
    { name: 'Medium (60–79%)', value: buckets.medium ?? 0, fill: '#d97706' },
    { name: 'Low (<60%)', value: buckets.low ?? 0, fill: '#dc2626' },
  ]

  const barData = [
    { name: 'High (≥80%)', count: buckets.high ?? 0, fill: '#16a34a' },
    { name: 'Medium (60–79%)', count: buckets.medium ?? 0, fill: '#d97706' },
    { name: 'Low (<60%)', count: buckets.low ?? 0, fill: '#dc2626' },
  ]

  return (
    <div className="space-y-6">
      {/* Summary tiles */}
      <div className="grid grid-cols-3 gap-4">
        {pieData.map(({ name, value, fill }) => (
          <div
            key={name}
            className="bg-white rounded-xl p-5 border border-gray-100 shadow-sm text-center"
          >
            <div className="text-3xl font-bold" style={{ color: fill }}>
              {value}
            </div>
            <div className="text-xs text-gray-500 mt-1">{name}</div>
            <div className="text-xs text-gray-400">
              {total > 0 ? `${Math.round((value / total) * 100)}%` : '—'}
            </div>
          </div>
        ))}
      </div>

      {/* Pie + bar */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl p-6 border border-gray-100 shadow-sm">
          <h3 className="text-sm font-semibold text-gray-700 mb-4 uppercase tracking-wide">
            Distribution
          </h3>
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie
                data={pieData}
                cx="50%"
                cy="50%"
                outerRadius={80}
                dataKey="value"
                label={({ name, value }: { name: string; value: number }) =>
                  value > 0 ? `${value}` : ''
                }
                labelLine={false}
                fontSize={12}
              >
                {pieData.map((entry, i) => (
                  <Cell key={i} fill={entry.fill} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{ fontSize: 12 }}
                formatter={(v: number) => [v, 'Papers']}
              />
              <Legend iconSize={10} wrapperStyle={{ fontSize: 12 }} />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-white rounded-xl p-6 border border-gray-100 shadow-sm">
          <h3 className="text-sm font-semibold text-gray-700 mb-4 uppercase tracking-wide">
            Papers by Completeness Band
          </h3>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={barData} barCategoryGap="4%">
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="name" tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
              <Tooltip
                contentStyle={{ fontSize: 12 }}
                formatter={(v: number) => [v, 'Papers']}
              />
              <Bar dataKey="count" radius={[3, 3, 0, 0]}>
                {barData.map((entry, i) => (
                  <Cell key={i} fill={entry.fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* PDF Analysis */}
      <PdfAnalysisSection stats={stats} />

      {/* Per-field coverage */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <FieldCoverageTable
          title="Paper Field Coverage"
          data={stats.paper_field_fill ?? {}}
          color="#0284c7"
        />
        <FieldCoverageTable
          title="Dataset Field Coverage"
          data={stats.dataset_field_fill ?? {}}
          color="#7c3aed"
        />
      </div>

      {/* Guidance note */}
      <p className="text-xs text-gray-400 italic">
        Completeness is scored across 12 fields: title, authors, year, DOI, abstract, keywords,
        location, bounding box, seismic lines, acquisition, vessel, and datasets.
        Papers below 60% are candidates for re-analysis.
      </p>
    </div>
  )
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function sortedEntries(freq: Record<string, number>) {
  return Object.entries(freq)
    .sort(([, a], [, b]) => b - a)
    .map(([name, count]) => ({ name, count }))
}

function sortedAcqYear(freq: Record<string, number>) {
  return Object.entries(freq)
    .map(([year, count]) => ({ year: Number(year), count }))
    .sort((a, b) => a.year - b.year)
}

// ── PDF analysis section ──────────────────────────────────────────────────────

function PdfAnalysisSection({ stats }: { stats: Stats }) {
  const total = stats.total_papers
  const analyzed = stats.pdfs_analyzed ?? 0
  const figTotal = stats.figures_total ?? 0
  const figMap = stats.figures_per_paper ?? {}
  const papersWithFigs = Object.values(figMap).filter(v => v > 0).length

  // Build per-paper rows sorted by figures desc, then name
  const rows = Object.entries(figMap).sort(([aId, aFigs], [bId, bFigs]) => {
    if (bFigs !== aFigs) return bFigs - aFigs
    return aId.localeCompare(bId)
  })

  const [expanded, setExpanded] = useState(false)
  const visibleRows = expanded ? rows : rows.slice(0, 10)

  return (
    <div className="bg-white rounded-xl p-6 border border-gray-100 shadow-sm space-y-4">
      <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">PDF Analysis</h3>

      {/* Summary tiles */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-gray-50 rounded-lg p-4 text-center">
          <div className="text-2xl font-bold text-sky-600">{analyzed} / {total}</div>
          <div className="text-xs text-gray-500 mt-1">PDFs analyzed (text extracted)</div>
        </div>
        <div className="bg-gray-50 rounded-lg p-4 text-center">
          <div className="text-2xl font-bold text-emerald-600">{papersWithFigs} / {total}</div>
          <div className="text-xs text-gray-500 mt-1">Papers with figures extracted</div>
        </div>
        <div className="bg-gray-50 rounded-lg p-4 text-center">
          <div className="text-2xl font-bold text-violet-600">{figTotal}</div>
          <div className="text-xs text-gray-500 mt-1">Total figures extracted</div>
        </div>
      </div>

      {/* Per-paper figure count table */}
      <div>
        <div className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">
          Figures per paper
        </div>
        <div className="divide-y divide-gray-50">
          {visibleRows.map(([paperId, count]) => {
            const barPct = rows.length > 0 ? Math.round((count / (rows[0][1] || 1)) * 100) : 0
            return (
              <div key={paperId} className="flex items-center gap-3 py-1.5 text-xs">
                <span className="w-72 shrink-0 text-gray-600 truncate font-mono" title={paperId}>
                  {paperId}
                </span>
                <div className="flex-1 bg-gray-100 rounded-full h-2 overflow-hidden">
                  {count > 0 && (
                    <div
                      className="h-2 rounded-full bg-violet-400"
                      style={{ width: `${barPct}%` }}
                    />
                  )}
                </div>
                <span className="w-8 text-right tabular-nums font-medium text-gray-700">
                  {count}
                </span>
              </div>
            )
          })}
        </div>
        {rows.length > 10 && (
          <button
            onClick={() => setExpanded(e => !e)}
            className="mt-2 text-xs text-sky-600 hover:underline"
          >
            {expanded ? 'Show less' : `Show all ${rows.length} papers`}
          </button>
        )}
      </div>
    </div>
  )
}

// ── Field coverage table ──────────────────────────────────────────────────────

function FieldCoverageTable({
  title,
  data,
  color,
}: {
  title: string
  data: Record<string, number>
  color: string
}) {
  const rows = Object.entries(data).sort(([, a], [, b]) => b - a)

  return (
    <div className="bg-white rounded-xl p-6 border border-gray-100 shadow-sm">
      <h3 className="text-sm font-semibold text-gray-700 mb-4 uppercase tracking-wide">{title}</h3>
      <div className="space-y-2">
        {rows.map(([field, pct]) => {
          const nullPct = 100 - pct
          const barColor = pct >= 80 ? '#16a34a' : pct >= 50 ? color : '#dc2626'
          return (
            <div key={field} className="flex items-center gap-3 text-xs">
              <span className="w-36 shrink-0 text-gray-600 truncate" title={field}>{field}</span>
              <div className="flex-1 bg-gray-100 rounded-full h-2 overflow-hidden">
                <div
                  className="h-2 rounded-full transition-all"
                  style={{ width: `${pct}%`, backgroundColor: barColor }}
                />
              </div>
              <span className="w-16 text-right shrink-0 tabular-nums">
                <span className="font-medium text-gray-700">{pct}%</span>
                {nullPct > 0 && (
                  <span className="text-gray-400 ml-1">({nullPct.toFixed(0)}% null)</span>
                )}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ── Shared horizontal bar chart ───────────────────────────────────────────────

function HorizontalBar({
  title,
  data,
  color,
  valueLabel,
  labelWidth = 120,
}: {
  title: string
  data: { name: string; count: number }[]
  color: string
  valueLabel: string
  labelWidth?: number
}) {
  const height = Math.max(data.length * 28 + 20, 80)
  return (
    <div className="bg-white rounded-xl p-6 border border-gray-100 shadow-sm">
      <h3 className="text-sm font-semibold text-gray-700 mb-4 uppercase tracking-wide">
        {title}
      </h3>
      <ResponsiveContainer width="100%" height={height}>
        <BarChart data={data} layout="vertical" barCategoryGap="4%" margin={{ left: 8, right: 24 }}>
          <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f0f0f0" />
          <XAxis type="number" tick={{ fontSize: 11 }} allowDecimals={false} />
          <YAxis type="category" dataKey="name" tick={{ fontSize: 11 }} width={labelWidth} />
          <Tooltip
            contentStyle={{ fontSize: 12 }}
            formatter={(v: number) => [v, valueLabel]}
          />
          <Bar dataKey="count" fill={color} radius={[0, 2, 2, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
