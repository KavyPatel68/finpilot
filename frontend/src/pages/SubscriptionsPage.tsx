import React, { useState, useEffect, useMemo } from 'react'
import {
  getSubscriptions,
  getPriceHikes,
  triggerRecurringDetection,
  updateSubscriptionStatus,
} from '../api/subscriptions'
import type { RecurringGroup, RecurringStatus, PriceHikeItem } from '../types'
import { SubscriptionList } from '../components/Subscriptions/SubscriptionList'
import { BillCalendar } from '../components/Subscriptions/BillCalendar'
import { LoadingSpinner } from '../components/common/LoadingSpinner'
import { formatAmount } from '../utils/currency'
import {
  ArrowPathIcon,
  ArrowTrendingUpIcon,
  SparklesIcon,
} from '@heroicons/react/24/outline'

export function SubscriptionsPage() {
  const [subscriptions, setSubscriptions] = useState<RecurringGroup[]>([])
  const [priceHikes, setPriceHikes] = useState<PriceHikeItem[]>([])
  const [selectedStatus, setSelectedStatus] = useState<string>('all')
  const [isLoading, setIsLoading] = useState(false)
  const [isDetecting, setIsDetecting] = useState(false)
  const [updatingId, setUpdatingId] = useState<number | null>(null)
  const [toastMessage, setToastMessage] = useState<string | null>(null)

  const loadData = async () => {
    setIsLoading(true)
    try {
      const [subsData, hikesData] = await Promise.all([
        getSubscriptions(),
        getPriceHikes().catch(() => []),
      ])
      setSubscriptions(subsData)
      setPriceHikes(hikesData)
    } catch (err) {
      console.error('Failed to load subscriptions data:', err)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  const handleDetect = async () => {
    setIsDetecting(true)
    try {
      const res = await triggerRecurringDetection()
      setToastMessage(res.message || 'Recurring charges scan completed.')
      await loadData()
      setTimeout(() => setToastMessage(null), 5000)
    } catch (err) {
      alert('Failed to detect subscriptions')
    } finally {
      setIsDetecting(false)
    }
  }

  const handleStatusChange = async (id: number, newStatus: RecurringStatus) => {
    setUpdatingId(id)
    try {
      const updated = await updateSubscriptionStatus(id, newStatus)
      setSubscriptions((prev) => prev.map((s) => (s.id === id ? updated : s)))
      setToastMessage(`Updated ${updated.merchant} to ${newStatus}.`)
      setTimeout(() => setToastMessage(null), 4000)
    } catch (err) {
      alert('Failed to update subscription status')
    } finally {
      setUpdatingId(null)
    }
  }

  // Filtered subscriptions
  const filteredSubscriptions = useMemo(() => {
    if (selectedStatus === 'all') return subscriptions
    return subscriptions.filter((s) => s.status === selectedStatus)
  }, [subscriptions, selectedStatus])

  // Aggregate metrics
  const metrics = useMemo(() => {
    let monthlyActiveCost = 0
    let activeCount = 0
    let overdueCount = 0

    for (const sub of subscriptions) {
      if (sub.status === 'active') {
        activeCount++
        if (sub.monthly_cost_minor) {
          monthlyActiveCost += sub.monthly_cost_minor
        } else {
          // Normalize to monthly equivalent fallback
          if (sub.frequency === 'weekly') {
            monthlyActiveCost += sub.avg_amount_minor * 4
          } else if (sub.frequency === 'quarterly') {
            monthlyActiveCost += Math.round(sub.avg_amount_minor / 3)
          } else if (sub.frequency === 'yearly') {
            monthlyActiveCost += Math.round(sub.avg_amount_minor / 12)
          } else {
            monthlyActiveCost += sub.avg_amount_minor
          }
        }
      } else if (sub.status === 'possibly_cancelled') {
        overdueCount++
      }
    }

    const annualActiveCost = monthlyActiveCost * 12

    return {
      monthlyActiveCost,
      annualActiveCost,
      activeCount,
      overdueCount,
    }
  }, [subscriptions])

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-2 border-b border-hairline">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-semibold tracking-tight text-content-primary">
              Subscriptions & Commitments
            </h1>
            <span className="px-2 py-0.5 rounded-full text-[10px] font-medium uppercase tracking-wider bg-canvas border border-hairline text-content-muted">
              Auto-Tracked
            </span>
          </div>
          <p className="text-xs text-content-muted mt-1">
            Track automated subscriptions, EMIs, and recurring utility bills with cadence detection and price increase alerts.
          </p>
        </div>

        <button
          onClick={handleDetect}
          disabled={isDetecting}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 border border-hairline bg-surface hover:bg-canvas text-content-primary text-xs font-medium rounded-lg transition-colors disabled:opacity-40 self-start sm:self-auto"
        >
          <ArrowPathIcon className={`w-3.5 h-3.5 text-[#4F46E5] dark:text-[#818CF8] ${isDetecting ? 'animate-spin' : ''}`} />
          <span>{isDetecting ? 'Scanning...' : 'Re-scan Recurring'}</span>
        </button>
      </div>

      {/* Toast Notification */}
      {toastMessage && (
        <div className="bg-emerald-500/8 border border-emerald-500/20 text-emerald-800 dark:text-emerald-300 text-xs px-4 py-2.5 rounded-lg flex items-center justify-between transition-colors">
          <div className="flex items-center gap-2">
            <SparklesIcon className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
            <span>{toastMessage}</span>
          </div>
          <button
            onClick={() => setToastMessage(null)}
            className="font-medium ml-2 hover:opacity-75"
          >
            ✕
          </button>
        </div>
      )}

      {/* Summary KPI Stats (Zero-box style or clean hairline row) */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 py-2">
        <div className="space-y-1">
          <span className="text-[11px] font-medium text-content-muted block">
            Monthly Fixed
          </span>
          <div className="text-2xl font-semibold tabular-nums text-content-primary">
            {formatAmount(metrics.monthlyActiveCost, 'INR')}
          </div>
          <p className="text-[11px] text-content-muted">Normalized run-rate</p>
        </div>

        <div className="space-y-1 sm:border-l sm:border-hairline sm:pl-4">
          <span className="text-[11px] font-medium text-content-muted block">
            Annualized Cost
          </span>
          <div className="text-2xl font-semibold tabular-nums text-content-primary">
            {formatAmount(metrics.annualActiveCost, 'INR')}
          </div>
          <p className="text-[11px] text-content-muted">Yearly committed outflow</p>
        </div>

        <div className="space-y-1 lg:border-l lg:border-hairline lg:pl-4">
          <span className="text-[11px] font-medium text-content-muted block">
            Active Plans
          </span>
          <div className="text-2xl font-semibold tabular-nums text-content-primary">
            {metrics.activeCount}
          </div>
          <p className="text-[11px] text-content-muted">Regular subscriptions</p>
        </div>

        <div className="space-y-1 border-l border-hairline pl-4">
          <span className="text-[11px] font-medium text-content-muted block">
            Needs Review
          </span>
          <div className="text-2xl font-semibold tabular-nums text-amber-600 dark:text-amber-400">
            {metrics.overdueCount}
          </div>
          <p className="text-[11px] text-content-muted">Overdue or lapsed renewals</p>
        </div>
      </div>

      {/* Price Hike Alert Banner */}
      {priceHikes.length > 0 && (
        <div className="rounded-xl border border-rose-500/20 bg-rose-500/5 p-4 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <ArrowTrendingUpIcon className="w-4 h-4 text-rose-600 dark:text-rose-400" />
              <h4 className="text-xs font-semibold text-rose-900 dark:text-rose-200">
                Price Increase Detected ({priceHikes.length})
              </h4>
            </div>
            <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-rose-500/10 text-rose-700 dark:text-rose-300 border border-rose-500/20">
              Action Recommended
            </span>
          </div>
          <p className="text-[11px] text-rose-800/80 dark:text-rose-300/80">
            FinPilot noticed increases in regular subscription billing amounts compared to previous cycles:
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5 pt-1">
            {priceHikes.map((hike, idx) => (
              <div
                key={idx}
                className="p-3 rounded-lg bg-surface border border-hairline text-xs space-y-1"
              >
                <div className="flex items-center justify-between font-medium text-content-primary">
                  <span>{hike.merchant}</span>
                  <span className="text-rose-600 dark:text-rose-400 font-semibold tabular-nums">
                    +{hike.difference_display}
                  </span>
                </div>
                <div className="text-[11px] text-content-muted tabular-nums flex items-center justify-between">
                  <span>{hike.previous_amount_display} → {hike.new_amount_display}</span>
                  <span className="text-[10px] text-content-muted">{hike.effective_date}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 30-Day Upcoming Bill Calendar */}
      <BillCalendar />

      {/* Status Filter Tabs & Table Section */}
      <div className="space-y-3">
        <div className="flex items-center justify-between border-b border-hairline pb-2">
          <div className="flex items-center gap-1.5 text-xs font-medium overflow-x-auto">
            {[
              { key: 'all', label: 'All Commitments', count: subscriptions.length },
              { key: 'active', label: 'Active', count: metrics.activeCount },
              { key: 'possibly_cancelled', label: 'Needs Review', count: metrics.overdueCount },
              {
                key: 'cancelled',
                label: 'Cancelled',
                count: subscriptions.filter((s) => s.status === 'cancelled').length,
              },
            ].map((tab) => (
              <button
                key={tab.key}
                onClick={() => setSelectedStatus(tab.key)}
                className={`px-3 py-1.5 rounded-lg transition-colors font-medium flex items-center gap-1.5 ${
                  selectedStatus === tab.key
                    ? 'bg-[#4F46E5]/10 text-[#4F46E5] dark:text-[#818CF8] border border-[#4F46E5]/20'
                    : 'text-content-muted hover:text-content-primary hover:bg-canvas'
                }`}
              >
                <span>{tab.label}</span>
                <span className="text-[10px] tabular-nums opacity-80">
                  ({tab.count})
                </span>
              </button>
            ))}
          </div>
        </div>

        {/* Subscription List or Loader */}
        {isLoading ? (
          <div className="p-16 flex justify-center bg-surface rounded-xl border border-hairline">
            <LoadingSpinner />
          </div>
        ) : (
          <SubscriptionList
            subscriptions={filteredSubscriptions}
            priceHikes={priceHikes}
            onStatusChange={handleStatusChange}
            isUpdatingId={updatingId}
          />
        )}
      </div>

      {/* Advisory Regulatory Disclaimer */}
      <div className="text-center pt-2">
        <p className="text-[11px] text-content-muted">
          Advisory notice: FinPilot subscription tracking and renewal forecasts are computed solely from transaction pattern heuristics. FinPilot is not a SEBI-registered advisor and does not execute automated mandate cancellations or debits.
        </p>
      </div>
    </div>
  )
}
