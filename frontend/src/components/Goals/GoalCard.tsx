import React from 'react'
import type { Goal } from '../../types'
import { formatAmount } from '../../utils/currency'
import {
  CheckCircleIcon,
  ExclamationTriangleIcon,
  PlusIcon,
  TrashIcon,
  PencilSquareIcon,
} from '@heroicons/react/24/outline'

interface GoalCardProps {
  goal: Goal
  onUpdateProgress: (goal: Goal) => void
  onEdit?: (goal: Goal) => void
  onDelete: (id: number) => void
}

export function GoalCard({ goal, onUpdateProgress, onEdit, onDelete }: GoalCardProps) {
  const pct = Math.min(100, Math.max(0, goal.progress_pct || 0))
  const isCompleted = pct >= 100

  // SVG Circular Progress Ring calculations with thin 3.5px stroke
  const radius = 26
  const strokeWidth = 3.5
  const circumference = 2 * Math.PI * radius
  const strokeDashoffset = circumference - (pct / 100) * circumference

  const getTypeBadge = (type: string) => {
    switch (type) {
      case 'emergency_fund':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-medium uppercase tracking-wider bg-canvas border border-hairline text-content-muted">
            Emergency Fund
          </span>
        )
      case 'purchase':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-medium uppercase tracking-wider bg-canvas border border-hairline text-content-muted">
            Planned Purchase
          </span>
        )
      default:
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-medium uppercase tracking-wider bg-canvas border border-hairline text-content-muted">
            Custom Goal
          </span>
        )
    }
  }

  const getStatusBadge = () => {
    if (isCompleted) {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium uppercase tracking-wider bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-500/20">
          <CheckCircleIcon className="w-3 h-3" /> Completed
        </span>
      )
    }
    if (goal.on_track === true) {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium uppercase tracking-wider bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-500/20">
          <CheckCircleIcon className="w-3 h-3" /> On Track
        </span>
      )
    }
    if (goal.on_track === false) {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium uppercase tracking-wider bg-amber-500/10 text-amber-700 dark:text-amber-400 border border-amber-500/20">
          <ExclamationTriangleIcon className="w-3 h-3" /> Behind
        </span>
      )
    }
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium uppercase tracking-wider bg-canvas text-content-muted border border-hairline">
        Flexible
      </span>
    )
  }

  const getRingColor = () => {
    if (isCompleted) return 'text-emerald-600 dark:text-emerald-400 stroke-current'
    if (goal.on_track === false) return 'text-amber-500 stroke-current'
    return 'text-[#4F46E5] dark:text-[#818CF8] stroke-current'
  }

  return (
    <div className="rounded-xl border bg-surface border-hairline p-5 shadow-2xs hover:border-[#4F46E5]/40 dark:hover:border-[#818CF8]/40 transition-colors flex flex-col justify-between space-y-4">
      <div className="space-y-4">
        {/* Header Row: Title, Type & Actions */}
        <div className="flex items-start justify-between gap-3">
          <div className="space-y-1">
            <div className="flex items-center gap-2 flex-wrap">
              <h3 className="font-semibold text-content-primary text-sm tracking-tight">
                {goal.name}
              </h3>
              {getStatusBadge()}
            </div>
            <div>{getTypeBadge(goal.type)}</div>
          </div>

          <div className="flex items-center gap-1">
            {onEdit && (
              <button
                onClick={() => onEdit(goal)}
                title="Edit Goal"
                className="p-1 rounded text-content-muted hover:text-content-primary hover:bg-canvas transition-colors"
              >
                <PencilSquareIcon className="w-4 h-4" />
              </button>
            )}
            <button
              onClick={() => onDelete(goal.id)}
              title="Delete Goal"
              className="p-1 rounded text-content-muted hover:text-rose-600 hover:bg-canvas transition-colors"
            >
              <TrashIcon className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Progress Ring & Balance Overview */}
        <div className="flex items-center gap-5 p-3.5 rounded-lg bg-canvas border border-hairline">
          {/* Thin Circular SVG Ring */}
          <div className="relative shrink-0 w-16 h-16 flex items-center justify-center">
            <svg className="w-16 h-16 -rotate-90 transform" viewBox="0 0 64 64">
              <circle
                cx="32"
                cy="32"
                r={radius}
                className="text-hairline stroke-current"
                strokeWidth={strokeWidth}
                fill="transparent"
              />
              <circle
                cx="32"
                cy="32"
                r={radius}
                className={`${getRingColor()} transition-all duration-500 ease-out`}
                strokeWidth={strokeWidth}
                strokeDasharray={circumference}
                strokeDashoffset={strokeDashoffset}
                strokeLinecap="round"
                fill="transparent"
              />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
              <span className="text-xs font-semibold tabular-nums text-content-primary">
                {Math.round(pct)}%
              </span>
              <span className="text-[8px] text-content-muted uppercase font-medium">Funded</span>
            </div>
          </div>

          {/* Amount Balance */}
          <div className="flex-1 space-y-0.5">
            <div className="text-[11px] text-content-muted">Current Balance</div>
            <div className="text-xl font-semibold tabular-nums text-content-primary">
              {formatAmount(goal.current_amount_minor, 'INR')}
            </div>
            <div className="text-[11px] text-content-muted tabular-nums">
              Target: <strong className="font-medium text-content-primary">{formatAmount(goal.target_amount_minor, 'INR')}</strong>
            </div>
          </div>
        </div>

        {/* Target Date & Contribution Pacing Details */}
        <div className="grid grid-cols-2 gap-2 text-xs">
          <div className="p-2.5 rounded-lg bg-canvas border border-hairline space-y-0.5">
            <span className="text-[10px] text-content-muted block uppercase font-medium">
              Planned Monthly
            </span>
            <span className="tabular-nums font-semibold text-content-primary block text-xs">
              {goal.monthly_contribution_planned_minor
                ? formatAmount(goal.monthly_contribution_planned_minor, 'INR')
                : 'Flexible'}
            </span>
            <span className="text-[10px] text-content-muted">Allocation</span>
          </div>

          <div className="p-2.5 rounded-lg bg-canvas border border-hairline space-y-0.5">
            <span className="text-[10px] text-content-muted block uppercase font-medium">
              Required Monthly
            </span>
            <span
              className={`tabular-nums font-semibold block text-xs ${
                goal.on_track === false
                  ? 'text-amber-600 dark:text-amber-400'
                  : 'text-content-primary'
              }`}
            >
              {isCompleted
                ? 'Achieved'
                : goal.required_monthly_savings_minor
                ? formatAmount(goal.required_monthly_savings_minor, 'INR')
                : '—'}
            </span>
            <span className="text-[10px] text-content-muted tabular-nums">
              {goal.months_remaining !== null
                ? `${goal.months_remaining} mo remaining`
                : 'Flexible target'}
            </span>
          </div>
        </div>

        {/* Feasibility Alert Note */}
        {goal.on_track === false && !isCompleted && goal.required_monthly_savings_minor && (
          <div className="p-2.5 rounded-lg bg-amber-500/5 border border-amber-500/20 text-[11px] text-amber-800 dark:text-amber-300 flex items-start gap-2">
            <ExclamationTriangleIcon className="w-4 h-4 shrink-0 mt-0.5 text-amber-600 dark:text-amber-400" />
            <span>
              Pacing alert: Increase savings by{' '}
              <strong className="tabular-nums font-semibold">
                {formatAmount(
                  goal.required_monthly_savings_minor -
                    (goal.monthly_contribution_planned_minor || 0),
                  'INR'
                )}
                /mo
              </strong>{' '}
              to reach target date ({goal.target_date}).
            </span>
          </div>
        )}
      </div>

      {/* Footer Action: Add Savings */}
      <div className="pt-2 border-t border-hairline">
        <button
          onClick={() => onUpdateProgress(goal)}
          className="w-full py-1.5 border border-hairline bg-surface hover:bg-canvas text-content-primary font-medium text-xs rounded-lg transition-colors flex items-center justify-center gap-1.5 cursor-pointer"
        >
          <PlusIcon className="w-3.5 h-3.5 text-[#4F46E5] dark:text-[#818CF8]" />
          <span>Update Balance / Add Deposit</span>
        </button>
      </div>
    </div>
  )
}
