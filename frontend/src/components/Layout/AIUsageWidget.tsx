import React, { useState, useEffect, useRef } from 'react'
import {
  SparklesIcon,
  BoltIcon,
  CpuChipIcon,
  NoSymbolIcon,
  ArrowPathIcon,
  TrashIcon,
  XMarkIcon,
  InformationCircleIcon,
} from '@heroicons/react/24/outline'
import { getAIUsage, setAIMode, clearAICache } from '../../api/ai'
import type { AIUsageStats } from '../../types'

export function AIUsageWidget() {
  const [stats, setStats] = useState<AIUsageStats | null>(null)
  const [isOpen, setIsOpen] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [isUpdatingMode, setIsUpdatingMode] = useState(false)
  const [actionMessage, setActionMessage] = useState<string | null>(null)
  const popoverRef = useRef<HTMLDivElement>(null)

  const fetchStats = async () => {
    try {
      const data = await getAIUsage()
      setStats(data)
    } catch (err) {
      console.error('Failed to fetch AI usage stats:', err)
    }
  }

  useEffect(() => {
    fetchStats()
    const interval = setInterval(fetchStats, 20000)
    return () => clearInterval(interval)
  }, [])

  // Close popover when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (popoverRef.current && !popoverRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
    }
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [isOpen])

  const handleModeChange = async (mode: 'off' | 'cheap' | 'full') => {
    setIsUpdatingMode(true)
    setActionMessage(null)
    try {
      const res = await setAIMode(mode)
      setActionMessage(`Mode set to ${mode.toUpperCase()}: ${res.description}`)
      await fetchStats()
    } catch (err) {
      setActionMessage('Failed to update mode')
    } finally {
      setIsUpdatingMode(false)
    }
  }

  const handleClearCache = async () => {
    setIsLoading(true)
    setActionMessage(null)
    try {
      const res = await clearAICache()
      setActionMessage(`AI Cache cleared (${res.cleared_entries} entries purged)`)
      await fetchStats()
    } catch (err) {
      setActionMessage('Failed to clear cache')
    } finally {
      setIsLoading(false)
    }
  }

  const currentMode = (stats?.llm_mode || 'cheap').toLowerCase()
  const tokensUsed = stats?.tokens_used_today ?? 0
  const tokensSaved = stats?.tokens_saved_by_cache ?? 0
  const costInr = stats?.estimated_cost_inr ?? 0
  const hitRate = stats?.cache_hit_rate_pct ?? 0

  const formatTokens = (num: number) => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`
    if (num >= 1000) return `${(num / 1000).toFixed(1)}k`
    return num.toString()
  }

  const isFree = stats?.is_free ?? true
  const providerTier = stats?.provider_tier || 'Offline'
  const isCircuitBreakerOpen = stats?.circuit_breaker_open ?? false

  return (
    <div className="relative" ref={popoverRef}>
      {/* TopBar Trigger Pill */}
      <button
        onClick={() => {
          setIsOpen(!isOpen)
          if (!isOpen) fetchStats()
        }}
        className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg border text-xs font-medium transition-all shadow-sm
          bg-white hover:bg-slate-50 border-slate-200 text-slate-700
          dark:bg-slate-800 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-750"
        title="Click to view AI token consumption & toggle mode"
      >
        {/* Provider Tier Badge */}
        <span
          className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
            providerTier === 'Local'
              ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/60 dark:text-emerald-300'
              : providerTier === 'Free Tier'
              ? 'bg-blue-100 text-blue-800 dark:bg-blue-900/60 dark:text-blue-300'
              : providerTier === 'Offline'
              ? 'bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300'
              : 'bg-purple-100 text-purple-700 dark:bg-purple-900/60 dark:text-purple-300'
          }`}
        >
          {providerTier === 'Offline' ? (
            <NoSymbolIcon className="w-3 h-3" />
          ) : providerTier === 'Local' ? (
            <CpuChipIcon className="w-3 h-3" />
          ) : (
            <BoltIcon className="w-3 h-3" />
          )}
          {providerTier}
        </span>

        {/* Tokens & Cost */}
        <span className="font-mono text-slate-600 dark:text-slate-300">
          {formatTokens(tokensUsed)} tok
        </span>

        {tokensSaved > 0 && (
          <span className="hidden sm:inline-flex items-center text-[10px] font-medium text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/50 px-1.5 py-0.5 rounded">
            +{formatTokens(tokensSaved)} saved
          </span>
        )}

        <span className="hidden md:inline font-mono font-semibold text-slate-900 dark:text-white">
          {isFree ? (
            <span className="text-emerald-600 dark:text-emerald-400 font-semibold">$0.00</span>
          ) : (
            <>
              ₹{costInr.toFixed(2)}
              <span className="text-[9px] font-normal text-slate-400 ml-0.5">est</span>
            </>
          )}
        </span>
      </button>

      {/* Popover Card */}
      {isOpen && (
        <div className="absolute right-0 mt-2 w-80 sm:w-96 rounded-2xl shadow-2xl border z-50 p-4 transition-all duration-200 animate-in fade-in slide-in-from-top-2
          bg-white border-slate-200 text-slate-800
          dark:bg-slate-900 dark:border-slate-750 dark:text-slate-100">
          {/* Header */}
          <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-lg bg-indigo-50 dark:bg-indigo-950/70 flex items-center justify-center text-indigo-600 dark:text-indigo-400">
                <SparklesIcon className="w-4 h-4" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-slate-900 dark:text-white leading-none">
                  AI Usage & Token Meter
                </h3>
                <p className="text-[11px] text-slate-400 mt-0.5">Real-time token cost & cache efficiency</p>
              </div>
            </div>
            <button
              onClick={() => setIsOpen(false)}
              className="p-1 rounded-md text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800"
            >
              <XMarkIcon className="w-4 h-4" />
            </button>
          </div>

          {/* Mode Selector */}
          <div className="mt-3">
            <label className="text-[11px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider block mb-1.5">
              Execution Engine Mode
            </label>
            <div className="grid grid-cols-3 gap-1.5 p-1 bg-slate-100 dark:bg-slate-800/80 rounded-xl">
              <button
                disabled={isUpdatingMode}
                onClick={() => handleModeChange('off')}
                className={`flex flex-col items-center py-1.5 px-2 rounded-lg text-xs font-medium transition-all ${
                  currentMode === 'off'
                    ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm font-semibold'
                    : 'text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200'
                }`}
              >
                <span>OFF</span>
                <span className="text-[9px] text-slate-400">Zero tokens</span>
              </button>

              <button
                disabled={isUpdatingMode}
                onClick={() => handleModeChange('cheap')}
                className={`flex flex-col items-center py-1.5 px-2 rounded-lg text-xs font-medium transition-all ${
                  currentMode === 'cheap'
                    ? 'bg-white dark:bg-slate-700 text-emerald-700 dark:text-emerald-300 shadow-sm font-semibold'
                    : 'text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200'
                }`}
              >
                <span>CHEAP</span>
                <span className="text-[9px] text-slate-400">Haiku + Cache</span>
              </button>

              <button
                disabled={isUpdatingMode}
                onClick={() => handleModeChange('full')}
                className={`flex flex-col items-center py-1.5 px-2 rounded-lg text-xs font-medium transition-all ${
                  currentMode === 'full'
                    ? 'bg-white dark:bg-slate-700 text-purple-700 dark:text-purple-300 shadow-sm font-semibold'
                    : 'text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200'
                }`}
              >
                <span>FULL</span>
                <span className="text-[9px] text-slate-400">Smart models</span>
              </button>
            </div>
          </div>

          {/* Metric Stats Grid */}
          <div className="grid grid-cols-2 gap-2 mt-3 text-xs">
            <div className="p-2.5 rounded-xl bg-slate-50 dark:bg-slate-800/50 border border-slate-100 dark:border-slate-800">
              <span className="text-[10px] text-slate-400 uppercase font-semibold block">Tokens Used Today</span>
              <div className="text-base font-bold font-mono text-slate-900 dark:text-white mt-0.5">
                {tokensUsed.toLocaleString()}
              </div>
              <span className="text-[10px] text-slate-400 mt-0.5 block">
                {stats?.input_tokens_today ?? 0} in / {stats?.output_tokens_today ?? 0} out
              </span>
            </div>

            <div className="p-2.5 rounded-xl bg-emerald-50/60 dark:bg-emerald-950/30 border border-emerald-100 dark:border-emerald-900/40">
              <span className="text-[10px] text-emerald-700 dark:text-emerald-400 uppercase font-semibold block">
                Tokens Saved by Cache
              </span>
              <div className="text-base font-bold font-mono text-emerald-700 dark:text-emerald-400 mt-0.5">
                +{tokensSaved.toLocaleString()}
              </div>
              <span className="text-[10px] text-emerald-600/80 dark:text-emerald-400/80 mt-0.5 block">
                {hitRate}% cache hit rate
              </span>
            </div>

            <div className="p-2.5 rounded-xl bg-slate-50 dark:bg-slate-800/50 border border-slate-100 dark:border-slate-800">
              <span className="text-[10px] text-slate-400 uppercase font-semibold block">Estimated Cost</span>
              <div className="text-base font-bold font-mono text-indigo-600 dark:text-indigo-400 mt-0.5">
                {isFree ? (
                  <span className="text-emerald-600 dark:text-emerald-400">$0.00</span>
                ) : (
                  <>
                    ₹{costInr.toFixed(2)}
                    <span className="text-xs font-normal text-slate-400 ml-1">
                      (${stats?.estimated_cost_usd?.toFixed(4) ?? '0.0000'})
                    </span>
                  </>
                )}
              </div>
              <span className="text-[10px] text-slate-400 mt-0.5 block">
                {isFree ? '100% Free / Local Tier' : 'Based on active config rates'}
              </span>
            </div>

            <div className="p-2.5 rounded-xl bg-slate-50 dark:bg-slate-800/50 border border-slate-100 dark:border-slate-800">
              <span className="text-[10px] text-slate-400 uppercase font-semibold block">Total Requests</span>
              <div className="text-base font-bold font-mono text-slate-900 dark:text-white mt-0.5">
                {stats?.total_requests ?? 0}
              </div>
              <span className="text-[10px] text-slate-400 mt-0.5 block truncate">
                Provider: {providerTier}
              </span>
            </div>
          </div>

          {/* Action Message / Toast */}
          {actionMessage && (
            <div className="mt-2.5 p-2 rounded-lg bg-indigo-50 dark:bg-indigo-950/60 border border-indigo-100 dark:border-indigo-900 text-indigo-800 dark:text-indigo-300 text-xs flex items-center gap-1.5">
              <InformationCircleIcon className="w-4 h-4 shrink-0" />
              <span>{actionMessage}</span>
            </div>
          )}

          {/* Footer Actions */}
          <div className="mt-3 pt-2.5 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between text-xs">
            <div className="flex items-center gap-3">
              <button
                onClick={fetchStats}
                className="flex items-center gap-1 text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-white"
              >
                <ArrowPathIcon className="w-3.5 h-3.5" />
                <span>Refresh</span>
              </button>

              <a
                href="/settings"
                onClick={() => setIsOpen(false)}
                className="text-brand-teal hover:underline"
              >
                Settings
              </a>
            </div>

            <button
              disabled={isLoading}
              onClick={handleClearCache}
              className="flex items-center gap-1 text-rose-600 hover:text-rose-700 dark:text-rose-400 dark:hover:text-rose-300 font-medium px-2 py-1 rounded hover:bg-rose-50 dark:hover:bg-rose-950/40 transition-colors"
            >
              <TrashIcon className="w-3.5 h-3.5" />
              <span>Clear Cache</span>
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
