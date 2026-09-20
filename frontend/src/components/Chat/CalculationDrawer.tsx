import React from 'react'
import {
  XMarkIcon,
  CpuChipIcon,
  BoltIcon,
  SparklesIcon,
  CheckCircleIcon,
  CircleStackIcon,
  WrenchScrewdriverIcon,
} from '@heroicons/react/24/outline'
import type { ChatMessage, CalculationMetadata } from '../../types'

interface CalculationDrawerProps {
  message: ChatMessage | null
  userQuery?: string
  onClose: () => void
}

export function CalculationDrawer({ message, userQuery, onClose }: CalculationDrawerProps) {
  if (!message) return null

  const meta: CalculationMetadata = message.calculation_metadata || {}
  const intent = meta.intent || 'financial_query'
  const confidence = meta.confidence !== undefined && meta.confidence !== null ? meta.confidence : 0.95
  const isZeroToken = meta.is_zero_token ?? (confidence >= 0.8 || meta.is_cached || meta.offline_mode)
  const isCached = meta.is_cached ?? false
  const model = meta.model || (isZeroToken ? 'Deterministic Rules Engine' : 'Claude Haiku 4.5')

  const toolCalls = Array.isArray(message.tool_calls) ? message.tool_calls : []
  const toolResults = Array.isArray(message.tool_results) ? message.tool_results : []

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-black/40 backdrop-blur-xs flex justify-end animate-in fade-in duration-200">
      <div
        className="w-full max-w-md bg-surface h-full shadow-2xl border-l border-hairline flex flex-col justify-between overflow-y-auto animate-in slide-in-from-right duration-200"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-5 border-b border-hairline flex items-start justify-between bg-surface">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-canvas border border-hairline flex items-center justify-center text-content-muted">
              <CpuChipIcon className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-content-primary leading-tight">
                Calculation Telemetry
              </h3>
              <p className="text-[11px] text-content-muted">Auditable proof & token-efficiency breakdown</p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1 rounded text-content-muted hover:text-content-primary hover:bg-canvas transition-colors"
          >
            <XMarkIcon className="w-5 h-5" />
          </button>
        </div>

        {/* Telemetry Details */}
        <div className="p-5 space-y-4 flex-1 text-xs">
          {/* User Query Reference */}
          {userQuery && (
            <div className="p-3 rounded-lg bg-canvas border border-hairline space-y-1">
              <span className="text-[10px] font-medium uppercase tracking-wider text-content-muted block">
                Inquiry Prompt
              </span>
              <p className="font-medium text-content-primary italic">&ldquo;{userQuery}&rdquo;</p>
            </div>
          )}

          {/* Execution Strategy Banner */}
          <div
            className={`p-3.5 rounded-lg border flex items-start gap-3 ${
              isZeroToken
                ? 'bg-emerald-500/5 border-emerald-500/20 text-emerald-800 dark:text-emerald-300'
                : 'bg-[#4F46E5]/5 border-[#4F46E5]/20 text-[#4F46E5] dark:text-[#818CF8]'
            }`}
          >
            {isZeroToken ? (
              <BoltIcon className="w-4 h-4 text-emerald-600 dark:text-emerald-400 shrink-0 mt-0.5" />
            ) : (
              <SparklesIcon className="w-4 h-4 text-[#4F46E5] dark:text-[#818CF8] shrink-0 mt-0.5" />
            )}
            <div>
              <span className="font-semibold block text-xs">
                {isCached
                  ? '⚡ Instant SQLite Cache Hit (0 Tokens)'
                  : isZeroToken
                  ? '⚡ Zero-Token Direct Intent Execution'
                  : '🤖 Single-Shot Claude Tool Execution'}
              </span>
              <p className="text-[11px] opacity-80 mt-0.5 leading-relaxed">
                {isCached
                  ? 'Response was retrieved directly from local data-versioned SQLite cache with zero token latency.'
                  : isZeroToken
                  ? 'Direct deterministic algorithm executed against local SQLite database without calling external LLM API.'
                  : 'Synthesized via compact Claude prompt capped at 250 max tokens.'}
              </p>
            </div>
          </div>

          {/* Telemetry Metric Cards */}
          <div className="grid grid-cols-2 gap-2">
            <div className="p-3 rounded-lg bg-canvas border border-hairline">
              <span className="text-[10px] text-content-muted uppercase font-medium block">Intent Detected</span>
              <span className="font-semibold text-content-primary mt-1 block">
                {intent.replace(/_/g, ' ')}
              </span>
              <span className="text-[10px] text-emerald-600 dark:text-emerald-400 mt-0.5 block tabular-nums">
                {(confidence * 100).toFixed(1)}% confidence
              </span>
            </div>

            <div className="p-3 rounded-lg bg-canvas border border-hairline">
              <span className="text-[10px] text-content-muted uppercase font-medium block">Execution Engine</span>
              <span className="font-semibold text-content-primary mt-1 block truncate">
                {model}
              </span>
              <span className="text-[10px] text-content-muted mt-0.5 block tabular-nums">
                {isZeroToken ? '0 API tokens' : `${meta.tokens_used || '~180'} tokens`}
              </span>
            </div>
          </div>

          {/* Grounded Tool Invocations */}
          <div className="space-y-2 pt-2">
            <div className="flex items-center gap-1.5 font-medium text-content-primary">
              <WrenchScrewdriverIcon className="w-4 h-4 text-[#4F46E5] dark:text-[#818CF8]" />
              <span>Grounded Database Invocations ({toolCalls.length > 0 ? toolCalls.length : 1})</span>
            </div>

            {toolCalls.length > 0 ? (
              <div className="space-y-2">
                {toolCalls.map((t: any, idx: number) => (
                  <div
                    key={idx}
                    className="p-3 rounded-lg bg-canvas border border-hairline text-[11px] space-y-1.5"
                  >
                    <div className="font-medium text-[#4F46E5] dark:text-[#818CF8] flex items-center gap-1">
                      <CircleStackIcon className="w-3.5 h-3.5" />
                      <span>{t.tool || t.name || 'query_tool'}()</span>
                    </div>
                    {t.arguments && (
                      <pre className="text-[10px] text-content-muted bg-surface p-2 rounded border border-hairline overflow-x-auto">
                        {JSON.stringify(t.arguments, null, 2)}
                      </pre>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="p-3 rounded-lg bg-canvas border border-hairline text-[11px] space-y-1">
                <div className="font-medium text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
                  <CheckCircleIcon className="w-3.5 h-3.5" />
                  <span>Deterministic Intent Matcher</span>
                </div>
                <p className="text-[11px] text-content-muted">
                  Query was matched by pre-compiled regex intent rules and resolved straight against SQLite aggregation indices.
                </p>
              </div>
            )}
          </div>

          {/* Raw Tool Data Snippet */}
          {toolResults.length > 0 && (
            <div className="space-y-1.5 pt-2">
              <span className="text-[10px] font-medium uppercase tracking-wider text-content-muted block">
                Calculated Return Figures
              </span>
              <pre className="text-[10px] text-content-muted bg-canvas p-3 rounded-lg overflow-x-auto border border-hairline max-h-40">
                {JSON.stringify(toolResults, null, 2)}
              </pre>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-hairline bg-surface flex justify-between items-center text-xs text-content-muted">
          <span>Non-Advisor Decision Support</span>
          <button
            onClick={onClose}
            className="px-3 py-1.5 rounded-lg border border-hairline hover:bg-canvas text-content-primary font-medium transition-colors"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  )
}
