'use client'

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'

// ── Pure helpers ──────────────────────────────────────────────────────────────

export function sortedEntries(freq: Record<string, number>) {
  return Object.entries(freq)
    .sort(([, a], [, b]) => b - a)
    .map(([name, count]) => ({ name, count }))
}

export function sortedAcqYear(freq: Record<string, number>) {
  return Object.entries(freq)
    .map(([year, count]) => ({ year: Number(year), count }))
    .sort((a, b) => a.year - b.year)
}

// ── Shared chart components ───────────────────────────────────────────────────

export function HorizontalBar({
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

export function FieldCoverageTable({
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
