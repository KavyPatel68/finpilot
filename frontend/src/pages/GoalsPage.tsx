import React, { useState, useEffect, useMemo } from 'react'
import { getGoals, createGoal, updateGoal, deleteGoal } from '../api/goals'
import type { Goal, GoalType } from '../types'
import { GoalCard } from '../components/Goals/GoalCard'
import { ScenarioSlider } from '../components/Goals/ScenarioSlider'
import { LoadingSpinner } from '../components/common/LoadingSpinner'
import { formatAmount } from '../utils/currency'
import {
  PlusIcon,
  SparklesIcon,
  TrophyIcon,
} from '@heroicons/react/24/outline'

export function GoalsPage() {
  const [goals, setGoals] = useState<Goal[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [selectedFilter, setSelectedFilter] = useState<'all' | 'on_track' | 'behind' | 'completed'>('all')
  const [toastMessage, setToastMessage] = useState<string | null>(null)

  // Create Goal Modal State
  const [createModalOpen, setCreateModalOpen] = useState(false)
  const [editingGoal, setEditingGoal] = useState<Goal | null>(null)
  const [name, setName] = useState('')
  const [goalType, setGoalType] = useState<GoalType>('emergency_fund')
  const [targetAmountRupees, setTargetAmountRupees] = useState('100000')
  const [currentAmountRupees, setCurrentAmountRupees] = useState('10000')
  const [targetDate, setTargetDate] = useState('')
  const [monthlyContributionRupees, setMonthlyContributionRupees] = useState('5000')
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Quick Deposit / Update Progress Modal State
  const [depositGoal, setDepositGoal] = useState<Goal | null>(null)
  const [depositAmountRupees, setDepositAmountRupees] = useState('')
  const [isDepositMode, setIsDepositMode] = useState<boolean>(true)
  const [isUpdatingProgress, setIsUpdatingProgress] = useState(false)

  const loadGoals = async () => {
    setIsLoading(true)
    try {
      const data = await getGoals()
      setGoals(data)
    } catch (err) {
      console.error('Failed to load goals:', err)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    loadGoals()
  }, [])

  const handleOpenCreate = () => {
    setEditingGoal(null)
    setName('')
    setGoalType('emergency_fund')
    setTargetAmountRupees('100000')
    setCurrentAmountRupees('10000')
    setTargetDate('')
    setMonthlyContributionRupees('5000')
    setCreateModalOpen(true)
  }

  const handleOpenEdit = (g: Goal) => {
    setEditingGoal(g)
    setName(g.name)
    setGoalType(g.type)
    setTargetAmountRupees(String(g.target_amount_minor / 100))
    setCurrentAmountRupees(String(g.current_amount_minor / 100))
    setTargetDate(g.target_date || '')
    setMonthlyContributionRupees(
      g.monthly_contribution_planned_minor
        ? String(g.monthly_contribution_planned_minor / 100)
        : ''
    )
    setCreateModalOpen(true)
  }

  const handleCreateOrUpdateSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsSubmitting(true)
    try {
      if (editingGoal) {
        await updateGoal(editingGoal.id, {
          name,
          type: goalType,
          target_amount_minor: Math.round(Number(targetAmountRupees) * 100),
          current_amount_minor: Math.round(Number(currentAmountRupees) * 100),
          target_date: targetDate || undefined,
          monthly_contribution_planned_minor: monthlyContributionRupees
            ? Math.round(Number(monthlyContributionRupees) * 100)
            : undefined,
        })
        setToastMessage(`Updated goal: ${name}`)
      } else {
        await createGoal({
          name,
          type: goalType,
          target_amount_minor: Math.round(Number(targetAmountRupees) * 100),
          current_amount_minor: Math.round(Number(currentAmountRupees) * 100),
          target_date: targetDate || undefined,
          monthly_contribution_planned_minor: monthlyContributionRupees
            ? Math.round(Number(monthlyContributionRupees) * 100)
            : undefined,
        })
        setToastMessage(`Created new goal: ${name}`)
      }
      setCreateModalOpen(false)
      await loadGoals()
      setTimeout(() => setToastMessage(null), 4000)
    } catch (err) {
      alert('Failed to save goal')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleOpenDeposit = (goal: Goal) => {
    setDepositGoal(goal)
    setDepositAmountRupees('5000')
    setIsDepositMode(true)
  }

  const handleDepositSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!depositGoal) return
    setIsUpdatingProgress(true)
    try {
      const enteredAmountMinor = Math.round(Number(depositAmountRupees) * 100)
      const newTotalMinor = isDepositMode
        ? depositGoal.current_amount_minor + enteredAmountMinor
        : enteredAmountMinor

      await updateGoal(depositGoal.id, { current_amount_minor: newTotalMinor })
      setToastMessage(
        isDepositMode
          ? `Added ₹${depositAmountRupees} to ${depositGoal.name}!`
          : `Updated balance for ${depositGoal.name}.`
      )
      setDepositGoal(null)
      await loadGoals()
      setTimeout(() => setToastMessage(null), 4000)
    } catch (err) {
      alert('Failed to update goal progress')
    } finally {
      setIsUpdatingProgress(false)
    }
  }

  const handleDelete = async (id: number) => {
    const target = goals.find((g) => g.id === id)
    if (!confirm(`Are you sure you want to remove the goal "${target?.name || ''}"?`)) return
    try {
      await deleteGoal(id)
      setToastMessage('Goal removed.')
      await loadGoals()
      setTimeout(() => setToastMessage(null), 3500)
    } catch (err) {
      alert('Failed to delete goal')
    }
  }

  // Aggregate metrics
  const metrics = useMemo(() => {
    let totalTarget = 0
    let totalSaved = 0
    let onTrackCount = 0
    let behindCount = 0
    let completedCount = 0

    for (const g of goals) {
      totalTarget += g.target_amount_minor
      totalSaved += g.current_amount_minor

      if (g.progress_pct >= 100) {
        completedCount++
      } else if (g.on_track === true) {
        onTrackCount++
      } else if (g.on_track === false) {
        behindCount++
      }
    }

    const fundingPct = totalTarget > 0 ? Math.round((totalSaved / totalTarget) * 100) : 0
    return { totalTarget, totalSaved, fundingPct, onTrackCount, behindCount, completedCount }
  }, [goals])

  // Filtered goals
  const filteredGoals = useMemo(() => {
    if (selectedFilter === 'all') return goals
    if (selectedFilter === 'completed') return goals.filter((g) => g.progress_pct >= 100)
    if (selectedFilter === 'on_track') return goals.filter((g) => g.on_track === true && g.progress_pct < 100)
    return goals.filter((g) => g.on_track === false && g.progress_pct < 100)
  }, [goals, selectedFilter])

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-2 border-b border-hairline">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-semibold tracking-tight text-content-primary">
              Savings Goals & Capital Milestones
            </h1>
            <span className="px-2 py-0.5 rounded-full text-[10px] font-medium uppercase tracking-wider bg-canvas border border-hairline text-content-muted">
              Milestones
            </span>
          </div>
          <p className="text-xs text-content-muted mt-1">
            Build emergency reserves and plan major purchases with progress rings and what-if acceleration simulations.
          </p>
        </div>

        <button
          onClick={handleOpenCreate}
          className="inline-flex items-center gap-1.5 px-3.5 py-1.5 bg-[#4F46E5] hover:bg-[#4338CA] text-white text-xs font-medium rounded-lg transition-colors cursor-pointer self-start sm:self-auto"
        >
          <PlusIcon className="w-3.5 h-3.5" />
          <span>Create New Goal</span>
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
            Target Capital
          </span>
          <div className="text-2xl font-semibold tabular-nums text-content-primary">
            {formatAmount(metrics.totalTarget, 'INR')}
          </div>
          <p className="text-[11px] text-content-muted">{goals.length} target milestones</p>
        </div>

        <div className="space-y-1 sm:border-l sm:border-hairline sm:pl-4">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-medium text-content-muted block">
              Accumulated
            </span>
            <span className="text-[11px] tabular-nums font-semibold text-emerald-600 dark:text-emerald-400">
              {metrics.fundingPct}%
            </span>
          </div>
          <div className="text-2xl font-semibold tabular-nums text-emerald-600 dark:text-emerald-400">
            {formatAmount(metrics.totalSaved, 'INR')}
          </div>
          <p className="text-[11px] text-content-muted">Funded across goals</p>
        </div>

        <div className="space-y-1 lg:border-l lg:border-hairline lg:pl-4">
          <span className="text-[11px] font-medium text-content-muted block">
            Remaining to Save
          </span>
          <div className="text-2xl font-semibold tabular-nums text-content-primary">
            {formatAmount(Math.max(0, metrics.totalTarget - metrics.totalSaved), 'INR')}
          </div>
          <p className="text-[11px] text-content-muted">Capital to complete</p>
        </div>

        <div className="space-y-1 border-l border-hairline pl-4">
          <span className="text-[11px] font-medium text-content-muted block">
            Goals Feasibility
          </span>
          <div className="text-2xl font-semibold tabular-nums text-content-primary flex items-baseline gap-2">
            <span>{metrics.onTrackCount + metrics.completedCount}</span>
            <span className="text-xs text-content-muted font-normal tabular-nums">
              ({metrics.onTrackCount} on track, {metrics.behindCount} behind)
            </span>
          </div>
          <p className="text-[11px] text-content-muted">Based on monthly rate</p>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center justify-between border-b border-hairline pb-2">
        <div className="flex items-center gap-1.5 text-xs font-medium overflow-x-auto">
          {[
            { key: 'all' as const, label: 'All Goals', count: goals.length },
            { key: 'on_track' as const, label: 'On Track', count: metrics.onTrackCount },
            { key: 'behind' as const, label: 'Behind Schedule', count: metrics.behindCount },
            { key: 'completed' as const, label: 'Completed', count: metrics.completedCount },
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

      {/* Goals Grid */}
      {isLoading ? (
        <div className="p-16 flex justify-center bg-surface rounded-xl border border-hairline">
          <LoadingSpinner />
        </div>
      ) : goals.length === 0 ? (
        <div className="bg-surface rounded-xl border border-hairline p-12 text-center space-y-3">
          <div className="w-10 h-10 rounded-lg bg-canvas border border-hairline text-content-muted flex items-center justify-center mx-auto">
            <TrophyIcon className="w-5 h-5" />
          </div>
          <h3 className="text-sm font-semibold text-content-primary">No Savings Goals Set</h3>
          <p className="text-xs text-content-muted max-w-sm mx-auto">
            Build financial resilience by setting an Emergency Reserve or planned purchase milestone.
          </p>
          <button
            onClick={handleOpenCreate}
            className="px-3.5 py-1.5 bg-[#4F46E5] hover:bg-[#4338CA] text-white text-xs font-medium rounded-lg transition-colors cursor-pointer"
          >
            Create Your First Goal
          </button>
        </div>
      ) : filteredGoals.length === 0 ? (
        <div className="bg-surface rounded-xl border border-hairline p-10 text-center text-xs text-content-muted">
          No savings goals match the &quot;{selectedFilter}&quot; filter.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filteredGoals.map((g) => (
            <GoalCard
              key={g.id}
              goal={g}
              onUpdateProgress={handleOpenDeposit}
              onEdit={handleOpenEdit}
              onDelete={handleDelete}
            />
          ))}
        </div>
      )}

      {/* Interactive What-If Scenario Simulator */}
      {goals.length > 0 && <ScenarioSlider goals={goals} />}

      {/* Create / Edit Goal Modal */}
      {createModalOpen && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-black/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-surface border border-hairline rounded-xl max-w-md w-full p-6 shadow-xl space-y-4 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-start justify-between border-b border-hairline pb-3">
              <div>
                <h2 className="text-sm font-semibold text-content-primary">
                  {editingGoal ? `Edit Goal: ${editingGoal.name}` : 'Create Savings Goal'}
                </h2>
                <p className="text-xs text-content-muted mt-0.5">
                  Define milestone target, deadline, and monthly plan
                </p>
              </div>
              <button
                onClick={() => setCreateModalOpen(false)}
                className="text-content-muted hover:text-content-primary rounded p-1 text-sm font-semibold"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateOrUpdateSubmit} className="space-y-3 text-xs">
              <div>
                <label className="block font-medium text-content-primary mb-1">
                  Goal Name
                </label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. 6-Month Emergency Buffer"
                  className="w-full rounded-lg border border-hairline bg-canvas text-content-primary px-3 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-[#4F46E5]"
                />
              </div>

              <div>
                <label className="block font-medium text-content-primary mb-1">
                  Goal Type
                </label>
                <select
                  value={goalType}
                  onChange={(e) => setGoalType(e.target.value as GoalType)}
                  className="w-full rounded-lg border border-hairline bg-canvas text-content-primary px-3 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-[#4F46E5]"
                >
                  <option value="emergency_fund">Emergency Fund</option>
                  <option value="purchase">Planned Purchase</option>
                  <option value="custom">Custom Milestone</option>
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-medium text-content-primary mb-1">
                    Target Amount (₹)
                  </label>
                  <input
                    type="number"
                    required
                    min="1000"
                    step="1000"
                    value={targetAmountRupees}
                    onChange={(e) => setTargetAmountRupees(e.target.value)}
                    className="w-full rounded-lg border border-hairline bg-canvas text-content-primary px-3 py-1.5 text-xs font-semibold tabular-nums focus:outline-none focus:ring-1 focus:ring-[#4F46E5]"
                  />
                </div>
                <div>
                  <label className="block font-medium text-content-primary mb-1">
                    Already Saved (₹)
                  </label>
                  <input
                    type="number"
                    min="0"
                    step="500"
                    value={currentAmountRupees}
                    onChange={(e) => setCurrentAmountRupees(e.target.value)}
                    className="w-full rounded-lg border border-hairline bg-canvas text-content-primary px-3 py-1.5 text-xs font-semibold tabular-nums focus:outline-none focus:ring-1 focus:ring-[#4F46E5]"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-medium text-content-primary mb-1">
                    Target Date (Optional)
                  </label>
                  <input
                    type="date"
                    value={targetDate}
                    onChange={(e) => setTargetDate(e.target.value)}
                    className="w-full rounded-lg border border-hairline bg-canvas text-content-primary px-3 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-[#4F46E5]"
                  />
                </div>
                <div>
                  <label className="block font-medium text-content-primary mb-1">
                    Planned Monthly (₹)
                  </label>
                  <input
                    type="number"
                    min="0"
                    step="500"
                    value={monthlyContributionRupees}
                    onChange={(e) => setMonthlyContributionRupees(e.target.value)}
                    placeholder="e.g. 5000"
                    className="w-full rounded-lg border border-hairline bg-canvas text-content-primary px-3 py-1.5 text-xs tabular-nums focus:outline-none focus:ring-1 focus:ring-[#4F46E5]"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-2.5 pt-3 border-t border-hairline">
                <button
                  type="button"
                  onClick={() => setCreateModalOpen(false)}
                  className="px-3.5 py-1.5 text-xs font-medium text-content-muted hover:text-content-primary rounded-lg border border-hairline hover:bg-canvas transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-4 py-1.5 text-xs font-medium bg-[#4F46E5] hover:bg-[#4338CA] text-white rounded-lg transition-colors disabled:opacity-40 cursor-pointer"
                >
                  {isSubmitting
                    ? 'Saving...'
                    : editingGoal
                    ? 'Update Goal'
                    : 'Create Goal'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Quick Deposit / Progress Update Modal */}
      {depositGoal && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-black/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-surface border border-hairline rounded-xl max-w-sm w-full p-6 shadow-xl space-y-4 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-start justify-between border-b border-hairline pb-3">
              <div>
                <h2 className="text-sm font-semibold text-content-primary">
                  Add Savings Deposit
                </h2>
                <p className="text-xs text-content-muted mt-0.5">{depositGoal.name}</p>
              </div>
              <button
                onClick={() => setDepositGoal(null)}
                className="text-content-muted hover:text-content-primary rounded p-1 text-sm font-semibold"
              >
                ✕
              </button>
            </div>

            {/* Mode Switcher */}
            <div className="flex rounded-lg bg-canvas border border-hairline p-0.5 text-xs">
              <button
                type="button"
                onClick={() => setIsDepositMode(true)}
                className={`flex-1 py-1 rounded-md font-medium transition-colors cursor-pointer ${
                  isDepositMode
                    ? 'bg-surface text-[#4F46E5] dark:text-[#818CF8] shadow-2xs'
                    : 'text-content-muted hover:text-content-primary'
                }`}
              >
                + Add Deposit
              </button>
              <button
                type="button"
                onClick={() => {
                  setIsDepositMode(false)
                  setDepositAmountRupees(String(depositGoal.current_amount_minor / 100))
                }}
                className={`flex-1 py-1 rounded-md font-medium transition-colors cursor-pointer ${
                  !isDepositMode
                    ? 'bg-surface text-[#4F46E5] dark:text-[#818CF8] shadow-2xs'
                    : 'text-content-muted hover:text-content-primary'
                }`}
              >
                Set Exact Balance
              </button>
            </div>

            <form onSubmit={handleDepositSubmit} className="space-y-4 text-xs">
              {/* Preset Chips */}
              {isDepositMode && (
                <div className="space-y-1.5">
                  <span className="text-[11px] text-content-muted font-medium">Quick Amount</span>
                  <div className="grid grid-cols-4 gap-1.5">
                    {[1000, 2500, 5000, 10000].map((amt) => (
                      <button
                        key={amt}
                        type="button"
                        onClick={() => setDepositAmountRupees(String(amt))}
                        className={`py-1 rounded-md border tabular-nums font-medium text-[11px] transition-colors cursor-pointer ${
                          depositAmountRupees === String(amt)
                            ? 'bg-[#4F46E5]/10 border-[#4F46E5]/30 text-[#4F46E5] dark:text-[#818CF8]'
                            : 'border-hairline bg-surface text-content-muted hover:text-content-primary'
                        }`}
                      >
                        +₹{amt >= 1000 ? `${amt / 1000}k` : amt}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              <div>
                <label className="block font-medium text-content-primary mb-1">
                  {isDepositMode ? 'Deposit Amount (₹)' : 'Current Balance (₹)'}
                </label>
                <div className="relative">
                  <span className="absolute left-3 top-2 text-content-muted text-xs">₹</span>
                  <input
                    type="number"
                    required
                    min="100"
                    step="100"
                    value={depositAmountRupees}
                    onChange={(e) => setDepositAmountRupees(e.target.value)}
                    className="w-full pl-7 pr-3 py-1.5 rounded-lg border border-hairline bg-canvas text-content-primary text-xs font-semibold tabular-nums focus:outline-none focus:ring-1 focus:ring-[#4F46E5]"
                    autoFocus
                  />
                </div>
                {isDepositMode && (
                  <p className="text-[10px] text-content-muted mt-1 tabular-nums">
                    New projected balance:{' '}
                    <strong className="text-content-primary font-medium">
                      {formatAmount(
                        depositGoal.current_amount_minor +
                          Math.round(Number(depositAmountRupees || 0) * 100),
                        'INR'
                      )}
                    </strong>
                  </p>
                )}
              </div>

              <div className="flex justify-end gap-2.5 pt-3 border-t border-hairline">
                <button
                  type="button"
                  onClick={() => setDepositGoal(null)}
                  className="px-3.5 py-1.5 text-xs font-medium text-content-muted hover:text-content-primary rounded-lg border border-hairline hover:bg-canvas transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isUpdatingProgress}
                  className="px-4 py-1.5 text-xs font-medium bg-[#4F46E5] hover:bg-[#4338CA] text-white rounded-lg transition-colors disabled:opacity-40 cursor-pointer"
                >
                  {isUpdatingProgress
                    ? 'Saving...'
                    : isDepositMode
                    ? 'Confirm Deposit'
                    : 'Save Balance'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Advisory Regulatory Notice */}
      <div className="text-center pt-2">
        <p className="text-[11px] text-content-muted">
          Advisory notice: FinPilot savings targets and what-if scenario simulations are educational forecasting tools. FinPilot is not a SEBI-registered investment advisor and does not execute investment or banking deposits.
        </p>
      </div>
    </div>
  )
}
