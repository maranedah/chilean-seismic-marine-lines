'use client'

import { useQuery } from '@tanstack/react-query'
import { fetchStats } from '@/services/api'
import StatsPanel from '@/organisms/StatsPanel'
import Spinner from '@/atoms/Spinner'

export default function ReportsPage() {
  const { data: stats, isLoading, isError } = useQuery({
    queryKey: ['stats'],
    queryFn: fetchStats,
  })

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <div className="flex-none px-6 pt-5 pb-4 bg-white border-b border-gray-200 shadow-sm">
        <h2 className="text-lg font-bold text-gray-900">Reports &amp; Statistics</h2>
        <p className="text-sm text-gray-500 mt-0.5">
          Overview of survey coverage, data availability, and processing status
        </p>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        {isLoading && (
          <div className="flex items-center justify-center py-20">
            <Spinner size="lg" />
          </div>
        )}
        {isError && (
          <p className="text-red-500 text-center py-12">
            Failed to load statistics. Is the backend running?
          </p>
        )}
        {stats && <StatsPanel stats={stats} />}
      </div>
    </div>
  )
}
