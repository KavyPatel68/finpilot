import { useState, useEffect } from 'react'
import {
  CpuChipIcon,
  ServerStackIcon,
  KeyIcon,
  GlobeAltIcon,
  BoltIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
  ShieldCheckIcon,
  ArrowPathIcon,
  ClockIcon,
  SparklesIcon,
  InformationCircleIcon,
} from '@heroicons/react/24/outline'
import { getAIConfig, updateAIConfig, testAIConnection } from '../api/ai'
import type { AIConfig, AITestConnectionResponse } from '../types'

interface ProviderOption {
  id: string
  name: string
  tier: 'Offline' | 'Local' | 'Free Tier' | 'Paid Cloud'
  cost: string
  description: string
  defaultModel: string
  defaultBaseUrl: string
  requiresKey: boolean
}

const PROVIDERS: ProviderOption[] = [
  {
    id: 'none',
    name: 'Offline Rules Engine',
    tier: 'Offline',
    cost: '$0.00 (100% Free)',
    description: 'Deterministic templates & 40+ intent SQL router. No internet or API keys required.',
    defaultModel: 'rule-engine-v1',
    defaultBaseUrl: '',
    requiresKey: false,
  },
  {
    id: 'ollama',
    name: 'Ollama (Local LLM)',
    tier: 'Local',
    cost: '$0.00 (Private & Free)',
    description: 'Runs on your device (Qwen 2.5, Llama 3.1). Complete financial data privacy.',
    defaultModel: 'qwen2.5:7b',
    defaultBaseUrl: 'http://localhost:11434/v1',
    requiresKey: false,
  },
  {
    id: 'groq',
    name: 'Groq Cloud',
    tier: 'Free Tier',
    cost: '$0.00 (30 RPM Free)',
    description: 'Ultra-fast LPU cloud inference with Llama 3.3 70B on free tier.',
    defaultModel: 'llama-3.3-70b-versatile',
    defaultBaseUrl: 'https://api.groq.com/openai/v1',
    requiresKey: true,
  },
  {
    id: 'gemini',
    name: 'Google Gemini',
    tier: 'Free Tier',
    cost: '$0.00 (15 RPM Free)',
    description: 'Google AI Studio free tier using Gemini 2.5 Flash.',
    defaultModel: 'gemini-2.5-flash',
    defaultBaseUrl: 'https://generativelanguage.googleapis.com/v1beta/openai',
    requiresKey: true,
  },
  {
    id: 'anthropic',
    name: 'Anthropic Claude',
    tier: 'Paid Cloud',
    cost: 'Pay-per-token',
    description: 'Optional paid model using Claude Haiku 4.5 with prompt caching.',
    defaultModel: 'claude-haiku-4-5-20251001',
    defaultBaseUrl: '',
    requiresKey: true,
  },
]

export function SettingsPage() {
  const [config, setConfig] = useState<AIConfig | null>(null)
  const [selectedProvider, setSelectedProvider] = useState<string>('none')
  const [model, setModel] = useState<string>('')
  const [baseUrl, setBaseUrl] = useState<string>('')
  const [apiKey, setApiKey] = useState<string>('')
  const [showKey, setShowKey] = useState<boolean>(false)

  const [loading, setLoading] = useState<boolean>(true)
  const [saving, setSaving] = useState<boolean>(false)
  const [saveSuccess, setSaveSuccess] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)

  const [testResult, setTestResult] = useState<AITestConnectionResponse | null>(null)
  const [testing, setTesting] = useState<boolean>(false)

  useEffect(() => {
    loadConfig()
  }, [])

  async function loadConfig() {
    try {
      setLoading(true)
      const data = await getAIConfig()
      setConfig(data)
      setSelectedProvider(data.provider || 'none')
      setModel(data.model || '')
      setBaseUrl(data.base_url || '')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load configuration')
    } finally {
      setLoading(false)
    }
  }

  function handleProviderSelect(provId: string) {
    setSelectedProvider(provId)
    const prov = PROVIDERS.find((p) => p.id === provId)
    if (prov) {
      setModel(prov.defaultModel)
      setBaseUrl(prov.defaultBaseUrl)
    }
    setTestResult(null)
  }

  async function handleSave() {
    try {
      setSaving(true)
      setError(null)
      const updated = await updateAIConfig({
        provider: selectedProvider,
        model: model || undefined,
        base_url: baseUrl || undefined,
        api_key: apiKey || undefined,
      })
      setConfig(updated)
      setSaveSuccess(true)
      setTimeout(() => setSaveSuccess(false), 3000)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to save settings')
    } finally {
      setSaving(false)
    }
  }

  async function handleTestConnection() {
    try {
      setTesting(true)
      setTestResult(null)
      const result = await testAIConnection({
        provider: selectedProvider,
        model: model || undefined,
        base_url: baseUrl || undefined,
        api_key: apiKey || undefined,
      })
      setTestResult(result)
    } catch (e) {
      setTestResult({
        status: 'error',
        latency_ms: 0,
        provider: selectedProvider,
        message: e instanceof Error ? e.message : 'Network test error',
      })
    } finally {
      setTesting(false)
    }
  }

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <ArrowPathIcon className="h-6 w-6 animate-spin text-indigo-500" />
        <span className="ml-2 text-sm text-slate-400">Loading AI Settings...</span>
      </div>
    )
  }

  const activeProviderMeta = PROVIDERS.find((p) => p.id === selectedProvider)

  return (
    <div className="space-y-8 pb-12">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
          <CpuChipIcon className="h-6 w-6 text-indigo-400" />
          AI & Provider Settings
        </h1>
        <p className="mt-1 text-sm text-slate-400">
          Configure FinPilot's AI engine. Use local models or free cloud tiers with zero mandatory API costs.
        </p>
      </div>

      {/* Circuit Breaker Status Notice */}
      {config?.circuit_breaker_open && (
        <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-4 text-amber-200 flex items-start gap-3">
          <ExclamationCircleIcon className="h-5 w-5 text-amber-400 mt-0.5 shrink-0" />
          <div>
            <h4 className="font-semibold text-sm text-amber-300">Running in Basic Mode</h4>
            <p className="text-xs text-amber-200/90 mt-1">
              The external provider hit a rate limit (429) and the circuit breaker was activated.
              FinPilot is currently serving deterministic rules and templates. Normal connection will automatically resume in{' '}
              <span className="font-bold">{config.circuit_breaker_cooldown}s</span>.
            </p>
          </div>
        </div>
      )}

      {/* Provider Selector Cards */}
      <div className="space-y-3">
        <label className="text-xs font-semibold uppercase tracking-wider text-slate-400">
          Select LLM Provider
        </label>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {PROVIDERS.map((prov) => {
            const isSelected = selectedProvider === prov.id
            const isFree = prov.tier === 'Offline' || prov.tier === 'Local' || prov.tier === 'Free Tier'

            return (
              <button
                key={prov.id}
                type="button"
                onClick={() => handleProviderSelect(prov.id)}
                className={`flex flex-col text-left p-4 rounded-xl border transition-all ${
                  isSelected
                    ? 'border-indigo-500 bg-indigo-500/10 shadow-lg shadow-indigo-500/5 ring-1 ring-indigo-500/30'
                    : 'border-slate-800 bg-slate-900/60 hover:border-slate-700 hover:bg-slate-900'
                }`}
              >
                <div className="flex items-center justify-between w-full mb-2">
                  <span className="font-semibold text-white text-sm flex items-center gap-1.5">
                    {prov.name}
                  </span>
                  <span
                    className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${
                      prov.tier === 'Local'
                        ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                        : prov.tier === 'Free Tier'
                        ? 'bg-blue-500/20 text-blue-300 border border-blue-500/30'
                        : prov.tier === 'Offline'
                        ? 'bg-slate-500/20 text-slate-300 border border-slate-500/30'
                        : 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                    }`}
                  >
                    {prov.tier}
                  </span>
                </div>
                <p className="text-xs text-slate-400 flex-1 leading-relaxed mb-3">
                  {prov.description}
                </p>
                <div className="flex items-center justify-between text-[11px] pt-2 border-t border-slate-800 text-slate-400">
                  <span>Cost:</span>
                  <span className={isFree ? 'font-semibold text-emerald-400' : 'text-slate-300'}>
                    {prov.cost}
                  </span>
                </div>
              </button>
            )
          })}
        </div>
      </div>

      {/* Provider Details & Config Form */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/80 p-6 space-y-6">
        <div className="flex items-center justify-between pb-4 border-b border-slate-800">
          <div>
            <h3 className="text-base font-semibold text-white flex items-center gap-2">
              <ServerStackIcon className="h-4 w-4 text-indigo-400" />
              Configure {activeProviderMeta?.name}
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Set model target, base endpoint, and optional credentials.
            </p>
          </div>
          {config?.provider === selectedProvider && (
            <span className="inline-flex items-center gap-1 text-xs text-indigo-400 bg-indigo-500/10 px-2.5 py-1 rounded-full border border-indigo-500/20">
              <CheckCircleIcon className="h-3.5 w-3.5" />
              Active Provider
            </span>
          )}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {/* Model Name */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-slate-300 flex items-center gap-1.5">
              <SparklesIcon className="h-3.5 w-3.5 text-slate-400" />
              Model Name
            </label>
            <input
              type="text"
              value={model}
              onChange={(e) => setModel(e.target.value)}
              disabled={selectedProvider === 'none'}
              placeholder={activeProviderMeta?.defaultModel}
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3.5 py-2 text-sm text-white placeholder-slate-500 focus:border-indigo-500 focus:outline-none disabled:opacity-50"
            />
            <p className="text-[11px] text-slate-500">
              {selectedProvider === 'none'
                ? 'Offline rule engine handles calculations without an LLM model.'
                : 'Enter the model identifier used by the provider.'}
            </p>
          </div>

          {/* Base URL */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-slate-300 flex items-center gap-1.5">
              <GlobeAltIcon className="h-3.5 w-3.5 text-slate-400" />
              Base URL / Host
            </label>
            <input
              type="text"
              value={baseUrl}
              onChange={(e) => setBaseUrl(e.target.value)}
              disabled={selectedProvider === 'none' || selectedProvider === 'anthropic'}
              placeholder={activeProviderMeta?.defaultBaseUrl || 'Default SDK endpoint'}
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3.5 py-2 text-sm text-white placeholder-slate-500 focus:border-indigo-500 focus:outline-none disabled:opacity-50"
            />
            <p className="text-[11px] text-slate-500">
              OpenAI-compatible chat completion endpoint.
            </p>
          </div>

          {/* API Key */}
          {activeProviderMeta?.requiresKey && (
            <div className="space-y-1.5 md:col-span-2">
              <label className="text-xs font-medium text-slate-300 flex items-center justify-between">
                <span className="flex items-center gap-1.5">
                  <KeyIcon className="h-3.5 w-3.5 text-slate-400" />
                  API Key
                </span>
                <button
                  type="button"
                  onClick={() => setShowKey(!showKey)}
                  className="text-[11px] text-indigo-400 hover:underline"
                >
                  {showKey ? 'Hide Key' : 'Show Key'}
                </button>
              </label>
              <input
                type={showKey ? 'text' : 'password'}
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder={config?.is_key_set ? '•••••••••••••••• (Key Configured)' : 'Enter API Key...'}
                className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3.5 py-2 text-sm text-white placeholder-slate-500 focus:border-indigo-500 focus:outline-none"
              />
              <p className="text-[11px] text-slate-500 flex items-center gap-1">
                <ShieldCheckIcon className="h-3.5 w-3.5 text-emerald-400 inline" />
                Keys are kept in secure memory and never written to raw logs.
              </p>
            </div>
          )}
        </div>

        {/* Action Buttons */}
        <div className="flex flex-wrap items-center justify-between gap-3 pt-4 border-t border-slate-800">
          <button
            type="button"
            onClick={handleTestConnection}
            disabled={testing}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-slate-700 bg-slate-800 text-xs font-medium text-slate-200 hover:bg-slate-750 transition-colors disabled:opacity-50"
          >
            {testing ? (
              <ArrowPathIcon className="h-3.5 w-3.5 animate-spin text-indigo-400" />
            ) : (
              <BoltIcon className="h-3.5 w-3.5 text-indigo-400" />
            )}
            Test Connection
          </button>

          <div className="flex items-center gap-3">
            {saveSuccess && (
              <span className="text-xs text-emerald-400 flex items-center gap-1">
                <CheckCircleIcon className="h-3.5 w-3.5" />
                Settings updated successfully
              </span>
            )}
            {error && <span className="text-xs text-rose-400">{error}</span>}
            <button
              type="button"
              onClick={handleSave}
              disabled={saving}
              className="inline-flex items-center gap-2 px-5 py-2 rounded-lg bg-indigo-600 text-xs font-semibold text-white hover:bg-indigo-500 transition-colors disabled:opacity-50 shadow-md shadow-indigo-600/20"
            >
              {saving ? <ArrowPathIcon className="h-3.5 w-3.5 animate-spin" /> : null}
              Save Configuration
            </button>
          </div>
        </div>

        {/* Test Result Display */}
        {testResult && (
          <div
            className={`rounded-lg p-3.5 text-xs flex items-start gap-2.5 border ${
              testResult.status === 'ok'
                ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300'
                : 'border-rose-500/30 bg-rose-500/10 text-rose-300'
            }`}
          >
            {testResult.status === 'ok' ? (
              <CheckCircleIcon className="h-4 w-4 text-emerald-400 mt-0.5 shrink-0" />
            ) : (
              <ExclamationCircleIcon className="h-4 w-4 text-rose-400 mt-0.5 shrink-0" />
            )}
            <div className="flex-1">
              <div className="flex items-center justify-between">
                <span className="font-semibold">
                  {testResult.status === 'ok' ? 'Connection Succeeded' : 'Connection Failed'}
                </span>
                {testResult.latency_ms > 0 && (
                  <span className="text-[11px] text-slate-400 flex items-center gap-1">
                    <ClockIcon className="h-3 w-3" />
                    {testResult.latency_ms} ms
                  </span>
                )}
              </div>
              <p className="mt-1 text-slate-300">{testResult.message}</p>
            </div>
          </div>
        )}
      </div>

      {/* Privacy & Zero-Token Architecture Highlights */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-5 space-y-3">
        <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
          <InformationCircleIcon className="h-4 w-4 text-indigo-400" />
          Free-to-Run Architecture
        </h4>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs text-slate-300">
          <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
            <span className="font-semibold text-white block mb-1">Layer 1: 40+ Intent Router</span>
            Evaluates requests locally via direct SQL templates with zero tokens and zero external API calls.
          </div>
          <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
            <span className="font-semibold text-white block mb-1">Layer 2: Privacy Anonymizer</span>
            Strips PAN, IFSC, account numbers, and PII before any query leaves your machine.
          </div>
          <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
            <span className="font-semibold text-white block mb-1">Layer 3: Circuit Breaker</span>
            If any free provider returns a 429 rate limit, FinPilot gracefully switches to basic mode for 60s.
          </div>
        </div>
      </div>

      {/* Regulatory Notice */}
      <div className="text-center text-[11px] text-slate-500 pt-4">
        SEBI Non-Advisor Notice: FinPilot is a personal finance decision-support tool. It does not provide investment advice or stock recommendations.
      </div>
    </div>
  )
}
