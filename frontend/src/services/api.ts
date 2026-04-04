import type { Paper, PaperSummary, Stats } from '../types/paper'

const BASE = '/api'

async function request<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText)
    throw new Error(`API ${res.status}: ${text}`)
  }
  return res.json() as Promise<T>
}

export function fetchPapers(): Promise<PaperSummary[]> {
  return request<PaperSummary[]>('/papers')
}

export function fetchPaper(id: string): Promise<Paper> {
  return request<Paper>(`/papers/${encodeURIComponent(id)}`)
}

export function fetchStats(): Promise<Stats> {
  return request<Stats>('/stats')
}
