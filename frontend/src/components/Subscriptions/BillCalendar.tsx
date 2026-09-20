import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import {
  CalendarDaysIcon,
  ClockIcon,
  ArrowRightIcon,
  CheckCircleIcon,
} from '@heroicons/react/24/outline'
import { getUpcomingObligations } from '../../api/subscriptions'
import type { UpcomingObligationsResponse } from '../../types'

export function BillCalendar() {
  const [data, setData] = useState<UpcomingObligationsResponse | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    setIsLoading(true)
    getUpcomingObligations(30)
      .then(setData)
      .catch((err) => console.error('Failed to load upcoming commitments:', err))
      .finally(() => setIsLoading(false))
  }, [])

  if (isLoading) {
    return (
      <div className="rounded-xl border border-hairline p-5 bg-surface text-center text-xs text-content-muted">
        Loading 30-day bill calendar...
      </div>
    )
  }

  if (!data || data.items.length === 0) {
    return (
      <div className="rounded-xl border border-hairline p-6 bg-surface text-center space-y-2">
        <CheckCircleIcon className="w-7 h-7 text-emerald-500 mx-auto" />
        <h4 className="text-xs font-semibold text-content-primary">
          No Bills Due in Next 30 Days
        </h4>
        <p className="text-[11px] text-content-muted">
          All regular recurring commitments and subscriptions are up to date.
        </p>
      </div>
    )
  }

  return (
    <div className="rounded-xl border border-hairline p-5 bg-surface space-y-4">
      {/* Calendar Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 border-b border-hairline pb-3">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-canvas border border-hairline flex items-center justify-center text-content-muted">
            <CalendarDaysIcon className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-content-primary">
              30-Day Scheduled Commitments Timeline
            </h3>
            <p className="text-[11px] text-content-muted">
              Upcoming automated debits, EMIs, and renewal dates
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-[11px] text-content-muted">Committed Outflow:</span>
          <span className="font-semibold tabular-nums text-content-primary text-xs px-2.5 py-0.5 rounded-md bg-canvas border border-hairline">
            {data.total_upcoming_display}
          </span>
        </div>
      </div>

      {/* Timeline Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {data.items.map((item) => {
          const isDueSoon = item.days_until_due <= 5
          return (
            <div
              key={item.id}
              className={`p-3.5 rounded-lg border transition-colors flex flex-col justify-between space-y-2.5 ${
                isDueSoon
                  ? 'bg-amber-500/5 border-amber-500/20'
                  : 'bg-canvas border-hairline'
              }`}
            >
              <div className="flex items-start justify-between gap-2">
                <span className="font-medium text-content-primary text-xs truncate">
                  {item.merchant}
                </span>
                <span
                  className={`px-1.5 py-0.5 rounded text-[10px] font-medium uppercase tracking-wider ${
                    isDueSoon
                      ? 'bg-amber-500/10 text-amber-700 dark:text-amber-400 border border-amber-500/20'
                      : 'bg-surface text-content-muted border border-hairline'
                  }`}
                >
                  {item.days_until_due === 0
                    ? 'Due Today'
                    : `In ${item.days_until_due}d`}
                </span>
              </div>

              <div className="flex items-baseline justify-between">
                <span className="text-base font-semibold tabular-nums text-content-primary">
                  {item.amount_display}
                </span>
                <span className="text-[10px] text-content-muted capitalize">
                  {item.frequency}
                </span>
              </div>

              <div className="pt-2 border-t border-hairline flex items-center justify-between text-[11px] text-content-muted">
                <span className="flex items-center gap-1 tabular-nums">
                  <ClockIcon className="w-3 h-3" />
                  {item.due_date}
                </span>
                <Link
                  to={`/transactions?q=${encodeURIComponent(item.merchant)}`}
                  className="font-medium text-[#4F46E5] dark:text-[#818CF8] hover:underline flex items-center gap-0.5"
                >
                  <span>History</span>
                  <ArrowRightIcon className="w-2.5 h-2.5" />
                </Link>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
