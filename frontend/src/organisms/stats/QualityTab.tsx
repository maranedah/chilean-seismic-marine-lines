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
import type { Stats } from '@/types/paper'
import { FieldCoverageTable } from './charts'

export default function QualityTab({ stats }: { stats: Stats }) {
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

// ── PDF analysis section ──────────────────────────────────────────────────────

function PdfAnalysisSection({ stats }: { stats: Stats }) {
  const total = stats.total_papers
  const analyzed = stats.pdfs_analyzed ?? 0
  const figTotal = stats.figures_total ?? 0
  const figMap = stats.figures_per_paper ?? {}
  const papersWithFigs = Object.values(figMap).filter(v => v > 0).length

  const rows = Object.entries(figMap).sort(([aId, aFigs], [bId, bFigs]) => {
    if (bFigs !== aFigs) return bFigs - aFigs
    return aId.localeCompare(bId)
  })

  const [expanded, setExpanded] = useState(false)
  const visibleRows = expanded ? rows : rows.slice(0, 10)

  return (
    <div className="bg-white rounded-xl p-6 border border-gray-100 shadow-sm space-y-4">
      <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">PDF Analysis</h3>

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
