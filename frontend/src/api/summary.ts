import { apiFetch } from './client'
import type { MonthlySummary } from '../types'

export async function getMonthlySummary(
  month?: string,
  userId: number = 1
): Promise<MonthlySummary> {
  const q = month ? `&month=${month}` : ''
  return apiFetch<MonthlySummary>(`/api/summary?user_id=${userId}${q}`)
}

export async function getAvailableMonths(userId: number = 1): Promise<string[]> {
  return apiFetch<string[]>(`/api/summary/months?user_id=${userId}`)
}

export async function regenerateSummary(
  month: string,
  userId: number = 1
): Promise<MonthlySummary> {
  return apiFetch<MonthlySummary>(`/api/summary/${month}/generate?user_id=${userId}`, {
    method: 'POST',
  })
}

export async function getSpendingTrends(
  months: number = 6,
  userId: number = 1
): Promise<import('../types').SpendingTrendItem[]> {
  return apiFetch<import('../types').SpendingTrendItem[]>(
    `/api/summary/trends?months=${months}&user_id=${userId}`
  )
}

