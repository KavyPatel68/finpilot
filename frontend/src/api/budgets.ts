import { apiFetch } from './client'
import type { Budget } from '../types'

export async function getBudgets(
  month?: string,
  userId: number = 1
): Promise<Budget[]> {
  const q = month ? `&month=${month}` : ''
  return apiFetch<Budget[]>(`/api/budgets?user_id=${userId}${q}`)
}

export async function createBudget(
  data: { category: string; monthly_limit_minor: number; effective_from?: string },
  userId: number = 1
): Promise<Budget> {
  return apiFetch<Budget>(`/api/budgets?user_id=${userId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}

export async function updateBudget(
  id: number,
  data: { monthly_limit_minor?: number; effective_from?: string; effective_to?: string },
  userId: number = 1
): Promise<Budget> {
  return apiFetch<Budget>(`/api/budgets/${id}?user_id=${userId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}

export async function deleteBudget(
  id: number,
  userId: number = 1
): Promise<{ status: string }> {
  return apiFetch<{ status: string }>(`/api/budgets/${id}?user_id=${userId}`, {
    method: 'DELETE',
  })
}
