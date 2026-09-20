import { apiFetch } from './client'
import type { RecurringGroup, RecurringStatus } from '../types'

export async function getSubscriptions(
  status?: RecurringStatus,
  userId: number = 1
): Promise<RecurringGroup[]> {
  const q = status ? `&status=${status}` : ''
  return apiFetch<RecurringGroup[]>(`/api/subscriptions?user_id=${userId}${q}`)
}

export async function triggerRecurringDetection(
  userId: number = 1
): Promise<{ groups_count: number; price_hikes: unknown[]; message: string }> {
  return apiFetch<{ groups_count: number; price_hikes: unknown[]; message: string }>(
    `/api/subscriptions/detect?user_id=${userId}`,
    { method: 'POST' }
  )
}

export async function updateSubscriptionStatus(
  groupId: number,
  status: RecurringStatus,
  userId: number = 1
): Promise<RecurringGroup> {
  return apiFetch<RecurringGroup>(
    `/api/subscriptions/${groupId}/status?status=${status}&user_id=${userId}`,
    { method: 'PATCH' }
  )
}

export async function getUpcomingObligations(
  days: number = 30,
  userId: number = 1
): Promise<import('../types').UpcomingObligationsResponse> {
  return apiFetch<import('../types').UpcomingObligationsResponse>(
    `/api/subscriptions/upcoming?days=${days}&user_id=${userId}`
  )
}

export async function getPriceHikes(
  userId: number = 1
): Promise<import('../types').PriceHikeItem[]> {
  return apiFetch<import('../types').PriceHikeItem[]>(
    `/api/subscriptions/hikes?user_id=${userId}`
  )
}

