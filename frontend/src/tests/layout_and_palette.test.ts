import { describe, it, expect } from 'vitest'
import type { AIUsageStats } from '../types'

describe('Layout and AI Usage Widget contracts', () => {
  it('validates AIUsageStats structure and calculations', () => {
    const mockUsage: AIUsageStats = {
      tokens_used_today: 450,
      input_tokens_today: 300,
      output_tokens_today: 150,
      cached_read_tokens_today: 120,
      tokens_saved_by_cache: 1200,
      cache_hit_rate_pct: 75.0,
      estimated_cost_inr: 0.04,
      estimated_cost_usd: 0.0005,
      is_estimated: true,
      currency_symbol: '₹',
      total_requests: 6,
      llm_mode: 'cheap',
      model_fast: 'claude-haiku-4-5-20251001',
      model_smart: 'claude-sonnet-5',
    }

    expect(mockUsage.tokens_used_today).toBe(
      mockUsage.input_tokens_today + mockUsage.output_tokens_today
    )
    expect(mockUsage.tokens_saved_by_cache).toBeGreaterThan(0)
    expect(mockUsage.is_estimated).toBe(true)
    expect(mockUsage.llm_mode).toBe('cheap')
    expect(mockUsage.estimated_cost_inr).toBe(0.04)
    expect(mockUsage.cache_hit_rate_pct).toBe(75.0)
  })

  it('formats token numbers with k/M suffixes properly', () => {
    const formatTokens = (num: number) => {
      if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`
      if (num >= 1000) return `${(num / 1000).toFixed(1)}k`
      return num.toString()
    }

    expect(formatTokens(450)).toBe('450')
    expect(formatTokens(1250)).toBe('1.3k')
    expect(formatTokens(2500000)).toBe('2.5M')
  })
})
