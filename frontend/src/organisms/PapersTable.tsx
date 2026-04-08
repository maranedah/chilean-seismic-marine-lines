'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import type { PaperSummary } from '@/types/paper'
import Badge, { type BadgeVariant } from '@/atoms/Badge'

function FigureHoverPreview({ figures }: { figures: string[] }) {
  if (!figures?.length) return null
  return (
    <div
      className="absolute z-50 bottom-full left-0 mb-2 bg-white border border-gray-200 rounded-lg shadow-xl p-2 pointer-events-none"
      style={{ width: 320 }}
    >
      <div className="flex gap-1.5">
        {figures.slice(0, 3).map((src) => (
          <img
            key={src}
            src={src}
            alt=""
            className="flex-1 min-w-0 rounded object-cover"
            style={{ height: 90 }}
          />
        ))}
      </div>
    </div>
  )
}

type SortKey = 'year' | 'title' | 'authors_short' | 'journal' | 'geographic_region' | 'num_datasets' | 'completeness'

const ACCESS_VARIANT: Record<string, BadgeVariant> = {
  open: 'success',
  restricted: 'danger',
  unknown: 'neutral',
}

interface Props {
  papers: PaperSummary[]
}

export default function PapersTable({ papers }: Props) {
  const router = useRouter()
  const [sortKey, setSortKey] = useState<SortKey>('year')
  const [sortAsc, setSortAsc] = useState(false)
  const [hoveredId, setHoveredId] = useState<string | null>(null)

  function handleSort(key: SortKey) {
    if (key === sortKey) {
      setSortAsc((v) => !v)
    } else {
      setSortKey(key)
      setSortAsc(key !== 'year')
    }
  }

  const sorted = [...papers].sort((a, b) => {
    const av = a[sortKey]
    const bv = b[sortKey]
    const cmp = av < bv ? -1 : av > bv ? 1 : 0
    return sortAsc ? cmp : -cmp
  })

  function SortIcon({ col }: { col: SortKey }) {
    if (col !== sortKey) return <span className="text-gray-300 ml-1">↕</span>
    return <span className="text-blue-500 ml-1">{sortAsc ? '↑' : '↓'}</span>
  }

  const thClass =
    'px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider cursor-pointer hover:text-gray-800 select-none whitespace-nowrap'

  return (
    <div className="overflow-x-auto rounded-lg border border-gray-200 shadow-sm">
      <table className="w-full text-sm">
        <thead className="bg-gray-50 border-b border-gray-200">
          <tr>
            <th className={thClass} onClick={() => handleSort('year')}>
              Year <SortIcon col="year" />
            </th>
            <th className={thClass} onClick={() => handleSort('authors_short')}>
              Authors <SortIcon col="authors_short" />
            </th>
            <th className={thClass} onClick={() => handleSort('title')}>
              Title <SortIcon col="title" />
            </th>
            <th className={thClass} onClick={() => handleSort('journal')}>
              Journal <SortIcon col="journal" />
            </th>
            <th className={thClass} onClick={() => handleSort('geographic_region')}>
              Region <SortIcon col="geographic_region" />
            </th>
            <th className={thClass}>Access</th>
            <th className={thClass} onClick={() => handleSort('num_datasets')}>
              Datasets <SortIcon col="num_datasets" />
            </th>
            <th className={thClass} onClick={() => handleSort('completeness')}>
              Fill <SortIcon col="completeness" />
            </th>
            <th className="px-4 py-3" />
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-100">
          {sorted.map((p) => (
            <tr
              key={p.id}
              className="hover:bg-blue-50 cursor-pointer transition-colors relative"
              onClick={() => router.push(`/papers/${p.id}`)}
              onMouseEnter={() => setHoveredId(p.id)}
              onMouseLeave={() => setHoveredId(null)}
            >
              <td className="px-4 py-3 text-gray-900 font-medium">{p.year}</td>
              <td className="px-4 py-3 text-gray-600 whitespace-nowrap">{p.authors_short}</td>
              <td className="px-4 py-3 text-gray-900 max-w-xs relative">
                {hoveredId === p.id && p.preview_figures?.length > 0 && (
                  <FigureHoverPreview figures={p.preview_figures} />
                )}
                <span className="line-clamp-2 hover:text-blue-700" title={p.title}>
                  {p.title}
                </span>
              </td>
              <td className="px-4 py-3 text-gray-600 whitespace-nowrap text-xs">{p.journal}</td>
              <td className="px-4 py-3 text-gray-600 text-xs whitespace-nowrap">
                {p.geographic_region.split(' (')[0]}
              </td>
              <td className="px-4 py-3">
                <div className="flex flex-wrap gap-1">
                  {p.access_types.map((a) => (
                    <Badge key={a} label={a} variant={ACCESS_VARIANT[a] ?? 'neutral'} />
                  ))}
                </div>
              </td>
              <td className="px-4 py-3 text-center text-gray-700">{p.num_datasets}</td>
              <td className="px-4 py-3 text-center whitespace-nowrap">
                <span
                  className={`text-xs font-medium ${
                    p.completeness >= 80
                      ? 'text-green-700'
                      : p.completeness >= 60
                        ? 'text-yellow-700'
                        : 'text-red-600'
                  }`}
                >
                  {p.completeness}%
                </span>
              </td>
              <td className="px-4 py-3">
                <div className="flex items-center gap-2 justify-end">
                  <button
                    onClick={(e) => { e.stopPropagation(); router.push(`/papers/${p.id}`) }}
                    className="text-xs text-blue-600 hover:text-blue-800 border border-blue-200 hover:border-blue-400 hover:bg-blue-50 px-2.5 py-1 rounded transition-colors whitespace-nowrap"
                  >
                    View summary
                  </button>
                  {p.paper_url && (
                    <a
                      href={p.paper_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      onClick={(e) => e.stopPropagation()}
                      className="text-xs text-gray-600 hover:text-gray-900 border border-gray-200 hover:border-gray-400 hover:bg-gray-50 px-2.5 py-1 rounded transition-colors whitespace-nowrap"
                    >
                      View paper ↗
                    </a>
                  )}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
