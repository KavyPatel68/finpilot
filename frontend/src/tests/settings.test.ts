import { describe, it, expect } from 'vitest'
import type { AIConfig, AIUsageStats, AITestConnectionResponse } from '../types'

describe('Settings & Provider-Agnostic AI Layer', () => {
  it('validates AIConfig structure for offline NoneProvider', () => {
    const config: AIConfig = {
      provider: 'none',
      provider_tier: 'Offline',
      model: 'rule-engine-v1',
      base_url: '',
      is_key_set: true,
      circuit_breaker_open: false,
      circuit_breaker_cooldown: 0,
      is_free: true,
    }

    expect(config.provider).toBe('none')
    expect(config.is_free).toBe(true)
    expect(config.circuit_breaker_open).toBe(false)
  })

  it('validates AIConfig structure for Ollama Local Provider', () => {
    const config: AIConfig = {
      provider: 'ollama',
      provider_tier: 'Local',
      model: 'qwen2.5:7b',
      base_url: 'http://localhost:11434/v1',
      is_key_set: true,
      circuit_breaker_open: false,
      circuit_breaker_cooldown: 0,
      is_free: true,
    }

    expect(config.provider).toBe('ollama')
    expect(config.provider_tier).toBe('Local')
    expect(config.is_free).toBe(true)
  })

  it('validates AIUsageStats displays $0.00 for free tier and local providers', () => {
    const freeUsage: AIUsageStats = {
      tokens_used_today: 1540,
      input_tokens_today: 1000,
      output_tokens_today: 540,
      cached_read_tokens_today: 400,
      tokens_saved_by_cache: 650,
      cache_hit_rate_pct: 62.5,
      estimated_cost_inr: 0.0,
      estimated_cost_usd: 0.0,
      is_free: true,
      provider: 'groq',
      provider_tier: 'Free Tier',
      circuit_breaker_open: false,
      circuit_breaker_cooldown: 0,
      is_estimated: true,
      currency_symbol: '₹',
      total_requests: 12,
      llm_mode: 'cheap',
      model_fast: 'llama-3.3-70b-versatile',
      model_smart: 'llama-3.3-70b-versatile',
    }

    expect(freeUsage.is_free).toBe(true)
    expect(freeUsage.estimated_cost_inr).toBe(0.0)
    expect(freeUsage.estimated_cost_usd).toBe(0.0)
    expect(freeUsage.provider_tier).toBe('Free Tier')
  })

  it('validates circuit breaker trip state handling', () => {
    const trippedUsage: AIUsageStats = {
      tokens_used_today: 200,
      input_tokens_today: 150,
      output_tokens_today: 50,
      cached_read_tokens_today: 0,
      tokens_saved_by_cache: 0,
      cache_hit_rate_pct: 0,
      estimated_cost_inr: 0.0,
      estimated_cost_usd: 0.0,
      is_free: true,
      provider: 'groq',
      provider_tier: 'Free Tier',
      circuit_breaker_open: true,
      circuit_breaker_cooldown: 45,
      is_estimated: true,
      currency_symbol: '₹',
      total_requests: 3,
      llm_mode: 'cheap',
      model_fast: 'circuit-breaker',
      model_smart: 'circuit-breaker',
    }

    expect(trippedUsage.circuit_breaker_open).toBe(true)
    expect(trippedUsage.circuit_breaker_cooldown).toBe(45)
  })

  it('validates connection test response payload', () => {
    const testResult: AITestConnectionResponse = {
      status: 'ok',
      latency_ms: 24,
      provider: 'none',
      message: 'Deterministic offline engine ready (0ms latency, zero tokens).',
    }

    expect(testResult.status).toBe('ok')
    expect(testResult.latency_ms).toBeLessThan(100)
    expect(testResult.provider).toBe('none')
  })
})
