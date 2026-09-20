import React, { useState, useEffect, useMemo } from 'react'
import { getBudgets, createBudget, updateBudget, deleteBudget } from '../api/budgets'
import { getCategories } from '../api/transactions'
import { useMonth } from '../context/MonthContext'
import type { Budget } from '../types'
import { BudgetProgressBar } from '../components/Budgets/BudgetProgressBar'
import { LoadingSpinner } from '../components/common/LoadingSpinner'
import { formatAmount } from '../utils/currency'
import {
  PlusIcon,
  CalendarDaysIcon,
  BanknotesIcon,
  SparklesIcon,
} from '@heroicons/react/24/outline'

export function BudgetsPage() {
  const { selectedMonth, setSelectedMonth, availableMonths } = useMonth()
  const [budgets, setBudgets] = useState<Budget[]>([])
  const [categories, setCategories] = useState<string[]>([])
  const [selectedFilter, setSelectedFilter] = useState<'all' | 'exceeded' | 'warning' | 'on_track'>('all')
  const [isLoading, setIsLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editingBudget, setEditingBudget] = useState<Budget | null>(null)
  const [toastMessage, setToastMessage] = useState<string | null>(null)

  // Form states
  const [formCategory, setFormCategory] = useState('')
  const [formLimitRupees, setFormLimitRupees] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Load categories
  useEffect(() => {
    getCategories()
      .then((cats) => {
        setCategories(cats)
        if (cats.length > 0) setFormCategory(cats[0])
      })
      .catch((err) => console.error('Failed to load categories:', err))
  }, [])

  const loadBudgets = async () => {
    setIsLoading(true)
    try {
      const data = await getBudgets(selectedMonth || undefined)
      setBudgets(data)
    } catch (err) {
      console.error('Failed to load budgets:', err)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    loadBudgets()
  }, [selectedMonth])

  // Aggregate totals
  const summaryTotals = useMemo(() => {
    let totalLimit = 0
    let totalSpent = 0
    let exceededCount = 0
    let warningCount = 0
    let onTrackCount = 0

    for (const b of budgets) {
      totalLimit += b.monthly_limit_minor
      const spent = b.spent_minor || 0
      totalSpent += spent

      if (b.status === 'exceeded' || (b.spent_pct && b.spent_pct > 100)) {
        exceededCount++
      } else if (b.status === 'warning' || (b.spent_pct && b.spent_pct >= 80)) {
        warningCount++
      } else {
        onTrackCount++
      }
    }

    const remaining = totalLimit - totalSpent
    const spentPct = totalLimit > 0 ? Math.round((totalSpent / totalLimit) * 100) : 0

    return {
      totalLimit,
      totalSpent,
      remaining,
      spentPct,
      exceededCount,
      warningCount,
      onTrackCount,
    }
  }, [budgets])

  // Filtered budgets
  const filteredBudgets = useMemo(() => {
    if (selectedFilter === 'all') return budgets
    if (selectedFilter === 'exceeded') {
      return budgets.filter((b) => b.status === 'exceeded' || (b.spent_pct && b.spent_pct > 100))
    }
    if (selectedFilter === 'warning') {
      return budgets.filter((b) => b.status === 'warning' || (b.spent_pct && b.spent_pct >= 80 && b.spent_pct <= 100))
    }
    return budgets.filter((b) => !b.status || b.status === 'on_track' || (b.spent_pct && b.spent_pct < 80))
  }, [budgets, selectedFilter])

  const handleOpenCreate = () => {
    setEditingBudget(null)
    const existingCats = new Set(budgets.map((b) => b.category))
    const firstAvailable = categories.find((c) => !existingCats.has(c)) || categories[0] || 'Dining'
    setFormCategory(firstAvailable)
    setFormLimitRupees('5000')
    setModalOpen(true)
  }

  const handleOpenEdit = (b: Budget) => {
    setEditingBudget(b)
    setFormCategory(b.category)
    setFormLimitRupees(String(b.monthly_limit_minor / 100))
    setModalOpen(true)
  }

  const handleInlineLimitSave = async (id: number, newLimitMinor: number) => {
    setBudgets((prev) =>
      prev.map((b) => {
        if (b.id !== id) return b
        const spent = b.spent_minor || 0
        const spentPct = newLimitMinor > 0 ? Math.round((spent / newLimitMinor) * 100) : 0
        const remaining = Math.max(0, newLimitMinor - spent)
        const status = spent > newLimitMinor ? 'exceeded' : spentPct >= 80 ? 'warning' : 'on_track'
        return {
          ...b,
          monthly_limit_minor: newLimitMinor,
          spent_pct: spentPct,
          remaining_minor: remaining,
          status,
        }
      })
    )

    try {
      await updateBudget(id, { monthly_limit_minor: newLimitMinor })
      setToastMessage('Budget limit updated.')
      setTimeout(() => setToastMessage(null), 3500)
    } catch (err) {
      alert('Failed to update limit on server, refreshing...')
      await loadBudgets()
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const limitMinor = Math.round(Number(formLimitRupees) * 100)
    if (!limitMinor || limitMinor <= 0) {
      alert('Please enter a valid budget amount in Rupees')
      return
    }

    setIsSubmitting(true)
    try {
      if (editingBudget) {
        await updateBudget(editingBudget.id, { monthly_limit_minor: limitMinor })
        setToastMessage(`Updated ${editingBudget.category} budget limit.`)
      } else {
        await createBudget({ category: formCategory, monthly_limit_minor: limitMinor })
        setToastMessage(`Set ${formCategory} budget to ₹${formLimitRupees}/mo.`)
      }
      setModalOpen(false)
      await loadBudgets()
      setTimeout(() => setToastMessage(null), 4000)
    } catch (err) {
      alert('Failed to save budget')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleDelete = async (id: number) => {
    const target = budgets.find((b) => b.id === id)
    if (!confirm(`Are you sure you want to remove the ${target?.category || ''} budget limit?`)) return

    try {
      await deleteBudget(id)
      setToastMessage('Budget limit removed.')
      await loadBudgets()
      setTimeout(() => setToastMessage(null), 3500)
    } catch (err) {
      alert('Failed to delete budget')
    }
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-2 border-b border-hairline">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-semibold tracking-tight text-content-primary">
              Category Budgets
            </h1>
            <span className="px-2 py-0.5 rounded-full text-[10px] font-medium uppercase tracking-wider bg-canvas border border-hairline text-content-muted">
              Guardrails
            </span>
          </div>
          <p className="text-xs text-content-muted mt-1">
            Establish discretionary spending guardrails with pacing projections, alert thresholds, and inline adjustment.
          </p>
        </div>

        <div className="flex items-center gap-2.5 self-start sm:self-auto">
          {availableMonths.length > 0 && (
            <div className="relative">
              <select
                value={selectedMonth}
                onChange={(e) => setSelectedMonth(e.target.value)}
                className="appearance-none pl-3 pr-8 py-1.5 rounded-lg text-xs font-medium bg-surface border border-hairline text-content-primary focus:outline-none focus:ring-1 focus:ring-[#4F46E5] cursor-pointer"
              >
                {availableMonths.map((m) => (
                  <option key={m} value={m}>
                    {new Date(`${m}-01`).toLocaleString('default', {
                      month: 'short',
                      year: 'numeric',
                    })}
                  </option>
                ))}
              </select>
              <CalendarDaysIcon className="w-3.5 h-3.5 text-content-muted absolute right-2.5 top-2 pointer-events-none" />
            </div>
          )}

          <button
            onClick={handleOpenCreate}
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 bg-[#4F46E5] hover:bg-[#4338CA] text-white text-xs font-medium rounded-lg transition-colors cursor-pointer"
          >
            <PlusIcon className="w-3.5 h-3.5" />
            <span>Set Budget</span>
          </button>
        </div>
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

      {/* Overview Stats (Zero-box style or clean hairline row) */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 py-2">
        <div className="space-y-1">
          <span className="text-[11px] font-medium text-content-muted block">
            Total Budgeted
          </span>
          <div className="text-2xl font-semibold tabular-nums text-content-primary">
            {formatAmount(summaryTotals.totalLimit, 'INR')}
          </div>
          <p className="text-[11px] text-content-muted">{budgets.length} monitored categories</p>
        </div>

        <div className="space-y-1 sm:border-l sm:border-hairline sm:pl-4">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-medium text-content-muted block">
              MTD Spend
            </span>
            <span className="text-[11px] tabular-nums font-semibold text-[#4F46E5] dark:text-[#818CF8]">
              {summaryTotals.spentPct}%
            </span>
          </div>
          <div className="text-2xl font-semibold tabular-nums text-[#4F46E5] dark:text-[#818CF8]">
            {formatAmount(summaryTotals.totalSpent, 'INR')}
          </div>
          <p className="text-[11px] text-content-muted">Aggregated outflow</p>
        </div>

        <div className="space-y-1 lg:border-l lg:border-hairline lg:pl-4">
          <span className="text-[11px] font-medium text-content-muted block">
            Remaining Buffer
          </span>
          <div
            className={`text-2xl font-semibold tabular-nums ${
              summaryTotals.remaining >= 0
                ? 'text-emerald-600 dark:text-emerald-400'
                : 'text-rose-600 dark:text-rose-400'
            }`}
          >
            {formatAmount(summaryTotals.remaining, 'INR')}
          </div>
          <p className="text-[11px] text-content-muted">
            {summaryTotals.remaining >= 0 ? 'Safe net cushion' : 'Net plan overage'}
          </p>
        </div>

        <div className="space-y-1 border-l border-hairline pl-4">
          <span className="text-[11px] font-medium text-content-muted block">
            Categories At Risk
          </span>
          <div className="text-2xl font-semibold tabular-nums flex items-baseline gap-2">
            <span
              className={
                summaryTotals.exceededCount > 0
                  ? 'text-rose-600 dark:text-rose-400'
                  : 'text-content-primary'
              }
            >
              {summaryTotals.exceededCount + summaryTotals.warningCount}
            </span>
            <span className="text-xs text-content-muted font-normal tabular-nums">
              ({summaryTotals.exceededCount} over, {summaryTotals.warningCount} near)
            </span>
          </div>
          <p className="text-[11px] text-content-muted">Exceeded or &gt;80% limit</p>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center justify-between border-b border-hairline pb-2">
        <div className="flex items-center gap-1.5 text-xs font-medium overflow-x-auto">
          {[
            { key: 'all' as const, label: 'All Categories', count: budgets.length },
            {
              key: 'exceeded' as const,
              label: 'Over Budget',
              count: summaryTotals.exceededCount,
            },
            {
              key: 'warning' as const,
              label: 'Near Limit (80%+)',
              count: summaryTotals.warningCount,
            },
            {
              key: 'on_track' as const,
              label: 'On Track',
              count: summaryTotals.onTrackCount,
            },
          ].map((tab) => (
            <button
              key={tab.key}
              onClick={() => setSelectedFilter(tab.key)}
              className={`px-3 py-1.5 rounded-lg transition-colors font-medium flex items-center gap-1.5 cursor-pointer ${
                selectedFilter === tab.key
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

      {/* Budgets Grid or Empty/Loading State */}
      {isLoading ? (
        <div className="p-16 flex justify-center bg-surface rounded-xl border border-hairline">
          <LoadingSpinner />
        </div>
      ) : budgets.length === 0 ? (
        <div className="bg-surface rounded-xl border border-hairline p-12 text-center space-y-3">
          <div className="w-10 h-10 rounded-lg bg-canvas border border-hairline text-content-muted flex items-center justify-center mx-auto">
            <BanknotesIcon className="w-5 h-5" />
          </div>
          <h3 className="text-sm font-semibold text-content-primary">
            No Category Budgets Configured
          </h3>
          <p className="text-xs text-content-muted max-w-sm mx-auto">
            Set spending guardrails on discretionary expenses like Dining, Shopping, or Groceries to monitor velocity and prevent overshooting.
          </p>
          <button
            onClick={handleOpenCreate}
            className="px-3.5 py-1.5 bg-[#4F46E5] hover:bg-[#4338CA] text-white text-xs font-medium rounded-lg transition-colors cursor-pointer"
          >
            Create Your First Budget
          </button>
        </div>
      ) : filteredBudgets.length === 0 ? (
        <div className="bg-surface rounded-xl border border-hairline p-10 text-center text-xs text-content-muted">
          No category budgets match the &quot;{selectedFilter}&quot; filter.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {filteredBudgets.map((b) => (
            <BudgetProgressBar
              key={b.id}
              budget={b}
              selectedMonth={selectedMonth}
              onEdit={handleOpenEdit}
              onDelete={handleDelete}
              onInlineLimitSave={handleInlineLimitSave}
            />
          ))}
        </div>
      )}

      {/* Create / Edit Modal */}
      {modalOpen && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-black/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-surface border border-hairline rounded-xl max-w-md w-full p-6 shadow-xl space-y-4 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-start justify-between border-b border-hairline pb-3">
              <div>
                <h2 className="text-sm font-semibold text-content-primary">
                  {editingBudget ? `Edit ${editingBudget.category} Budget` : 'Set Category Budget'}
                </h2>
                <p className="text-xs text-content-muted mt-0.5">
                  Monthly ceiling for discretionary spending
                </p>
              </div>
              <button
                onClick={() => setModalOpen(false)}
                className="text-content-muted hover:text-content-primary rounded p-1 text-sm font-semibold"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4 text-xs">
              <div>
                <label className="block font-medium text-content-primary mb-1">
                  Category
                </label>
                <select
                  disabled={editingBudget !== null}
                  value={formCategory}
                  onChange={(e) => setFormCategory(e.target.value)}
                  className="w-full rounded-lg border border-hairline bg-canvas text-content-primary px-3 py-2 text-xs focus:outline-none focus:ring-1 focus:ring-[#4F46E5] disabled:opacity-60"
                >
                  {categories.map((cat) => (
                    <option key={cat} value={cat}>
                      {cat}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block font-medium text-content-primary mb-1">
                  Monthly Limit (₹)
                </label>
                <div className="relative">
                  <span className="absolute left-3 top-2 text-content-muted text-xs">₹</span>
                  <input
                    type="number"
                    required
                    min="100"
                    step="100"
                    value={formLimitRupees}
                    onChange={(e) => setFormLimitRupees(e.target.value)}
                    placeholder="e.g. 10000"
                    className="w-full pl-7 pr-3 py-2 rounded-lg border border-hairline bg-canvas text-content-primary text-xs font-semibold tabular-nums focus:outline-none focus:ring-1 focus:ring-[#4F46E5]"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-2.5 pt-3 border-t border-hairline">
                <button
                  type="button"
                  onClick={() => setModalOpen(false)}
                  className="px-3.5 py-1.5 text-xs font-medium text-content-muted hover:text-content-primary rounded-lg border border-hairline hover:bg-canvas transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-4 py-1.5 text-xs font-medium bg-[#4F46E5] hover:bg-[#4338CA] text-white rounded-lg transition-colors disabled:opacity-40 cursor-pointer"
                >
                  {isSubmitting ? 'Saving...' : editingBudget ? 'Update Limit' : 'Save Budget'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Advisory Regulatory Notice */}
      <div className="text-center pt-2">
        <p className="text-[11px] text-content-muted">
          Advisory notice: FinPilot budget limits and spend velocity projections are personal monitoring benchmarks and do not block card transactions or banking operations. FinPilot is not a SEBI-registered advisor.
        </p>
      </div>
    </div>
  )
}
