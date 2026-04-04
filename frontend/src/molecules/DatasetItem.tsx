'use client'

import type { Dataset } from '../types/paper'
import Badge, { type BadgeVariant } from '../atoms/Badge'
import { DATA_TYPE_LABELS } from '../utils/filters'

const ACCESS_VARIANT: Record<string, BadgeVariant> = {
  open: 'success',
  restricted: 'danger',
  embargoed: 'warning',
  unknown: 'neutral',
}

const CLASSIFICATION_VARIANT: Record<string, BadgeVariant> = {
  RAW: 'info',
  SEMI_PROCESSED: 'warning',
  PROCESSED: 'purple',
}

interface Props {
  dataset: Dataset
}

export default function DatasetItem({ dataset }: Props) {
  const typeLabel =
    DATA_TYPE_LABELS[dataset.data_type] ||
    dataset.data_type?.replace(/_/g, ' ') ||
    'Unknown type'

  return (
    <tr className="border-b border-gray-100 last:border-0 hover:bg-gray-50/60">
      <td className="py-3 pr-4 align-top">
        <p className="text-sm font-medium text-gray-900 leading-snug">
          {dataset.name || typeLabel}
        </p>
        {dataset.description && (
          <p className="text-xs text-gray-400 mt-0.5 leading-relaxed">{dataset.description}</p>
        )}
      </td>
      <td className="py-3 pr-4 align-top text-xs text-gray-600 whitespace-nowrap">{typeLabel}</td>
      <td className="py-3 pr-4 align-top text-xs text-gray-600 whitespace-nowrap">
        {dataset.format ?? '—'}
      </td>
      <td className="py-3 pr-4 align-top text-xs text-gray-600 whitespace-nowrap">
        {dataset.repository ?? '—'}
      </td>
      <td className="py-3 pr-4 align-top whitespace-nowrap">
        <div className="flex gap-1.5">
          <Badge label={dataset.access} variant={ACCESS_VARIANT[dataset.access] ?? 'neutral'} />
          <Badge
            label={dataset.classification}
            variant={CLASSIFICATION_VARIANT[dataset.classification] ?? 'neutral'}
          />
        </div>
      </td>
      <td className="py-3 align-top whitespace-nowrap">
        {dataset.url && (
          <a
            href={dataset.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-xs font-medium text-blue-600 hover:text-blue-800 hover:underline"
          >
            ↓ Download
          </a>
        )}
        {!dataset.url && dataset.doi && (
          <a
            href={`https://doi.org/${dataset.doi}`}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-blue-600 hover:underline"
          >
            DOI ↗
          </a>
        )}
        {!dataset.url && !dataset.doi && (
          <span className="text-xs text-gray-300 italic">—</span>
        )}
      </td>
    </tr>
  )
}
