import React, { useState, useRef, useEffect } from 'react'
import {
  PaperAirplaneIcon,
  TrashIcon,
  SparklesIcon,
  BoltIcon,
  ArrowsPointingOutIcon,
  ArrowsPointingInIcon,
  QuestionMarkCircleIcon,
} from '@heroicons/react/24/outline'
import type { ChatMessage } from '../../types'

interface ChatPanelProps {
  messages: ChatMessage[]
  onSend: (message: string) => Promise<void>
  onClear: () => Promise<void>
  onInspectCalculation: (message: ChatMessage, query?: string) => void
  isLoading: boolean
}

export function ChatPanel({
  messages,
  onSend,
  onClear,
  onInspectCalculation,
  isLoading,
}: ChatPanelProps) {
  const [input, setInput] = useState('')
  const [isExpanded, setIsExpanded] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, isLoading])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || isLoading) return
    const text = input.trim()
    setInput('')
    await onSend(text)
  }

  // Find corresponding user query for an assistant response
  const getUserQueryForAssistant = (index: number): string | undefined => {
    for (let i = index - 1; i >= 0; i--) {
      if (messages[i].role === 'user') {
        return messages[i].content
      }
    }
    return undefined
  }

  return (
    <div
      className={`flex flex-col transition-all duration-300 rounded-xl border bg-surface border-hairline shadow-2xs overflow-hidden ${
        isExpanded ? 'h-[800px]' : 'h-[620px]'
      }`}
    >
      {/* Header Toolbar */}
      <div className="px-5 py-3 border-b border-hairline flex items-center justify-between bg-surface">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-emerald-500" />
          <span className="text-xs font-medium text-content-primary">
            Financial Assistant
          </span>
          <span className="hidden sm:inline-block px-2 py-0.5 rounded-full text-[10px] font-medium uppercase tracking-wider bg-canvas border border-hairline text-content-muted">
            Zero-Token Optimized
          </span>
        </div>

        <div className="flex items-center gap-2">
          {messages.length > 0 && (
            <button
              onClick={onClear}
              className="flex items-center gap-1 text-xs text-content-muted hover:text-rose-600 dark:hover:text-rose-400 font-medium px-2 py-1 rounded transition-colors"
              title="Clear conversation history"
            >
              <TrashIcon className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Clear</span>
            </button>
          )}

          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="p-1 rounded text-content-muted hover:text-content-primary hover:bg-canvas transition-colors"
            title={isExpanded ? 'Dock view' : 'Expand full view'}
          >
            {isExpanded ? (
              <ArrowsPointingInIcon className="w-4 h-4" />
            ) : (
              <ArrowsPointingOutIcon className="w-4 h-4" />
            )}
          </button>
        </div>
      </div>

      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto p-5 sm:p-6 space-y-4">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center p-6 space-y-2.5">
            <div className="w-10 h-10 rounded-lg bg-canvas border border-hairline flex items-center justify-center text-content-muted">
              <SparklesIcon className="w-5 h-5 text-[#4F46E5] dark:text-[#818CF8]" />
            </div>
            <h3 className="font-semibold text-content-primary text-sm">
              Ask FinPilot Anything
            </h3>
            <p className="text-xs text-content-muted max-w-sm leading-relaxed">
              Ask about dining spend, monthly inflows, active subscriptions, or savings targets.
              FinPilot uses deterministic tools first for instant, grounded answers.
            </p>
          </div>
        ) : (
          messages.map((m, idx) => {
            const isUser = m.role === 'user'
            const meta = m.calculation_metadata
            const isZeroToken = meta?.is_zero_token ?? true

            return (
              <div
                key={m.id || idx}
                className={`flex gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}
              >
                {!isUser && (
                  <div className="w-7 h-7 rounded-lg bg-canvas border border-hairline text-content-muted flex items-center justify-center text-[10px] font-semibold shrink-0 mt-0.5">
                    FP
                  </div>
                )}

                <div
                  className={`max-w-xl rounded-xl p-3.5 text-xs leading-relaxed space-y-2 shadow-2xs ${
                    isUser
                      ? 'bg-[#4F46E5] text-white rounded-tr-xs'
                      : 'bg-surface border border-hairline text-content-primary rounded-tl-xs'
                  }`}
                >
                  {/* Message Content */}
                  <div className="whitespace-pre-wrap leading-relaxed font-normal">
                    {m.content}
                  </div>

                  {/* Assistant Telemetry & Calculation Inspector */}
                  {!isUser && (
                    <div className="pt-2 border-t border-hairline flex items-center justify-between gap-2 flex-wrap text-[10px]">
                      <div className="flex items-center gap-1.5">
                        <span
                          className={`inline-flex items-center gap-0.5 px-2 py-0.5 rounded-full font-medium ${
                            isZeroToken
                              ? 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-500/20'
                              : 'bg-[#4F46E5]/10 text-[#4F46E5] dark:text-[#818CF8] border border-[#4F46E5]/20'
                          }`}
                        >
                          <BoltIcon className="w-2.5 h-2.5" />
                          {isZeroToken ? '0 Tokens' : 'LLM Synthesized'}
                        </span>

                        <span className="text-content-muted tabular-nums">
                          {new Date(m.created_at).toLocaleTimeString([], {
                            hour: '2-digit',
                            minute: '2-digit',
                          })}
                        </span>
                      </div>

                      {/* "How was this calculated?" trigger */}
                      <button
                        onClick={() =>
                          onInspectCalculation(m, getUserQueryForAssistant(idx))
                        }
                        className="inline-flex items-center gap-1 font-medium text-[#4F46E5] dark:text-[#818CF8] hover:underline cursor-pointer"
                      >
                        <QuestionMarkCircleIcon className="w-3 h-3" />
                        <span>How was this calculated?</span>
                      </button>
                    </div>
                  )}

                  {/* User Message Timestamp */}
                  {isUser && (
                    <div className="text-[10px] text-indigo-200 text-right tabular-nums">
                      {new Date(m.created_at).toLocaleTimeString([], {
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </div>
                  )}
                </div>
              </div>
            )
          })
        )}

        {/* Typing Indicator */}
        {isLoading && (
          <div className="flex gap-3 justify-start items-center">
            <div className="w-7 h-7 rounded-lg bg-canvas border border-hairline text-content-muted flex items-center justify-center text-[10px] font-semibold shrink-0">
              FP
            </div>
            <div className="bg-surface border border-hairline rounded-xl px-4 py-2.5 text-xs text-content-muted flex items-center gap-2">
              <span className="flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-[#4F46E5] animate-bounce [animation-delay:-0.3s]" />
                <span className="w-1.5 h-1.5 rounded-full bg-[#4F46E5] animate-bounce [animation-delay:-0.15s]" />
                <span className="w-1.5 h-1.5 rounded-full bg-[#4F46E5] animate-bounce" />
              </span>
              <span>Evaluating intent & querying database records...</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Message Input Box */}
      <form
        onSubmit={handleSubmit}
        className="p-3 border-t border-hairline bg-surface"
      >
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about spending, bills, budgets, or goals... (e.g. 'What subscriptions do I have?')"
            className="flex-1 text-xs rounded-lg border border-hairline px-3.5 py-2 bg-canvas text-content-primary placeholder:text-content-muted focus:outline-none focus:ring-1 focus:ring-[#4F46E5]"
          />
          <button
            type="submit"
            disabled={!input.trim() || isLoading}
            className="px-4 py-2 bg-[#4F46E5] hover:bg-[#4338CA] text-white text-xs font-medium rounded-lg disabled:opacity-40 transition-colors shrink-0 flex items-center gap-1.5"
          >
            <span>Send</span>
            <PaperAirplaneIcon className="w-3.5 h-3.5" />
          </button>
        </div>
      </form>
    </div>
  )
}
