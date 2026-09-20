import { apiFetch } from './client'
import type { Goal, GoalSimulationResponse } from '../types'

export async function getGoals(
  isActive?: boolean,
  userId: number = 1
): Promise<Goal[]> {
  const q = isActive !== undefined ? `&is_active=${isActive}` : ''
  return apiFetch<Goal[]>(`/api/goals?user_id=${userId}${q}`)
}

export async function createGoal(
  data: {
    name: string
    type?: string
    target_amount_minor: number
    current_amount_minor?: number
    target_date?: string
    monthly_contribution_planned_minor?: number
  },
  userId: number = 1
): Promise<Goal> {
  return apiFetch<Goal>(`/api/goals?user_id=${userId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}

export async function updateGoal(
  id: number,
  data: {
    name?: string
    type?: string
    target_amount_minor?: number
    current_amount_minor?: number
    target_date?: string
    monthly_contribution_planned_minor?: number
    is_active?: boolean
  },
  userId: number = 1
): Promise<Goal> {
  return apiFetch<Goal>(`/api/goals/${id}?user_id=${userId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}

export async function deleteGoal(
  id: number,
  userId: number = 1
): Promise<{ status: string }> {
  return apiFetch<{ status: string }>(`/api/goals/${id}?user_id=${userId}`, {
    method: 'DELETE',
  })
}

export async function simulateGoal(
  data: {
    goal_id: number
    cut_category: string
    cut_amount_minor: number
  },
  userId: number = 1
): Promise<GoalSimulationResponse> {
  return apiFetch<GoalSimulationResponse>(`/api/goals/simulate?user_id=${userId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}
