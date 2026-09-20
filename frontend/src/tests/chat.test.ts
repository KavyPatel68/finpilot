import { describe, it, expect } from 'vitest'
import type { ChatMessage, CalculationMetadata } from '../types'

describe('Chat assistant and calculation telemetry contracts', () => {
  it('validates ChatMessage with calculation metadata', () => {
    const mockMeta: CalculationMetadata = {
      intent: 'category_spend',
      confidence: 0.98,
      is_zero_token: true,
      is_cached: false,
      model: 'Zero-Token Intent Engine',
    }

    const mockMsg: ChatMessage = {
      id: 1,
      role: 'assistant',
      content: 'You spent ₹6,500.00 on dining in August 2024 across 4 transactions.',
      tool_calls: [{ tool: 'search_transactions', arguments: { category: 'Dining', month: '2024-08' } }],
      tool_results: [{ total_minor: 650000, count: 4 }],
      calculation_metadata: mockMeta,
      created_at: '2024-09-20T10:00:00Z',
    }

    expect(mockMsg.role).toBe('assistant')
    expect(mockMsg.calculation_metadata?.is_zero_token).toBe(true)
    expect(mockMsg.calculation_metadata?.confidence).toBeGreaterThan(0.9)
    expect(mockMsg.tool_calls).toHaveLength(1)
  })

  it('validates cached message structure', () => {
    const cachedMeta: CalculationMetadata = {
      intent: 'subscriptions',
      confidence: 1.0,
      is_zero_token: true,
      is_cached: true,
      model: 'SQLite Cache',
    }

    expect(cachedMeta.is_cached).toBe(true)
    expect(cachedMeta.is_zero_token).toBe(true)
  })
})
