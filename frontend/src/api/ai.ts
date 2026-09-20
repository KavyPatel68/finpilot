import { apiFetch } from './client'
import type {
  AIUsageStats,
  AIModeResponse,
  AIConfig,
  AIConfigUpdateRequest,
  AITestConnectionResponse,
} from '../types'

export async function getAIUsage(userId: number = 1): Promise<AIUsageStats> {
  return apiFetch<AIUsageStats>(`/api/ai/usage?user_id=${userId}`)
}

export async function setAIMode(
  mode: 'off' | 'cheap' | 'full'
): Promise<AIModeResponse> {
  return apiFetch<AIModeResponse>('/api/ai/mode', {
    method: 'POST',
    body: JSON.stringify({ mode }),
  })
}

export async function getAIConfig(): Promise<AIConfig> {
  return apiFetch<AIConfig>('/api/ai/config')
}

export async function updateAIConfig(
  payload: AIConfigUpdateRequest
): Promise<AIConfig> {
  return apiFetch<AIConfig>('/api/ai/config', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function testAIConnection(
  payload?: Partial<AIConfigUpdateRequest>
): Promise<AITestConnectionResponse> {
  return apiFetch<AITestConnectionResponse>('/api/ai/test-connection', {
    method: 'POST',
    body: JSON.stringify(payload || {}),
  })
}

export async function clearAICache(
  userId: number = 1
): Promise<{ status: string; cleared_entries: number }> {
  return apiFetch<{ status: string; cleared_entries: number }>(
    `/api/ai/cache?user_id=${userId}`,
    {
      method: 'DELETE',
    }
  )
}
