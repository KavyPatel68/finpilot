import React from 'react'
import { Link } from 'react-router-dom'
import {
  ArrowTrendingUpIcon,
  ExclamationTriangleIcon,
  ArrowRightIcon,
  CheckCircleIcon,
  XCircleIcon,
} from '@heroicons/react/24/outline'
import type { RecurringGroup, RecurringStatus, PriceHikeItem } from '../../types'
import { formatAmount } from '../../utils/currency'

interface SubscriptionListProps {
  subscriptions: RecurringGroup[]
  priceHikes?: PriceHikeItem[]
  onStatusChange: (id: number, newStatus: RecurringStatus) => Promise<void>
  isUpdatingId?: number | null
}

export function SubscriptionList({
  subscriptions,
  priceHikes = [],
  onStatusChange,
  isUpdatingId,
}: SubscriptionListProps) {
  if (!subscriptions || subscriptions.length === 0) {
    return (
      <div className="text-center py-16 text-xs text-content-muted bg-surface rounded-xl border border-hairline">
        No recurring subscriptions or bills found matching the selected filter.
      </div>
    )
  }

  // Create lookup for price hikes by merchant
  const hikeMap = new Map<string, PriceHikeItem>()
  priceHikes.forEach((h) => hikeMap.set(h.merchant.toLowerCase(), h))

  const getStatusBadge = (status: RecurringStatus) => {
    switch (status) {
      case 'active':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium uppercase tracking-wider bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-500/20">
            <CheckCircleIcon className="w-3 h-3" /> Active
          </span>
        )
      case 'possibly_cancelled':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium uppercase tracking-wider bg-amber-500/10 text-amber-700 dark:text-amber-400 border border-amber-500/20">
            <ExclamationTriangleIcon className="w-3 h-3" /> Overdue
          </span>
        )
      case 'cancelled':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium uppercase tracking-wider bg-canvas text-content-muted border border-hairline">
            <XCircleIcon className="w-3 h-3" /> Cancelled
          </span>
        )
      default:
        return (
          <span className="px-2 py-0.5 rounded-full text-[10px] font-medium uppercase tracking-wider bg-canvas text-content-muted border border-hairline">
            {status}
          </span>
        )
    }
  }

  const getTypeBadge = (type: string) => {
    switch (type) {
      case 'subscription':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-medium uppercase tracking-wider bg-canvas text-content-muted border border-hairline">
            Subscription
          </span>
        )
      case 'emi':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-medium uppercase tracking-wider bg-amber-500/10 text-amber-700 dark:text-amber-400 border border-amber-500/20">
            EMI / Loan
          </span>
        )
      case 'bill':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-medium uppercase tracking-wider bg-[#4F46E5]/10 text-[#4F46E5] dark:text-[#818CF8] border border-[#4F46E5]/20">
            Utility Bill
          </span>
        )
      default:
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-medium uppercase tracking-wider bg-canvas text-content-muted border border-hairline">
            Recurring
          </span>
        )
    }
  }

  return (
    <div className="rounded-xl border border-hairline bg-surface overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-xs text-left">
          <thead className="bg-canvas text-content-muted font-medium border-b border-hairline">
            <tr>
              <th className="px-5 py-3">Merchant & Service</th>
              <th className="px-4 py-3">Type</th>
              <th className="px-4 py-3">Interval</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Next Renewal</th>
              <th className="px-5 py-3 text-right">Recurring Cost</th>
              <th className="px-4 py-3 text-center w-28">Action</th>
            </tr>
          </thead>

          <tbody className="divide-y divide-hairline text-content-primary">
            {subscriptions.map((sub) => {
              const isUpdating = isUpdatingId === sub.id
              const isCancelled = sub.status === 'cancelled'
              const hike = hikeMap.get(sub.merchant.toLowerCase())

              return (
                <tr
                  key={sub.id}
                  className="hover:bg-canvas/50 transition-colors"
                >
                  {/* Merchant & Price Hike Pill */}
                  <td className="px-5 py-3.5">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-content-primary">
                        {sub.merchant}
                      </span>

                      {/* Price hike detected badge */}
                      {hike && (
                        <span
                          title={`Price increase detected: ${hike.previous_amount_display} → ${hike.new_amount_display} (+${hike.difference_display})`}
                          className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium bg-rose-500/10 text-rose-700 dark:text-rose-400 border border-rose-500/20"
                        >
                          <ArrowTrendingUpIcon className="w-3 h-3" />
                          <span>+{hike.difference_display}</span>
                        </span>
                      )}
                    </div>

                    <div className="text-[11px] text-content-muted mt-0.5 flex items-center gap-2">
                      <span>Last charge: {sub.last_seen}</span>
                      <span>•</span>
                      <Link
                        to={`/transactions?q=${encodeURIComponent(sub.merchant)}`}
                        className="text-[#4F46E5] dark:text-[#818CF8] hover:underline flex items-center gap-0.5"
                      >
                        <span>View history</span>
                        <ArrowRightIcon className="w-2.5 h-2.5" />
                      </Link>
                    </div>
                  </td>

                  {/* Type */}
                  <td className="px-4 py-3.5 whitespace-nowrap">{getTypeBadge(sub.type)}</td>

                  {/* Interval */}
                  <td className="px-4 py-3.5 whitespace-nowrap capitalize text-content-muted font-medium">
                    {sub.frequency}
                  </td>

                  {/* Status */}
                  <td className="px-4 py-3.5 whitespace-nowrap">{getStatusBadge(sub.status)}</td>

                  {/* Next Expected with Inter tabular nums */}
                  <td className="px-4 py-3.5 whitespace-nowrap tabular-nums text-content-muted">
                    {sub.next_expected_date || '—'}
                  </td>

                  {/* Cost with Inter tabular nums */}
                  <td className="px-5 py-3.5 text-right whitespace-nowrap">
                    <div className="font-medium tabular-nums text-content-primary text-sm">
                      {formatAmount(sub.avg_amount_minor, 'INR')}
                    </div>
                    {sub.frequency !== 'monthly' && (
                      <div className="text-[11px] text-content-muted tabular-nums">
                        ≈ {formatAmount(sub.monthly_cost_minor, 'INR')}/mo
                      </div>
                    )}
                  </td>

                  {/* Actions */}
                  <td className="px-4 py-3.5 text-center whitespace-nowrap">
                    <button
                      onClick={() =>
                        onStatusChange(sub.id, isCancelled ? 'active' : 'cancelled')
                      }
                      disabled={isUpdating}
                      className={`text-xs font-medium px-2.5 py-1 rounded-md transition-colors ${
                        isCancelled
                          ? 'text-[#4F46E5] dark:text-[#818CF8] hover:underline'
                          : 'text-content-muted hover:text-rose-600 dark:hover:text-rose-400'
                      }`}
                    >
                      {isUpdating
                        ? 'Saving...'
                        : isCancelled
                        ? 'Reactivate'
                        : 'Mark Cancelled'}
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
