import { apiFetch } from './client'
import type { Insight, Severity } from '../types'

export async function getInsights(
  params: { month?: string; type?: string; severity?: Severity; user_id?: number } = {}
): Promise<Insight[]> {
  const query = new URLSearchParams()
  query.set('user_id', String(params.user_id ?? 1))
  if (params.month) query.set('month', params.month)
  if (params.type) query.set('type', params.type)
  if (params.severity) query.set('severity', params.severity)

  return apiFetch<Insight[]>(`/api/insights?${query.toString()}`)
}

export async function triggerAnomalyDetection(userId: number = 1): Promise<Insight[]> {
  return apiFetch<Insight[]>(`/api/insights/detect?user_id=${userId}`, {
    method: 'POST',
  })
}
