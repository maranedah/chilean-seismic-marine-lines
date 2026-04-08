'use client'

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
import { DATA_TYPE_LABELS } from '@/utils/filters'
import { HorizontalBar, sortedEntries } from './charts'

const CLASS_COLORS: Record<string, string> = {
  RAW: '#3b82f6',
  SEMI_PROCESSED: '#f59e0b',
  PROCESSED: '#8b5cf6',
}

export default function DatasetsTab({ stats }: { stats: Stats }) {
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
