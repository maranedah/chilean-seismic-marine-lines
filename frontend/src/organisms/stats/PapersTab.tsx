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
} from 'recharts'
import type { Stats } from '@/types/paper'
import { HorizontalBar, sortedAcqYear, sortedEntries } from './charts'

const REGION_COLORS = ['#0284c7', '#0d9488', '#7c3aed']

export default function PapersTab({ stats }: { stats: Stats }) {
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
