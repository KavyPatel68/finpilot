import React, { useState, useEffect } from 'react'
import {
  XMarkIcon,
  DocumentDuplicateIcon,
  CheckIcon,
  SparklesIcon,
  TagIcon,
  CalendarDaysIcon,
  ExclamationTriangleIcon,
  PencilSquareIcon,
} from '@heroicons/react/24/outline'
import type { Transaction } from '../../types'
import { formatAmount } from '../../utils/currency'
import { updateTransactionCategory, updateTransactionNotes } from '../../api/transactions'

interface TransactionDetailDrawerProps {
  transaction: Transaction | null
  categories: string[]
  onClose: () => void
  onUpdate: (updatedTx: Transaction) => void
}

export function TransactionDetailDrawer({
  transaction,
  categories,
  onClose,
  onUpdate,
}: TransactionDetailDrawerProps) {
  const [selectedCat, setSelectedCat] = useState('')
  const [createRule, setCreateRule] = useState(true)
  const [notes, setNotes] = useState('')
  const [isSavingCategory, setIsSavingCategory] = useState(false)
  const [isSavingNotes, setIsSavingNotes] = useState(false)
  const [copied, setCopied] = useState(false)
  const [feedbackMessage, setFeedbackMessage] = useState<string | null>(null)

  useEffect(() => {
    if (transaction) {
      setSelectedCat(transaction.category || 'Other')
      setNotes(transaction.notes || '')
      setFeedbackMessage(null)
      setCopied(false)
    }
  }, [transaction])

  // Close on Escape
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && transaction) {
        onClose()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [transaction, onClose])

  if (!transaction) return null

  const isIncome = transaction.direction === 'income'
  const payeeName = transaction.merchant_normalized || transaction.raw_description
  const initial = (payeeName || 'T').charAt(0).toUpperCase()

  const handleCopyRaw = () => {
    navigator.clipboard.writeText(transaction.raw_description)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleSaveCategory = async () => {
    if (!selectedCat || selectedCat === transaction.category) return
    setIsSavingCategory(true)
    setFeedbackMessage(null)
    try {
      const updated = await updateTransactionCategory(
        transaction.id,
        selectedCat,
        createRule
      )
      onUpdate(updated)
      setFeedbackMessage(`Category saved as ${selectedCat}${createRule ? ' & rule created!' : '.'}`)
    } catch (err) {
      setFeedbackMessage('Failed to update category')
    } finally {
      setIsSavingCategory(false)
    }
  }

  const handleSaveNotes = async () => {
    setIsSavingNotes(true)
    setFeedbackMessage(null)
    try {
      const updated = await updateTransactionNotes(transaction.id, notes)
      onUpdate(updated)
      setFeedbackMessage('Notes saved successfully.')
    } catch (err) {
      setFeedbackMessage('Failed to save notes')
    } finally {
      setIsSavingNotes(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-black/40 backdrop-blur-xs flex justify-end animate-in fade-in duration-200">
      <div
        className="w-full max-w-md bg-surface h-full shadow-2xl border-l border-hairline flex flex-col justify-between overflow-y-auto animate-in slide-in-from-right duration-200"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-5 border-b border-hairline flex items-start justify-between bg-surface">
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 rounded-full bg-canvas border border-hairline flex items-center justify-center font-medium text-sm text-content-primary shrink-0">
              {initial}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span
                  className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium uppercase tracking-wider ${
                    isIncome
                      ? 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-500/20'
                      : 'bg-rose-500/10 text-rose-700 dark:text-rose-400 border border-rose-500/20'
                  }`}
                >
                  {transaction.direction}
                </span>
                <span className="text-[11px] tabular-nums text-content-muted">ID #{transaction.id}</span>
              </div>

              <div className="mt-1.5 text-2xl font-semibold tabular-nums text-content-primary">
                <span className={isIncome ? 'text-emerald-600 dark:text-emerald-400' : 'text-content-primary'}>
                  {isIncome ? '+' : '-'}{formatAmount(transaction.amount_minor, 'INR')}
                </span>
              </div>
              <p className="text-xs text-content-muted flex items-center gap-1.5 mt-0.5 tabular-nums">
                <CalendarDaysIcon className="w-3.5 h-3.5" />
                <span>{transaction.date}</span>
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1 rounded text-content-muted hover:text-content-primary hover:bg-canvas transition-colors"
          >
            <XMarkIcon className="w-5 h-5" />
          </button>
        </div>

        {/* Content Details */}
        <div className="p-5 space-y-4 flex-1">
          {feedbackMessage && (
            <div className="p-3 rounded-lg bg-[#4F46E5]/10 border border-[#4F46E5]/20 text-[#4F46E5] dark:text-[#818CF8] text-xs flex items-center gap-2">
              <SparklesIcon className="w-4 h-4 shrink-0" />
              <span>{feedbackMessage}</span>
            </div>
          )}

          {/* Anomaly Notice if flagged */}
          {transaction.is_anomaly && (
            <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-700 dark:text-rose-400 text-xs flex items-center gap-2">
              <ExclamationTriangleIcon className="w-4 h-4 shrink-0" />
              <span>
                <strong>Flagged Anomaly:</strong> Flagged as potential duplicate, unusual spike, or outlier.
              </span>
            </div>
          )}

          {/* Merchant & Narration */}
          <div className="rounded-lg p-3.5 bg-canvas border border-hairline space-y-2">
            <span className="text-[11px] font-medium text-content-muted block">
              Payee / Merchant
            </span>
            <div className="text-sm font-semibold text-content-primary">
              {transaction.merchant_normalized || 'Unrecognized Merchant'}
            </div>

            <div className="pt-2 border-t border-hairline">
              <div className="flex items-center justify-between text-[11px] text-content-muted font-medium mb-1">
                <span>Raw Statement Narration</span>
                <button
                  type="button"
                  onClick={handleCopyRaw}
                  className="flex items-center gap-1 text-[#4F46E5] dark:text-[#818CF8] hover:underline"
                >
                  {copied ? <CheckIcon className="w-3 h-3 text-emerald-500" /> : <DocumentDuplicateIcon className="w-3 h-3" />}
                  <span>{copied ? 'Copied' : 'Copy'}</span>
                </button>
              </div>
              <p className="text-xs text-content-muted break-words leading-relaxed">
                {transaction.raw_description}
              </p>
            </div>
          </div>

          {/* Category & Rule Learning */}
          <div className="rounded-lg p-3.5 bg-canvas border border-hairline space-y-3">
            <div className="flex items-center justify-between">
              <label className="text-[11px] font-medium text-content-muted flex items-center gap-1">
                <TagIcon className="w-3.5 h-3.5" />
                <span>Category</span>
              </label>
              <span className="text-[10px] px-2 py-0.5 rounded-full font-medium bg-surface border border-hairline text-content-muted tabular-nums">
                Source: {transaction.category_source || 'rule'} ({Math.round((transaction.confidence || 1.0) * 100)}%)
              </span>
            </div>

            <div className="space-y-2">
              <select
                value={selectedCat}
                onChange={(e) => setSelectedCat(e.target.value)}
                className="w-full text-xs font-medium rounded-lg border border-hairline px-3 py-2 bg-surface text-content-primary focus:outline-none focus:ring-1 focus:ring-[#4F46E5]"
              >
                {categories.map((cat) => (
                  <option key={cat} value={cat}>
                    {cat}
                  </option>
                ))}
              </select>

              <label className="flex items-center gap-2 text-xs text-content-muted cursor-pointer pt-1">
                <input
                  type="checkbox"
                  checked={createRule}
                  onChange={(e) => setCreateRule(e.target.checked)}
                  className="rounded border-hairline text-[#4F46E5] focus:ring-[#4F46E5]"
                />
                <span>Remember rule for future uploads ({transaction.merchant_normalized || 'this payee'})</span>
              </label>

              <button
                type="button"
                onClick={handleSaveCategory}
                disabled={isSavingCategory || selectedCat === transaction.category}
                className="w-full mt-2 py-1.5 px-3 rounded-lg text-xs font-medium bg-[#4F46E5] text-white hover:bg-[#4338CA] disabled:opacity-40 transition-colors"
              >
                {isSavingCategory ? 'Updating...' : 'Update Category'}
              </button>
            </div>
          </div>

          {/* Metadata Grid */}
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="p-3 rounded-lg bg-canvas border border-hairline">
              <span className="text-[11px] text-content-muted font-medium block">Payment Method</span>
              <span className="font-medium text-content-primary mt-0.5 block">
                {transaction.payment_method || 'Standard Electronic'}
              </span>
            </div>

            <div className="p-3 rounded-lg bg-canvas border border-hairline">
              <span className="text-[11px] text-content-muted font-medium block">Recurring Group</span>
              <span className="font-medium text-content-primary mt-0.5 block truncate">
                {transaction.is_recurring ? 'Active Subscription' : 'One-off payment'}
              </span>
            </div>
          </div>

          {/* Notes Section */}
          <div className="space-y-1.5">
            <label className="text-[11px] font-medium text-content-muted flex items-center gap-1">
              <PencilSquareIcon className="w-3.5 h-3.5" />
              <span>Notes</span>
            </label>
            <textarea
              rows={3}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Add personal notes or tax tags..."
              className="w-full text-xs rounded-lg border border-hairline p-2.5 bg-canvas text-content-primary focus:outline-none focus:ring-1 focus:ring-[#4F46E5] resize-none"
            />
            <div className="flex justify-end">
              <button
                type="button"
                onClick={handleSaveNotes}
                disabled={isSavingNotes || notes === (transaction.notes || '')}
                className="px-3 py-1 text-xs font-medium rounded-lg border border-hairline bg-surface hover:bg-canvas text-content-primary disabled:opacity-40 transition-colors"
              >
                {isSavingNotes ? 'Saving...' : 'Save Notes'}
              </button>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-hairline bg-surface flex justify-between items-center text-xs text-content-muted">
          <span>Ledger Record</span>
          <button
            onClick={onClose}
            className="px-3 py-1.5 rounded-lg border border-hairline hover:bg-canvas text-content-primary font-medium transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}
