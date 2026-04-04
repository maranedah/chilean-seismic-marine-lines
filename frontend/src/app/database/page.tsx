'use client'

import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchPapers } from '@/services/api'
import { applyFilters, computeFilterOptions } from '@/utils/filters'
import type { PaperFilters } from '@/types/paper'
import FilterBar from '@/molecules/FilterBar'
import PapersTable from '@/organisms/PapersTable'
import Spinner from '@/atoms/Spinner'

export default function DatabasePage() {
  const [filters, setFilters] = useState<PaperFilters>({})

  const { data: allPapers = [], isLoading, isError } = useQuery({
    queryKey: ['papers'],
    queryFn: fetchPapers,
  })

  const filtered = useMemo(() => applyFilters(allPapers, filters), [allPapers, filters])
  const filterOptions = useMemo(() => computeFilterOptions(allPapers), [allPapers])

  function downloadCsv() {
    const headers = ['Year', 'Authors', 'Title', 'Journal', 'Region', 'Access', 'Datasets']
    const rows = filtered.map((p) => [
      p.year,
      p.authors_short,
      `"${p.title.replace(/"/g, '""')}"`,
      `"${p.journal.replace(/"/g, '""')}"`,
      p.geographic_region,
      p.access_types.join('; '),
      p.num_datasets,
    ])
    const csv = [headers, ...rows].map((r) => r.join(',')).join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'chilean_seismic_papers.csv'
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <div className="flex-none px-6 pt-5 pb-4 bg-white border-b border-gray-200 shadow-sm">
        <div className="flex items-start justify-between gap-4 mb-4">
          <div>
            <h2 className="text-lg font-bold text-gray-900">Papers Database</h2>
            <p className="text-sm text-gray-500 mt-0.5">
              {isLoading ? '…' : `${filtered.length} of ${allPapers.length} papers`}
            </p>
          </div>
          <button
            onClick={downloadCsv}
            disabled={filtered.length === 0}
            className="text-sm text-blue-600 hover:text-blue-800 border border-blue-200 hover:border-blue-400 px-3 py-1.5 rounded-md transition-colors disabled:opacity-40"
          >
            Export CSV
          </button>
        </div>
        <FilterBar filters={filters} onChange={setFilters} options={filterOptions} />
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        {isLoading && (
          <div className="flex items-center justify-center py-20">
            <Spinner size="lg" />
          </div>
        )}
        {isError && (
          <p className="text-red-500 text-center py-12">
            Failed to load papers. Is the backend running?
          </p>
        )}
        {!isLoading && !isError && filtered.length === 0 && (
          <p className="text-gray-400 text-center py-12">No papers match the current filters.</p>
        )}
        {!isLoading && !isError && filtered.length > 0 && <PapersTable papers={filtered} />}
      </div>
    </div>
  )
}
