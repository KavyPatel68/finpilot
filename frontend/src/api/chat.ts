import { apiFetch } from './client'
import type { ChatMessage } from '../types'

export interface SendMessageResponse {
  reply: string
  tool_calls?: Array<{ tool: string; arguments: Record<string, unknown> }>
  tool_results?: Array<Record<string, unknown>>
  message_id?: number
  calculation_metadata?: import('../types').CalculationMetadata
}


export async function sendMessage(
  message: string,
  userId: number = 1
): Promise<SendMessageResponse> {
  return apiFetch<SendMessageResponse>(`/api/chat?user_id=${userId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, user_id: userId }),
  })
}

export async function getChatHistory(userId: number = 1): Promise<ChatMessage[]> {
  return apiFetch<ChatMessage[]>(`/api/chat/history?user_id=${userId}`)
}

export async function clearChatHistory(userId: number = 1): Promise<{ status: string }> {
  return apiFetch<{ status: string }>(`/api/chat/history?user_id=${userId}`, {
    method: 'DELETE',
  })
}
