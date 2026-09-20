import React, { useState, useMemo } from 'react'
import { Link } from 'react-router-dom'
import type { Budget } from '../../types'
import { formatAmount } from '../../utils/currency'
import {
  CheckIcon,
  XMarkIcon,
  PencilSquareIcon,
  TrashIcon,
  ArrowRightIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  ChartBarIcon,
} from '@heroicons/react/24/outline'

interface BudgetProgressBarProps {
  budget: Budget
  selectedMonth?: string
  onEdit: (budget: Budget) => void
  onDelete: (id: number) => void
  onInlineLimitSave?: (id: number, newLimitMinor: number) => Promise<void>
}

export function BudgetProgressBar({
  budget,
  selectedMonth,
  onEdit,
  onDelete,
  onInlineLimitSave,
}: BudgetProgressBarProps) {
  const [isEditingInline, setIsEditingInline] = useState(false)
  const [inlineValue, setInlineValue] = useState(String(budget.monthly_limit_minor / 100))
  const [isSavingInline, setIsSavingInline] = useState(false)

  const spentPct = budget.spent_pct || 0
  const isExceeded = budget.status === 'exceeded' || spentPct > 100
  const isWarning = budget.status === 'warning' || (spentPct >= 80 && spentPct <= 100)

  // Projection calculation based on days elapsed
  const projection = useMemo(() => {
    if (!budget.monthly_limit_minor || !budget.spent_minor) {
      return {
        projectedSpendMinor: 0,
        projectedPct: 0,
        paceStatus: 'neutral',
        isCompleteMonth: true,
      }
    }

    let totalDays = 30
    let elapsedDays = 30
    let isCompleteMonth = true

    if (selectedMonth) {
      const parts = selectedMonth.split('-')
      if (parts.length === 2) {
        const y = parseInt(parts[0], 10)
        const m = parseInt(parts[1], 10)
        totalDays = new Date(y, m, 0).getDate()

        const now = new Date()
        const currentYear = now.getFullYear()
        const currentMonth = now.getMonth() + 1

        if (y === currentYear && m === currentMonth) {
          elapsedDays = Math.max(1, Math.min(now.getDate(), totalDays))
          isCompleteMonth = elapsedDays === totalDays
        }
      }
    }

    const projectedSpendMinor =
      elapsedDays > 0
        ? Math.round((budget.spent_minor / elapsedDays) * totalDays)
        : budget.spent_minor

    const projectedPct = Math.round(
      (projectedSpendMinor / budget.monthly_limit_minor) * 100
    )

    let paceStatus: 'under' | 'warning' | 'overshoot' = 'under'
    if (projectedSpendMinor > budget.monthly_limit_minor) {
      paceStatus = 'overshoot'
    } else if (projectedPct >= 80) {
      paceStatus = 'warning'
    }

    return { projectedSpendMinor, projectedPct, paceStatus, isCompleteMonth }
  }, [budget, selectedMonth])

  const getBarColor = () => {
    if (isExceeded) return 'bg-rose-500 dark:bg-rose-500'
    if (isWarning) return 'bg-amber-500 dark:bg-amber-500'
    return 'bg-[#4F46E5] dark:bg-[#818CF8]'
  }

  const handleSaveInline = async () => {
    const parsed = Math.round(Number(inlineValue) * 100)
    if (!parsed || parsed <= 0) {
      alert('Please enter a valid amount in Rupees')
      return
    }

    if (onInlineLimitSave) {
      setIsSavingInline(true)
      try {
        await onInlineLimitSave(budget.id, parsed)
        setIsEditingInline(false)
      } catch (err) {
        alert('Failed to update limit')
      } finally {
        setIsSavingInline(false)
      }
    } else {
      onEdit({ ...budget, monthly_limit_minor: parsed })
      setIsEditingInline(false)
    }
  }

  return (
    <div
      className={`rounded-xl border bg-surface p-4 transition-colors space-y-3 ${
        isExceeded
          ? 'border-rose-500/30'
          : isWarning
          ? 'border-amber-500/30'
          : 'border-hairline'
      }`}
    >
      {/* Top Header: Category, Status Badge & Actions */}
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="font-semibold text-content-primary text-sm tracking-tight">
              {budget.category}
            </h3>

            {isExceeded ? (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium uppercase tracking-wider bg-rose-500/10 text-rose-700 dark:text-rose-400 border border-rose-500/20">
                <ExclamationTriangleIcon className="w-3 h-3" /> Over Budget
              </span>
            ) : isWarning ? (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium uppercase tracking-wider bg-amber-500/10 text-amber-700 dark:text-amber-400 border border-amber-500/20">
                <ExclamationTriangleIcon className="w-3 h-3" /> Near Limit ({spentPct}%)
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium uppercase tracking-wider bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-500/20">
                <CheckCircleIcon className="w-3 h-3" /> On Track
              </span>
            )}
          </div>

          {/* Inline Limit Editor or Display */}
          <div className="mt-1 flex items-center gap-1.5 text-xs">
            {isEditingInline ? (
              <div className="flex items-center gap-1">
                <span className="text-content-muted">₹</span>
                <input
                  type="number"
                  min="100"
                  step="100"
                  value={inlineValue}
                  onChange={(e) => setInlineValue(e.target.value)}
                  className="w-24 px-2 py-0.5 rounded border border-[#4F46E5] bg-canvas text-content-primary text-xs font-medium tabular-nums focus:outline-none"
                  autoFocus
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') handleSaveInline()
                    if (e.key === 'Escape') setIsEditingInline(false)
                  }}
                />
                <button
                  onClick={handleSaveInline}
                  disabled={isSavingInline}
                  title="Save Limit"
                  className="p-1 rounded text-emerald-600 hover:bg-canvas"
                >
                  <CheckIcon className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={() => {
                    setInlineValue(String(budget.monthly_limit_minor / 100))
                    setIsEditingInline(false)
                  }}
                  title="Cancel"
                  className="p-1 rounded text-content-muted hover:text-content-primary"
                >
                  <XMarkIcon className="w-3.5 h-3.5" />
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-1.5 text-content-muted">
                <span>Limit:</span>
                <span className="font-semibold tabular-nums text-content-primary">
                  {formatAmount(budget.monthly_limit_minor, 'INR')}
                </span>
                <span>/mo</span>
                <button
                  onClick={() => setIsEditingInline(true)}
                  title="Quick Edit Limit"
                  className="p-0.5 rounded text-content-muted hover:text-[#4F46E5] dark:hover:text-[#818CF8] transition-colors"
                >
                  <PencilSquareIcon className="w-3.5 h-3.5" />
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-1">
          <Link
            to={`/transactions?category=${encodeURIComponent(budget.category)}`}
            title={`View ${budget.category} transactions`}
            className="p-1 rounded text-content-muted hover:text-[#4F46E5] dark:hover:text-[#818CF8] hover:bg-canvas transition-colors"
          >
            <ChartBarIcon className="w-4 h-4" />
          </Link>
          <button
            onClick={() => onEdit(budget)}
            title="Configure Budget"
            className="p-1 rounded text-content-muted hover:text-content-primary hover:bg-canvas transition-colors"
          >
            <PencilSquareIcon className="w-4 h-4" />
          </button>
          <button
            onClick={() => onDelete(budget.id)}
            title="Delete Budget"
            className="p-1 rounded text-content-muted hover:text-rose-600 hover:bg-canvas transition-colors"
          >
            <TrashIcon className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Slim 6px Progress Bar */}
      <div className="space-y-1.5">
        <div className="relative w-full bg-canvas border border-hairline rounded-full h-2 overflow-visible">
          {/* Fill */}
          <div
            className={`h-full rounded-full transition-all duration-500 ease-out ${getBarColor()}`}
            style={{ width: `${Math.min(spentPct, 100)}%` }}
          />

          {/* Projected Marker Pin */}
          {!projection.isCompleteMonth && projection.projectedPct > 0 && (
            <div
              title={`Projected End-of-Month: ${formatAmount(
                projection.projectedSpendMinor,
                'INR'
              )} (${projection.projectedPct}%)`}
              style={{
                left: `${Math.min(Math.max(projection.projectedPct, 2), 98)}%`,
              }}
              className="absolute -top-1 bottom-0 z-20 pointer-events-none"
            >
              <div
                className={`w-1 h-4 -mt-0.5 rounded-full shadow-xs ${
                  projection.paceStatus === 'overshoot'
                    ? 'bg-rose-600'
                    : projection.paceStatus === 'warning'
                    ? 'bg-amber-500'
                    : 'bg-[#4F46E5] dark:bg-[#818CF8]'
                }`}
              />
            </div>
          )}
        </div>

        {/* Metrics Row: Spent vs Remaining / Exceeded */}
        <div className="flex justify-between items-baseline text-xs pt-0.5">
          <span className="text-content-muted font-medium">
            Spent:{' '}
            <strong className="font-semibold tabular-nums text-content-primary">
              {formatAmount(budget.spent_minor || 0, 'INR')}
            </strong>{' '}
            <span className="text-content-muted tabular-nums">({spentPct}%)</span>
          </span>

          <span
            className={`tabular-nums font-medium ${
              isExceeded
                ? 'text-rose-600 dark:text-rose-400 font-semibold'
                : 'text-content-muted'
            }`}
          >
            {isExceeded
              ? `+${formatAmount(
                  (budget.spent_minor || 0) - budget.monthly_limit_minor,
                  'INR'
                )} Over`
              : `Remaining: ${formatAmount(budget.remaining_minor || 0, 'INR')}`}
          </span>
        </div>

        {/* Velocity / Projected Subtext */}
        <div className="pt-1 text-[11px] flex items-center justify-between border-t border-hairline text-content-muted">
          {!projection.isCompleteMonth ? (
            <div className="flex items-center gap-1 truncate">
              {projection.paceStatus === 'overshoot' ? (
                <span className="text-rose-600 dark:text-rose-400 font-medium">
                  ⚠️ Projects spend of{' '}
                  <span className="tabular-nums font-semibold">
                    {formatAmount(projection.projectedSpendMinor, 'INR')}
                  </span>{' '}
                  ({projection.projectedPct}%)
                </span>
              ) : (
                <span className="text-content-muted">
                  Projects{' '}
                  <span className="tabular-nums font-medium text-content-primary">
                    {formatAmount(projection.projectedSpendMinor, 'INR')}
                  </span>{' '}
                  by month-end
                </span>
              )}
            </div>
          ) : (
            <span>
              {isExceeded
                ? 'Month closed above budget limit'
                : 'Month closed within planned budget'}
            </span>
          )}

          <Link
            to={`/transactions?category=${encodeURIComponent(budget.category)}`}
            className="text-[#4F46E5] dark:text-[#818CF8] hover:underline flex items-center gap-0.5 shrink-0 ml-2 font-medium"
          >
            <span>Ledger</span>
            <ArrowRightIcon className="w-2.5 h-2.5" />
          </Link>
        </div>
      </div>
    </div>
  )
}
