import React, { useState, useEffect } from 'react'
import {
  ShieldCheckIcon,
  ChatBubbleLeftRightIcon,
  TrashIcon,
} from '@heroicons/react/24/outline'
import { sendMessage, getChatHistory, clearChatHistory } from '../api/chat'
import type { ChatMessage } from '../types'
import { ChatPanel } from '../components/Chat/ChatPanel'
import { SuggestedQuestions } from '../components/Chat/SuggestedQuestions'
import { CalculationDrawer } from '../components/Chat/CalculationDrawer'

export function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [inspectingCalc, setInspectingCalc] = useState<{
    message: ChatMessage
    query?: string
  } | null>(null)

  const loadHistory = async () => {
    try {
      const hist = await getChatHistory()
      setMessages(hist)
    } catch (err) {
      console.error('Failed to load chat history:', err)
    }
  }

  useEffect(() => {
    loadHistory()
  }, [])

  const handleSend = async (text: string) => {
    const tempUserMsg: ChatMessage = {
      id: Date.now(),
      role: 'user',
      content: text,
      tool_calls: null,
      tool_results: null,
      calculation_metadata: null,
      created_at: new Date().toISOString(),
    }
    setMessages((prev) => [...prev, tempUserMsg])
    setIsLoading(true)

    try {
      const res = await sendMessage(text)
      const assistantMsg: ChatMessage = {
        id: res.message_id || Date.now() + 1,
        role: 'assistant',
        content: res.reply,
        tool_calls: res.tool_calls || null,
        tool_results: res.tool_results || null,
        calculation_metadata: res.calculation_metadata || null,
        created_at: new Date().toISOString(),
      }
      setMessages((prev) => [...prev, assistantMsg])
    } catch (err) {
      alert('Failed to send message. Please make sure backend is active.')
    } finally {
      setIsLoading(false)
    }
  }

  const handleClear = async () => {
    if (!confirm('Clear all conversation history?')) return
    try {
      await clearChatHistory()
      setMessages([])
    } catch (err) {
      alert('Failed to clear chat history')
    }
  }

  return (
    <div className="space-y-6 max-w-5xl mx-auto animate-in fade-in duration-200">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-2 border-b border-hairline">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-content-primary flex items-center gap-2">
            <ChatBubbleLeftRightIcon className="w-5 h-5 text-[#4F46E5] dark:text-[#818CF8]" />
            <span>AI Financial Assistant</span>
          </h1>
          <p className="text-xs text-content-muted mt-1">
            Grounded financial intelligence. Answers queries via deterministic tools and zero-token caching.
          </p>
        </div>

        {messages.length > 0 && (
          <button
            onClick={handleClear}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-content-muted hover:text-rose-600 dark:hover:text-rose-400 border border-hairline bg-surface hover:bg-canvas rounded-lg transition-colors self-start sm:self-auto"
          >
            <TrashIcon className="w-3.5 h-3.5" />
            <span>Clear History</span>
          </button>
        )}
      </div>

      {/* Advisory Notice Banner */}
      <div className="p-3.5 rounded-xl bg-canvas border border-hairline text-content-muted text-xs flex items-center gap-3">
        <ShieldCheckIcon className="w-4 h-4 text-content-muted shrink-0" />
        <p className="leading-relaxed">
          <strong className="text-content-primary font-medium">Decision-Support Guardrail:</strong> FinPilot analyzes your uploaded transactions and provides everyday spending insight. FinPilot never recommends specific securities, commercial loans, or investment schemes.
        </p>
      </div>

      {/* Suggested Quick Inquiries */}
      <SuggestedQuestions onSelect={handleSend} />

      {/* Main Interactive Chat Panel */}
      <ChatPanel
        messages={messages}
        onSend={handleSend}
        onClear={handleClear}
        onInspectCalculation={(msg, query) =>
          setInspectingCalc({ message: msg, query })
        }
        isLoading={isLoading}
      />

      {/* Calculation Telemetry Drawer */}
      {inspectingCalc && (
        <CalculationDrawer
          message={inspectingCalc.message}
          userQuery={inspectingCalc.query}
          onClose={() => setInspectingCalc(null)}
        />
      )}
    </div>
  )
}
