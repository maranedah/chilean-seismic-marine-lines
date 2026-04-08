'use client'

import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import dynamic from 'next/dynamic'
import { fetchPapers } from '@/services/api'
import { applyFilters, computeFilterOptions } from '@/utils/filters'
import type { PaperFilters } from '@/types/paper'
import FilterBar from '@/molecules/FilterBar'
import Spinner from '@/atoms/Spinner'

// Leaflet accesses `window` — must be loaded client-side only
const SurveyMap = dynamic(() => import('@/organisms/SurveyMap'), { ssr: false })

export default function MapPage() {
  const [filters, setFilters] = useState<PaperFilters>({})
  const [showLines, setShowLines] = useState(false)

  const { data: allPapers = [], isLoading, isError } = useQuery({
    queryKey: ['papers'],
    queryFn: fetchPapers,
  })

  const filtered = useMemo(() => applyFilters(allPapers, filters), [allPapers, filters])
  const filterOptions = useMemo(() => computeFilterOptions(allPapers), [allPapers])
  const mapped = filtered.filter((p) => p.latitude !== null)
  const openCount = mapped.filter((p) => p.has_open_data).length

  return (
    <div className="flex flex-col h-full">
      {/* Filter bar */}
      <div className="flex-none px-5 py-3 bg-white border-b border-gray-200 shadow-sm">
        <FilterBar filters={filters} onChange={setFilters} options={filterOptions} />
      </div>

      {/* Map */}
      <div className="flex-1 min-h-0 relative">
        {isLoading && (
          <div className="absolute inset-0 flex items-center justify-center bg-white z-10">
            <div className="text-center">
              <Spinner size="lg" className="mx-auto mb-3" />
              <p className="text-gray-500 text-sm">Loading survey data…</p>
            </div>
          </div>
        )}
        {isError && (
          <div className="absolute inset-0 flex items-center justify-center z-10">
            <p className="text-red-500">Failed to load papers. Is the backend running?</p>
          </div>
        )}
        {!isLoading && <SurveyMap papers={filtered} showLines={showLines} />}

        {/* Legend */}
        <div className="absolute bottom-6 left-4 bg-white/95 rounded-xl shadow-md border border-gray-200 px-4 py-3 z-[1000] text-xs space-y-2">
          <p className="font-semibold text-gray-700">
            {mapped.length} survey{mapped.length !== 1 ? 's' : ''} shown
          </p>
          <div className="space-y-1.5">
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-green-500 inline-block shrink-0" />
              <span className="text-gray-600">Open data ({openCount})</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-blue-500 inline-block shrink-0" />
              <span className="text-gray-600">
                Paper only ({mapped.filter((p) => !p.has_open_data && p.paper_url).length})
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-gray-400 inline-block shrink-0" />
              <span className="text-gray-600">
                No URL ({mapped.filter((p) => !p.paper_url).length})
              </span>
            </div>
          </div>

<p className="text-gray-400 pt-1 border-t border-gray-100">Click a dot to open paper →</p>
          <button
            className={`mt-2 pt-2 border-t border-gray-100 text-xs w-full text-left transition-colors ${
              showLines ? 'text-blue-600 font-medium' : 'text-gray-400 hover:text-gray-600'
            }`}
            onClick={() => setShowLines((v) => !v)}
          >
            {showLines ? '— Hide seismic lines' : '+ Show seismic lines'}
          </button>
        </div>
      </div>
    </div>
  )
}
