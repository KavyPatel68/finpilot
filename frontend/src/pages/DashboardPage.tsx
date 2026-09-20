import React, { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  ArrowPathIcon,
  ChevronRightIcon,
  ArrowTrendingUpIcon,
  TagIcon,
  BellAlertIcon,
} from '@heroicons/react/24/outline'
import { useMonth } from '../context/MonthContext'
import { getMonthlySummary, regenerateSummary, getSpendingTrends } from '../api/summary'
import { getInsights } from '../api/insights'
import type { MonthlySummary, Insight, SpendingTrendItem } from '../types'
import { LoadingSpinner } from '../components/common/LoadingSpinner'
import { SummaryCards } from '../components/Dashboard/SummaryCards'
import { CategoryPieChart } from '../components/Dashboard/CategoryPieChart'
import { TrendLineChart } from '../components/Dashboard/TrendLineChart'
import { formatAmount } from '../utils/currency'

export function DashboardPage() {
  const { selectedMonth, availableMonths } = useMonth()
  const [summary, setSummary] = useState<MonthlySummary | null>(null)
  const [insights, setInsights] = useState<Insight[]>([])
  const [trends, setTrends] = useState<SpendingTrendItem[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isRegenerating, setIsRegenerating] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    if (!selectedMonth) return
    setIsLoading(true)

    Promise.all([
      getMonthlySummary(selectedMonth),
      getInsights({ month: selectedMonth }),
      getSpendingTrends(6),
    ])
      .then(([summaryData, insightsData, trendsData]) => {
        setSummary(summaryData)
        setInsights(insightsData)
        setTrends(trendsData)
      })
      .catch((err) => console.error('Failed to load dashboard data:', err))
      .finally(() => setIsLoading(false))
  }, [selectedMonth])

  const handleRegenerate = async () => {
    if (!selectedMonth) return
    setIsRegenerating(true)
    try {
      const refreshed = await regenerateSummary(selectedMonth)
      setSummary(refreshed)
      const freshInsights = await getInsights({ month: selectedMonth })
      setInsights(freshInsights)
    } catch (err) {
      console.error('Failed to regenerate summary:', err)
    } finally {
      setIsRegenerating(false)
    }
  }

  const payload = summary?.payload

  // Derive top 2-3 concise insight action items
  const displayInsights = (insights || []).slice(0, 3)

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-baseline sm:justify-between gap-2 pb-2">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-[#1C1917] dark:text-[#EDEDEF]">
            Dashboard
          </h1>
          <p className="text-xs text-[#78716C] dark:text-[#8B8B95] mt-0.5">
            Cash flow trajectory, automated patterns, and spending intelligence
          </p>
        </div>

        <button
          onClick={handleRegenerate}
          disabled={isRegenerating || !selectedMonth}
          className="self-start sm:self-auto inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-lg border border-[#E7E5E4] dark:border-[#232329] bg-[#FFFFFF] dark:bg-[#131318] text-[#78716C] dark:text-[#8B8B95] hover:text-[#1C1917] dark:hover:text-[#EDEDEF] transition-colors disabled:opacity-50"
        >
          <ArrowPathIcon className={`w-3.5 h-3.5 ${isRegenerating ? 'animate-spin' : ''}`} />
          <span>{isRegenerating ? 'Refreshing...' : 'Refresh'}</span>
        </button>
      </div>

      {isLoading ? (
        <div className="py-20 flex flex-col items-center justify-center">
          <LoadingSpinner />
          <p className="mt-3 text-xs text-[#78716C] dark:text-[#8B8B95]">Loading financial metrics...</p>
        </div>
      ) : !payload ? (
        <div className="rounded-xl border border-[#E7E5E4] dark:border-[#232329] p-12 text-center bg-[#FFFFFF] dark:bg-[#131318]">
          <h3 className="text-sm font-semibold text-[#1C1917] dark:text-[#EDEDEF]">No Data Available</h3>
          <p className="text-xs text-[#78716C] dark:text-[#8B8B95] mt-1 max-w-sm mx-auto">
            Upload your first bank statement to generate insights and cash flow metrics.
          </p>
          <button
            onClick={() => navigate('/upload')}
            className="mt-4 px-3.5 py-1.5 text-xs font-medium bg-[#4F46E5] text-white rounded-lg hover:bg-[#4338CA] transition-colors"
          >
            Upload Statement
          </button>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Hero Row: 4 KPIs without boxes */}
          <SummaryCards payload={payload} trends={trends} />

          {/* Actionable Insights Strip: 2-3 short cards */}
          {displayInsights.length > 0 && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {displayInsights.map((insight) => (
                <div
                  key={insight.id}
                  className="rounded-xl border border-[#E7E5E4] dark:border-[#232329] p-3.5 bg-[#FFFFFF] dark:bg-[#131318] flex items-start gap-3 transition-colors"
                >
                  <div className="p-1.5 rounded-lg bg-[#FAFAF9] dark:bg-[#1A1A22] border border-[#E7E5E4] dark:border-[#232329] text-[#4F46E5] dark:text-[#818CF8] shrink-0 mt-0.5">
                    {insight.type?.includes('subscription') || insight.type?.includes('hike') ? (
                      <ArrowTrendingUpIcon className="w-4 h-4" />
                    ) : insight.type?.includes('alert') ? (
                      <BellAlertIcon className="w-4 h-4" />
                    ) : (
                      <TagIcon className="w-4 h-4" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs text-[#1C1917] dark:text-[#EDEDEF] leading-relaxed line-clamp-2">
                      {insight.text}
                    </p>
                    <Link
                      to={
                        insight.type?.includes('subscription')
                          ? '/subscriptions'
                          : insight.type?.includes('budget')
                          ? '/budgets'
                          : '/transactions'
                      }
                      className="inline-flex items-center gap-1 text-[11px] font-medium text-[#4F46E5] dark:text-[#818CF8] mt-1.5 hover:underline"
                    >
                      <span>Review</span>
                      <ChevronRightIcon className="w-3 h-3" />
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Charts & Breakdown Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
            {/* Cash Flow Trajectory (7 cols) */}
            <div className="lg:col-span-7">
              <TrendLineChart initialMonths={6} />
            </div>

            {/* Spending by Category (5 cols) */}
            <div className="lg:col-span-5">
              <CategoryPieChart
                categories={payload.top_categories || []}
                totalExpenseMinor={payload.expense_minor}
              />
            </div>
          </div>

          {/* Top Payees List */}
          {payload.top_merchants && payload.top_merchants.length > 0 && (
            <div className="rounded-xl border border-[#E7E5E4] dark:border-[#232329] p-5 bg-[#FFFFFF] dark:bg-[#131318]">
              <div className="flex items-center justify-between border-b border-[#E7E5E4] dark:border-[#232329] pb-3 mb-3">
                <div>
                  <h3 className="text-sm font-semibold tracking-tight text-[#1C1917] dark:text-[#EDEDEF]">
                    Top Outflow Payees
                  </h3>
                  <p className="text-xs text-[#78716C] dark:text-[#8B8B95] mt-0.5">
                    Largest payment recipients this period
                  </p>
                </div>
                <Link
                  to="/transactions"
                  className="text-xs font-medium text-[#4F46E5] dark:text-[#818CF8] hover:underline"
                >
                  View all
                </Link>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                {payload.top_merchants.slice(0, 8).map((merch) => {
                  const initial = merch.merchant.charAt(0).toUpperCase() || 'M'
                  return (
                    <div
                      key={merch.merchant}
                      onClick={() =>
                        navigate(`/transactions?search=${encodeURIComponent(merch.merchant)}`)
                      }
                      className="p-3 rounded-lg border border-[#E7E5E4] dark:border-[#232329] bg-[#FAFAF9] dark:bg-[#18181F] hover:bg-[#F5F5F4] dark:hover:bg-[#1F1F27] transition-colors cursor-pointer flex items-center justify-between gap-2.5"
                    >
                      <div className="flex items-center gap-2.5 min-w-0">
                        <div className="w-7 h-7 rounded-full bg-[#E7E5E4] dark:bg-[#232329] text-[#1C1917] dark:text-[#EDEDEF] text-xs font-medium flex items-center justify-center shrink-0">
                          {initial}
                        </div>
                        <div className="truncate">
                          <p className="text-xs font-medium text-[#1C1917] dark:text-[#EDEDEF] truncate">
                            {merch.merchant}
                          </p>
                          <p className="text-[10px] text-[#78716C] dark:text-[#8B8B95]">
                            {merch.transaction_count} transaction{merch.transaction_count > 1 ? 's' : ''}
                          </p>
                        </div>
                      </div>
                      <span className="text-xs font-medium text-[#1C1917] dark:text-[#EDEDEF] tabular-nums font-sans shrink-0">
                        {merch.amount_display}
                      </span>
                    </div>
                  )
                })}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
