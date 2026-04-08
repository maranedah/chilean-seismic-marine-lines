'use client'

import { useState } from 'react'
import { MapContainer, TileLayer, CircleMarker, Tooltip, Polyline } from 'react-leaflet'
import type { PaperSummary } from '@/types/paper'

function markerColor(paper: PaperSummary): string {
  if (paper.has_open_data) return '#22c55e'
  if (paper.paper_url) return '#3b82f6'
  return '#9ca3af'
}

function FigurePreview({ src }: { src: string }) {
  const [failed, setFailed] = useState(false)
  if (failed) return null
  return (
    <img
      src={src}
      alt=""
      onError={() => setFailed(true)}
      style={{ width: 96, height: 90, objectFit: 'cover', borderRadius: 4, display: 'block', flexShrink: 0 }}
    />
  )
}

function PaperTooltip({ paper }: { paper: PaperSummary }) {
  // Use API-provided paths if available, otherwise try sequential filenames
  const candidates = paper.preview_figures?.length
    ? paper.preview_figures.slice(0, 3)
    : [1, 2, 3].map((n) => `/images/${paper.id}/fig_${String(n).padStart(3, '0')}.png`)

  return (
    <div className="paper-tooltip-inner">
      <div style={{ display: 'flex', gap: 4, marginBottom: 8 }}>
        {candidates.map((src) => (
          <FigurePreview key={src} src={src} />
        ))}
      </div>
      <p style={{ fontWeight: 600, marginBottom: 3, lineHeight: 1.3, fontSize: 13 }}>
        {paper.title.length > 80 ? paper.title.slice(0, 80) + '…' : paper.title}
      </p>
      <p style={{ color: '#555', fontSize: 12, marginBottom: 2 }}>
        {paper.authors_short} · {paper.year}
      </p>
      <p style={{ color: '#666', fontSize: 11 }}>
        {paper.city} · {paper.latitude?.toFixed(2)}°, {paper.longitude?.toFixed(2)}°
      </p>
      <p style={{ fontSize: 11, color: '#777', marginTop: 4 }}>
        Click to open paper details →
      </p>
    </div>
  )
}

interface Props {
  papers: PaperSummary[]
  showLines?: boolean
}

export default function SurveyMap({ papers, showLines = false }: Props) {
  const mapped = papers.filter((p) => p.latitude !== null && p.longitude !== null)

  return (
    <MapContainer
      center={[-35, -72]}
      zoom={4}
      style={{ height: '100%', width: '100%' }}
      scrollWheelZoom
    >
      <TileLayer
        url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>'
      />

      {mapped.map((paper) => {
        const color = markerColor(paper)
        return (
          <CircleMarker
            key={paper.id}
            center={[paper.latitude!, paper.longitude!]}
            radius={8}
            pathOptions={{ color: '#fff', weight: 1.5, fillColor: color, fillOpacity: 0.85 }}
            eventHandlers={{
              click: () => window.open(`/papers/${paper.id}`, '_blank'),
              mouseover: (e) => e.target.setStyle({ radius: 11, weight: 2 }),
              mouseout: (e) => e.target.setStyle({ radius: 8, weight: 1.5 }),
            }}
          >
            <Tooltip direction="top" offset={[0, -6]} className="paper-tooltip">
              <PaperTooltip paper={paper} />
            </Tooltip>
          </CircleMarker>
        )
      })}

      {showLines &&
        mapped.flatMap((paper) =>
          paper.seismic_lines
            .filter(
              (l) =>
                l.lat_start != null &&
                l.lon_start != null &&
                l.lat_end != null &&
                l.lon_end != null,
            )
            .map((line, i) => (
              <Polyline
                key={`${paper.id}-line-${i}`}
                positions={[
                  [line.lat_start!, line.lon_start!],
                  [line.lat_end!, line.lon_end!],
                ]}
                pathOptions={{ color: markerColor(paper), weight: 2, opacity: 0.55 }}
              />
            )),
        )}
    </MapContainer>
  )
}
