import React from 'react'
import { formatAmount } from '../../utils/currency'
import type { SummaryPayload, SpendingTrendItem } from '../../types'

interface SummaryCardsProps {
  payload: SummaryPayload
  trends?: SpendingTrendItem[]
}

export function SummaryCards({ payload, trends = [] }: SummaryCardsProps) {
  // Sparkline data
  const expensePoints = trends.map((t) => t.expense_minor)
  const maxExpense = Math.max(...expensePoints, 1)
  const minExpense = Math.min(...expensePoints, 0)

  const incomePoints = trends.map((t) => t.income_minor)
  const maxIncome = Math.max(...incomePoints, 1)
  const minIncome = Math.min(...incomePoints, 0)

  const renderSparkline = (points: number[], min: number, max: number, strokeColor: string) => {
    if (points.length < 2) return null
    const width = 64
    const height = 20
    const range = max - min || 1
    const coords = points.map((val, idx) => {
      const x = (idx / (points.length - 1)) * width
      const y = height - ((val - min) / range) * (height - 4) - 2
      return `${x.toFixed(1)},${y.toFixed(1)}`
    })
    return (
      <svg width={width} height={height} className="overflow-visible shrink-0 opacity-70">
        <polyline
          fill="none"
          stroke={strokeColor}
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          points={coords.join(' ')}
        />
      </svg>
    )
  }

  const isNetPositive = payload.net_savings_minor >= 0
  const comparisonLabel = payload.is_partial_month ? 'vs same days last month' : 'vs last month'

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 divide-y lg:divide-y-0 lg:divide-x divide-[#E7E5E4] dark:divide-[#232329] border-y border-[#E7E5E4] dark:border-[#232329] py-5">
      {/* 1. Total Inflow */}
      <div className="px-4 first:pl-0">
        <span className="text-xs text-[#78716C] dark:text-[#8B8B95] font-medium">
          Total Inflow
        </span>
        <div className="mt-1.5 flex items-baseline justify-between gap-2">
          <span className="text-3xl font-medium tracking-tight text-[#1C1917] dark:text-[#EDEDEF] tabular-nums font-sans">
            {formatAmount(payload.income_minor, 'INR')}
          </span>
          {renderSparkline(incomePoints, minIncome, maxIncome, '#78716C')}
        </div>
        <p className="text-xs text-[#78716C] dark:text-[#8B8B95] mt-1.5">
          Salary & deposits
        </p>
      </div>

      {/* 2. Total Outflow */}
      <div className="px-4">
        <span className="text-xs text-[#78716C] dark:text-[#8B8B95] font-medium">
          Total Outflow
        </span>
        <div className="mt-1.5 flex items-baseline justify-between gap-2">
          <span className="text-3xl font-medium tracking-tight text-[#1C1917] dark:text-[#EDEDEF] tabular-nums font-sans">
            {formatAmount(payload.expense_minor, 'INR')}
          </span>
          {renderSparkline(expensePoints, minExpense, maxExpense, '#78716C')}
        </div>
        <div className="mt-1.5 flex flex-wrap items-center gap-1.5 text-xs">
          {payload.mom_change_pct !== null && (
            <span
              className={`inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded-full text-[11px] font-medium ${
                payload.mom_change_pct > 0
                  ? 'bg-[#E11D48]/10 text-[#E11D48] dark:bg-[#F43F5E]/10 dark:text-[#F43F5E]'
                  : 'bg-[#16A34A]/10 text-[#16A34A] dark:bg-[#22C55E]/10 dark:text-[#22C55E]'
              }`}
            >
              <span>{payload.mom_change_pct > 0 ? '↑' : '↓'}</span>
              <span>{Math.abs(payload.mom_change_pct)}%</span>
            </span>
          )}
          <span className="text-[#78716C] dark:text-[#8B8B95] text-[11px]">
            {payload.mom_change_pct !== null ? comparisonLabel : 'Monthly expenses'}
          </span>
        </div>
        {payload.transfers_minor !== undefined && payload.transfers_minor > 0 && (
          <p className="text-[11px] text-[#78716C] dark:text-[#8B8B95] mt-1">
            Transfers: {formatAmount(payload.transfers_minor, 'INR')} (excluded)
          </p>
        )}
      </div>

      {/* 3. Net Cash Flow */}
      <div className="px-4 pt-4 lg:pt-0">
        <span className="text-xs text-[#78716C] dark:text-[#8B8B95] font-medium">
          Net Cash Flow
        </span>
        <div className="mt-1.5 flex items-baseline justify-between gap-2">
          <span
            className={`text-3xl font-medium tracking-tight tabular-nums font-sans ${
              isNetPositive
                ? 'text-[#1C1917] dark:text-[#EDEDEF]'
                : 'text-[#E11D48] dark:text-[#F43F5E]'
            }`}
          >
            {formatAmount(payload.net_savings_minor, 'INR')}
          </span>
        </div>
        <div className="mt-1.5">
          <span
            className={`inline-flex items-center px-1.5 py-0.5 rounded-full text-[11px] font-medium ${
              isNetPositive
                ? 'bg-[#16A34A]/10 text-[#16A34A] dark:bg-[#22C55E]/10 dark:text-[#22C55E]'
                : 'bg-[#E11D48]/10 text-[#E11D48] dark:bg-[#F43F5E]/10 dark:text-[#F43F5E]'
            }`}
          >
            {isNetPositive ? 'Net Surplus' : 'Deficit'}
          </span>
        </div>
      </div>

      {/* 4. Savings Rate */}
      <div className="px-4 pt-4 lg:pt-0 last:pr-0">
        <span className="text-xs text-[#78716C] dark:text-[#8B8B95] font-medium">
          Savings Rate
        </span>
        <div className="mt-1.5 flex items-baseline justify-between gap-2">
          <span className="text-3xl font-medium tracking-tight text-[#1C1917] dark:text-[#EDEDEF] tabular-nums font-sans">
            {payload.savings_rate_pct}%
          </span>
        </div>
        <p className="text-xs text-[#78716C] dark:text-[#8B8B95] mt-1.5">
          {payload.savings_rate_pct >= 20 ? 'Target achieved (≥20%)' : 'Below 20% target'}
        </p>
      </div>
    </div>
  )
}
