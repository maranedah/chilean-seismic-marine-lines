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
      {/* Papers per year */}
      <div className="bg-white rounded-xl p-6 border border-gray-100 shadow-sm">
        <h3 className="text-sm font-semibold text-gray-700 mb-4 uppercase tracking-wide">
          Papers per Year
        </h3>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={yearData} barSize={8}>
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

      {/* Region pie + Source type */}
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

        <HorizontalBar
          title="Data Acquisition (Source Type)"
          data={sortedEntries(stats.by_source_type)}
          color="#0d9488"
          valueLabel="Papers"
        />
      </div>

      {/* Vessel + Year acquired */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <HorizontalBar
          title="Vessel"
          data={sortedEntries(stats.by_vessel)}
          color="#7c3aed"
          valueLabel="Papers"
          labelWidth={160}
        />
        <div className="bg-white rounded-xl p-6 border border-gray-100 shadow-sm">
          <h3 className="text-sm font-semibold text-gray-700 mb-4 uppercase tracking-wide">
            Year Acquired
          </h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={sortedAcqYear(stats.by_acq_year)} barSize={8}>
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

  return (
    <div className="space-y-6">
      {/* Type + Format */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl p-6 border border-gray-100 shadow-sm">
          <h3 className="text-sm font-semibold text-gray-700 mb-4 uppercase tracking-wide">
            Datasets by Type
          </h3>
          <ResponsiveContainer width="100%" height={Math.max(dataTypeData.length * 28 + 20, 80)}>
            <BarChart data={dataTypeData} layout="vertical" barSize={14}>
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
          data={sortedEntries(stats.by_data_format)}
          color="#0284c7"
          valueLabel="Datasets"
        />
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
            <BarChart data={barData} barSize={36}>
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
        <BarChart data={data} layout="vertical" barSize={14} margin={{ left: 8, right: 24 }}>
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
