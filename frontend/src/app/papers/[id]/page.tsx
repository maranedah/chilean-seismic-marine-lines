'use client'

import { useParams, useRouter } from 'next/navigation'
import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { fetchFigures, fetchPaper } from '@/services/api'
import Badge, { type BadgeVariant } from '@/atoms/Badge'
import Button from '@/atoms/Button'
import Field from '@/atoms/Field'
import Section from '@/atoms/Section'
import DatasetItem from '@/molecules/DatasetItem'
import Spinner from '@/atoms/Spinner'
import GalleryImage from '@/organisms/GalleryImage'

const CLASS_VARIANT: Record<string, BadgeVariant> = {
  RAW: 'info',
  SEMI_PROCESSED: 'warning',
  PROCESSED: 'purple',
}

const CONFIDENCE_VARIANT: Record<string, BadgeVariant> = {
  high: 'success',
  medium: 'warning',
  low: 'danger',
}

export default function PaperDetailPage() {
  const params = useParams()
  const id = params?.id as string
  const router = useRouter()

  const {
    data: paper,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ['paper', id],
    queryFn: () => fetchPaper(id),
    enabled: !!id,
  })

  const { data: figuresManifest } = useQuery({
    queryKey: ['figures', id],
    queryFn: () => fetchFigures(id),
    enabled: !!id,
  })


  const [bibtexCopied, setBibtexCopied] = useState(false)

  function copyBibTeX() {
    if (!paper) return
    const authors = paper.authors.join(' and ')
    const lines = [
      `@article{${paper.id},`,
      `  title   = {${paper.title}},`,
      `  author  = {${authors}},`,
      `  journal = {${paper.journal}},`,
      `  year    = {${paper.year}},`,
      ...(paper.doi ? [`  doi     = {${paper.doi}},`] : []),
      `}`,
    ]
    navigator.clipboard.writeText(lines.join('\n')).then(() => {
      setBibtexCopied(true)
      setTimeout(() => setBibtexCopied(false), 2000)
    })
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Spinner size="lg" />
      </div>
    )
  }

  if (isError || !paper) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4">
        <p className="text-gray-500">Paper not found or failed to load.</p>
        <Button variant="secondary" onClick={() => router.back()}>
          ← Go back
        </Button>
      </div>
    )
  }

  const doiUrl = paper.doi ? `https://doi.org/${paper.doi}` : null

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Sticky header */}
      <div className="flex-none px-6 py-4 bg-white border-b border-gray-200 shadow-sm">
        <div className="flex items-start gap-4">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => router.back()}
            className="mt-0.5 shrink-0"
          >
            ← Back
          </Button>
          <div className="min-w-0">
            <h1 className="text-lg font-bold text-gray-900 leading-snug">{paper.title}</h1>
            <div className="flex flex-wrap items-center gap-2 mt-2">
              <span className="text-sm text-gray-500">
                {paper.authors
                  .slice(0, 3)
                  .map((a) => a.split(',')[0])
                  .join(', ')}
                {paper.authors.length > 3 ? ' et al.' : ''}
              </span>
              <span className="text-gray-300">·</span>
              <span className="text-sm font-medium text-gray-700">{paper.year}</span>
              <span className="text-gray-300">·</span>
              <span className="text-sm text-gray-500 italic">{paper.journal}</span>
              {paper.analysis_confidence && (
                <Badge
                  label={`Confidence: ${paper.analysis_confidence}`}
                  variant={CONFIDENCE_VARIANT[paper.analysis_confidence] ?? 'neutral'}
                />
              )}
              {paper.completeness != null && (
                <Badge
                  label={`${paper.completeness}% complete`}
                  variant={paper.completeness >= 80 ? 'success' : paper.completeness >= 60 ? 'warning' : 'danger'}
                />
              )}
            </div>
            <div className="flex flex-wrap gap-3 mt-3">
              {doiUrl && (
                <a
                  href={doiUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs text-blue-600 hover:underline"
                >
                  DOI: {paper.doi}
                </a>
              )}
              {paper.open_access_url && (
                <a
                  href={paper.open_access_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs bg-green-50 text-green-700 border border-green-200 px-2 py-0.5 rounded hover:bg-green-100"
                >
                  Open Access PDF ↗
                </a>
              )}
              {!paper.open_access_url && paper.url && (
                <a
                  href={paper.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs bg-blue-50 text-blue-700 border border-blue-200 px-2 py-0.5 rounded hover:bg-blue-100"
                >
                  View Paper ↗
                </a>
              )}
              <button
                onClick={copyBibTeX}
                className="text-xs bg-gray-50 text-gray-700 border border-gray-200 px-2 py-0.5 rounded hover:bg-gray-100 transition-colors"
              >
                {bibtexCopied ? 'Copied!' : 'Copy BibTeX'}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto p-6 space-y-5">
        {paper.abstract && (
          <Section title="Abstract">
            <p className="text-sm text-gray-700 leading-relaxed">{paper.abstract}</p>
          </Section>
        )}

        {figuresManifest && figuresManifest.figures.length > 0 && (
          <Section title={`Gallery (${figuresManifest.figures.length})`}>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3">
              {figuresManifest.figures.map((fig) => (
                <GalleryImage key={fig.filename} figure={fig} paperId={id} />
              ))}
            </div>
          </Section>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          {paper.location && (
            <Section title="Location">
              <div className="space-y-2">
                <Field label="City" value={paper.location.city} />
                <Field
                  label="Coordinates"
                  value={
                    paper.location.latitude != null && paper.location.longitude != null
                      ? `${paper.location.latitude}°, ${paper.location.longitude}°`
                      : undefined
                  }
                />
                <Field label="Region" value={paper.location.region} />
                <Field label="Country" value={paper.location.country} />
                <Field label="Description" value={paper.location.description} />
                <Field label="Tectonic setting" value={paper.tectonic_setting} />
                {paper.associated_earthquakes?.length > 0 && (
                  <div>
                    <p className="text-xs font-medium text-gray-500 mb-1">Associated earthquakes</p>
                    <div className="flex flex-wrap gap-1.5">
                      {paper.associated_earthquakes.map((eq, i) => (
                        <span key={i} className="text-xs bg-red-50 text-red-700 border border-red-100 px-2 py-0.5 rounded-full">{eq}</span>
                      ))}
                    </div>
                  </div>
                )}
                {paper.location.seismic_lines.length > 0 && (
                  <div className="pt-2">
                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
                      Seismic Lines ({paper.location.seismic_lines.length})
                    </p>
                    <div className="space-y-1.5">
                      {paper.location.seismic_lines.map((line, i) => (
                        <div
                          key={i}
                          className="text-xs bg-gray-50 rounded p-2 border border-gray-100"
                        >
                          <div className="flex items-center justify-between gap-2">
                            <p className="font-medium text-gray-800">{line.name}</p>
                            <div className="flex gap-1 shrink-0">
                              {line.profile_orientation && (
                                <span className="text-gray-400 italic">{line.profile_orientation}</span>
                              )}
                              {line.depth_km != null && (
                                <span className="text-gray-400">· {line.depth_km} km deep</span>
                              )}
                            </div>
                          </div>
                          <p className="text-gray-500 mt-0.5">
                            ({line.lat_start}, {line.lon_start}) → ({line.lat_end},{' '}
                            {line.lon_end})
                            {line.length_km ? ` · ${line.length_km} km` : ''}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </Section>
          )}

          {paper.acquisition && (
            <Section title="Acquisition">
              <div className="space-y-2">
                <Field label="Vessel" value={paper.acquisition.vessel?.join(', ')} />
                <Field label="Expeditions" value={paper.acquisition.expeditions?.join('; ')} />
                <Field label="Year acquired" value={paper.acquisition.year_acquired} />
                <Field label="Source type" value={paper.acquisition.source_type?.join(', ')} />
                <Field
                  label="Source volume"
                  value={
                    paper.acquisition.source_volume_cui
                      ? `${paper.acquisition.source_volume_cui} cui`
                      : undefined
                  }
                />
                <Field
                  label="Streamer length"
                  value={
                    paper.acquisition.streamer_length_m
                      ? `${paper.acquisition.streamer_length_m} m`
                      : undefined
                  }
                />
                <Field label="Channels" value={paper.acquisition.channel_count} />
                <Field
                  label="Sample rate"
                  value={
                    paper.acquisition.sample_rate_ms
                      ? `${paper.acquisition.sample_rate_ms} ms`
                      : undefined
                  }
                />
                <Field
                  label="Record length"
                  value={
                    paper.acquisition.record_length_s
                      ? `${paper.acquisition.record_length_s} s`
                      : undefined
                  }
                />
                <Field label="Fold" value={paper.acquisition.fold} />
                <Field
                  label="Shot interval"
                  value={paper.acquisition.shot_interval_m != null ? `${paper.acquisition.shot_interval_m} m` : undefined}
                />
                <Field
                  label="Group interval"
                  value={paper.acquisition.group_interval_m != null ? `${paper.acquisition.group_interval_m} m` : undefined}
                />
                <Field
                  label="OBS spacing"
                  value={paper.acquisition.obs_spacing_km != null ? `${paper.acquisition.obs_spacing_km} km` : undefined}
                />
                <Field
                  label="Nearest offset"
                  value={paper.acquisition.nearest_offset_m != null ? `${paper.acquisition.nearest_offset_m} m` : undefined}
                />
                <Field
                  label="Frequency range"
                  value={
                    paper.acquisition.frequency_range_hz
                      ? `${paper.acquisition.frequency_range_hz[0]}–${paper.acquisition.frequency_range_hz[1]} Hz`
                      : undefined
                  }
                />
                <Field
                  label="Depth penetration"
                  value={paper.acquisition.depth_penetration_km != null ? `${paper.acquisition.depth_penetration_km} km` : undefined}
                />
              </div>
            </Section>
          )}
        </div>

        <Section title={`Datasets (${paper.data.length})`}>
          {paper.data.length === 0 ? (
            <p className="text-sm text-gray-400 italic">No datasets recorded.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left">
                <thead>
                  <tr className="border-b border-gray-200">
                    <th className="pb-2 pr-4 text-xs font-semibold text-gray-500 uppercase tracking-wide">Name</th>
                    <th className="pb-2 pr-4 text-xs font-semibold text-gray-500 uppercase tracking-wide">Type</th>
                    <th className="pb-2 pr-4 text-xs font-semibold text-gray-500 uppercase tracking-wide">Format</th>
                    <th className="pb-2 pr-4 text-xs font-semibold text-gray-500 uppercase tracking-wide">Repository</th>
                    <th className="pb-2 pr-4 text-xs font-semibold text-gray-500 uppercase tracking-wide">Size</th>
                    <th className="pb-2 pr-4 text-xs font-semibold text-gray-500 uppercase tracking-wide">CDP Spacing</th>
                    <th className="pb-2 pr-4 text-xs font-semibold text-gray-500 uppercase tracking-wide">Status</th>
                    <th className="pb-2 text-xs font-semibold text-gray-500 uppercase tracking-wide">Download</th>
                  </tr>
                </thead>
                <tbody>
                  {paper.data.map((ds, i) => (
                    <DatasetItem key={i} dataset={ds} />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Section>

        {paper.processing && (
          <Section title="Processing">
            <div className="space-y-3">
              <Badge
                label={paper.processing.classification}
                variant={CLASS_VARIANT[paper.processing.classification] ?? 'neutral'}
              />
              {paper.processing.summary && (
                <p className="text-sm text-gray-700 leading-relaxed">{paper.processing.summary}</p>
              )}
              {paper.processing.workflow.length > 0 && (
                <div>
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
                    Workflow
                  </p>
                  <ol className="space-y-1">
                    {paper.processing.workflow.map((step, i) => (
                      <li key={i} className="text-sm text-gray-700 flex gap-2">
                        <span className="text-gray-400 shrink-0">{i + 1}.</span>
                        <span>{step.replace(/^\d+\.\s*/, '')}</span>
                      </li>
                    ))}
                  </ol>
                </div>
              )}
              {paper.processing.migration_type && (
                <p className="text-sm text-gray-600">
                  <span className="font-medium">Migration: </span>
                  {paper.processing.migration_type}
                </p>
              )}
              {paper.processing.software.length > 0 && (
                <p className="text-sm text-gray-600">
                  <span className="font-medium">Software: </span>
                  {paper.processing.software.join(', ')}
                </p>
              )}
              {paper.processing.notes && (
                <p className="text-xs text-gray-400 italic">{paper.processing.notes}</p>
              )}
            </div>
          </Section>
        )}

        {paper.analysis_notes && (
          <Section title="Analysis Notes">
            <p className="text-sm text-gray-600 leading-relaxed italic">{paper.analysis_notes}</p>
          </Section>
        )}

        {paper.keywords.length > 0 && (
          <Section title="Keywords">
            <div className="flex flex-wrap gap-2">
              {paper.keywords.map((kw, i) => (
                <Badge key={i} label={kw} variant="neutral" />
              ))}
            </div>
          </Section>
        )}
      </div>
    </div>
  )
}
