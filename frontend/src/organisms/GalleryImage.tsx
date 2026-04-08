'use client'

import { useState } from 'react'
import type { FigureEntry } from '@/types/paper'

interface Props {
  figure: FigureEntry
  paperId: string
}

export default function GalleryImage({ figure, paperId }: Props) {
  const [expanded, setExpanded] = useState(false)
  const src = `/images/${paperId}/${figure.filename}`

  return (
    <>
      <div
        className="group cursor-zoom-in rounded-lg overflow-hidden border border-gray-100 bg-gray-50 hover:border-blue-300 hover:shadow-md transition-all"
        onClick={() => setExpanded(true)}
      >
        <img
          src={src}
          alt={figure.figure_label ?? figure.filename}
          className="w-full object-cover"
          style={{ height: 160 }}
        />
        {(figure.figure_label || figure.type) && (
          <div className="px-2.5 py-2 border-t border-gray-100">
            <div className="flex items-center justify-between gap-2">
              {figure.figure_label && (
                <span className="text-xs font-medium text-gray-700 truncate">
                  {figure.figure_label}
                </span>
              )}
              {figure.type && (
                <span className="text-xs text-gray-400 shrink-0 capitalize">{figure.type.replace('_', ' ')}</span>
              )}
            </div>
            {figure.description && (
              <p className="text-xs text-gray-500 mt-1 line-clamp-2">{figure.description}</p>
            )}
          </div>
        )}
      </div>

      {expanded && (
        <div
          className="fixed inset-0 z-[9999] bg-black/80 flex items-center justify-center p-4"
          onClick={() => setExpanded(false)}
        >
          <div
            className="bg-white rounded-xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between px-5 py-3 border-b border-gray-100">
              <span className="font-semibold text-gray-800 text-sm">
                {figure.figure_label ?? figure.filename}
              </span>
              <button
                onClick={() => setExpanded(false)}
                className="text-gray-400 hover:text-gray-700 text-lg leading-none"
              >
                ✕
              </button>
            </div>
            <img src={src} alt={figure.figure_label ?? ''} className="w-full" />
            {figure.caption && (
              <div className="px-5 py-4 border-t border-gray-100">
                <p className="text-xs text-gray-600 leading-relaxed">{figure.caption}</p>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  )
}
