import React from 'react'
import {
  ChevronUpIcon,
  ChevronDownIcon,
  SparklesIcon,
  ExclamationTriangleIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline'
import type { Transaction } from '../../types'
import { formatAmount } from '../../utils/currency'

interface TransactionTableProps {
  transactions: Transaction[]
  sortBy: 'date' | 'amount_minor'
  sortOrder: 'asc' | 'desc'
  onSort: (col: 'date' | 'amount_minor') => void
  onSelectTransaction: (transaction: Transaction) => void
  onEditCategory: (transaction: Transaction) => void
}

export function TransactionTable({
  transactions,
  sortBy,
  sortOrder,
  onSort,
  onSelectTransaction,
  onEditCategory,
}: TransactionTableProps) {
  if (!transactions || transactions.length === 0) {
    return (
      <div className="text-center py-16 text-xs text-content-muted bg-surface rounded-xl border border-hairline">
        No transactions match your search and filter criteria.
      </div>
    )
  }

  const getSourceBadge = (source: string | null | undefined) => {
    switch (source) {
      case 'rule':
        return (
          <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-canvas border border-hairline text-content-muted">
            Rule
          </span>
        )
      case 'llm':
        return (
          <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-[#4F46E5]/10 text-[#4F46E5] dark:text-[#818CF8] border border-[#4F46E5]/20 inline-flex items-center gap-0.5">
            <SparklesIcon className="w-2.5 h-2.5" /> AI
          </span>
        )
      case 'user':
        return (
          <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-amber-500/10 text-amber-700 dark:text-amber-400 border border-amber-500/20">
            User
          </span>
        )
      default:
        return (
          <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-canvas border border-hairline text-content-muted">
            Auto
          </span>
        )
    }
  }

  const renderSortIndicator = (col: 'date' | 'amount_minor') => {
    if (sortBy !== col) return null
    return sortOrder === 'asc' ? (
      <ChevronUpIcon className="w-3.5 h-3.5 inline ml-1 text-[#4F46E5] dark:text-[#818CF8]" />
    ) : (
      <ChevronDownIcon className="w-3.5 h-3.5 inline ml-1 text-[#4F46E5] dark:text-[#818CF8]" />
    )
  }

  return (
    <div className="rounded-xl border border-hairline bg-surface overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-xs text-left">
          {/* Sticky Header */}
          <thead className="sticky top-0 z-10 bg-canvas/90 backdrop-blur-xs text-content-muted font-medium border-b border-hairline">
            <tr>
              <th
                onClick={() => onSort('date')}
                className="px-5 py-3 w-32 cursor-pointer hover:text-content-primary select-none transition-colors"
              >
                Date {renderSortIndicator('date')}
              </th>
              <th className="px-4 py-3">Description & Payee</th>
              <th className="px-4 py-3">Category</th>
              <th className="px-4 py-3">Method</th>
              <th
                onClick={() => onSort('amount_minor')}
                className="px-5 py-3 text-right cursor-pointer hover:text-content-primary select-none transition-colors"
              >
                Amount {renderSortIndicator('amount_minor')}
              </th>
              <th className="px-4 py-3 text-center w-20">Action</th>
            </tr>
          </thead>

          <tbody className="divide-y divide-hairline text-content-primary">
            {transactions.map((t) => {
              const isIncome = t.direction === 'income'
              return (
                <tr
                  key={t.id}
                  onClick={() => onSelectTransaction(t)}
                  className="hover:bg-canvas/60 cursor-pointer transition-colors"
                >
                  {/* Date with Inter tabular numbers */}
                  <td className="px-5 py-3 text-content-muted tabular-nums whitespace-nowrap text-[11px]">
                    {t.date}
                  </td>

                  {/* Description & Payee */}
                  <td className="px-4 py-3 max-w-sm">
                    <div className="flex items-center gap-1.5 flex-wrap">
                      <span className="font-medium text-content-primary truncate">
                        {t.merchant_normalized || t.raw_description}
                      </span>
                      {t.is_anomaly && (
                        <span
                          title="Flagged anomaly / unusual spike"
                          className="inline-flex items-center gap-0.5 px-1.5 py-0.2 rounded text-[10px] font-medium bg-rose-500/10 text-rose-700 dark:text-rose-400 border border-rose-500/20"
                        >
                          <ExclamationTriangleIcon className="w-2.5 h-2.5" /> Anomaly
                        </span>
                      )}
                      {t.is_recurring && (
                        <span
                          title="Recurring subscription / bill"
                          className="inline-flex items-center gap-0.5 px-1.5 py-0.2 rounded text-[10px] font-medium bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-500/20"
                        >
                          <ArrowPathIcon className="w-2.5 h-2.5" /> Recurring
                        </span>
                      )}
                      {t.is_transfer && (
                        <span
                          title="Own-account transfer (excluded from totals)"
                          className="px-1.5 py-0.2 rounded text-[10px] font-medium bg-canvas border border-hairline text-content-muted"
                        >
                          Transfer
                        </span>
                      )}
                    </div>

                    {t.merchant_normalized && t.merchant_normalized !== t.raw_description && (
                      <div className="text-[11px] text-content-muted truncate mt-0.5">
                        {t.raw_description}
                      </div>
                    )}
                  </td>

                  {/* Category + Source */}
                  <td className="px-4 py-3 whitespace-nowrap">
                    <div className="flex items-center gap-1.5">
                      <span className="px-2 py-0.5 rounded-full text-[11px] font-medium bg-canvas border border-hairline text-content-primary">
                        {t.category || 'Other'}
                      </span>
                      {getSourceBadge(t.category_source)}
                    </div>
                  </td>

                  {/* Payment Method */}
                  <td className="px-4 py-3 whitespace-nowrap text-content-muted">
                    {t.payment_method ? (
                      <span className="px-1.5 py-0.5 rounded text-[10px] font-medium uppercase bg-canvas border border-hairline text-content-muted">
                        {t.payment_method}
                      </span>
                    ) : (
                      '—'
                    )}
                  </td>

                  {/* Amount with Inter tabular numbers */}
                  <td
                    className={`px-5 py-3 text-right font-medium tabular-nums whitespace-nowrap ${
                      isIncome
                        ? 'text-emerald-600 dark:text-emerald-400'
                        : 'text-content-primary'
                    }`}
                  >
                    {isIncome ? '+' : '-'}
                    {formatAmount(t.amount_minor, 'INR')}
                  </td>

                  {/* Action */}
                  <td
                    className="px-4 py-3 text-center whitespace-nowrap"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <button
                      onClick={() => onEditCategory(t)}
                      className="text-[#4F46E5] dark:text-[#818CF8] hover:underline font-medium px-2 py-1 rounded transition-colors"
                    >
                      Edit
                    </button>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
