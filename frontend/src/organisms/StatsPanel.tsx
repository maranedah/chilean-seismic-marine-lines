'use client'

import { useState } from 'react'
import type { Stats } from '../types/paper'
import PapersTab from './stats/PapersTab'
import DatasetsTab from './stats/DatasetsTab'
import QualityTab from './stats/QualityTab'

interface Props {
  stats: Stats
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

      {activeTab === 'papers' && <PapersTab stats={stats} />}
      {activeTab === 'datasets' && <DatasetsTab stats={stats} />}
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
