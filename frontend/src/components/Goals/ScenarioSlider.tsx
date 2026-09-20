import React, { useState, useEffect, useRef } from 'react'
import type { Goal, GoalSimulationResponse } from '../../types'
import { simulateGoal } from '../../api/goals'
import { formatAmount } from '../../utils/currency'
import {
  SparklesIcon,
  ClockIcon,
  ArrowRightIcon,
  AdjustmentsHorizontalIcon,
} from '@heroicons/react/24/outline'

interface ScenarioSliderProps {
  goals: Goal[]
}

const DISCRETIONARY_CATEGORIES = [
  'Dining',
  'Shopping',
  'Subscriptions',
  'Entertainment',
  'Transport',
  'Other',
]

export function ScenarioSlider({ goals }: ScenarioSliderProps) {
  const activeGoals = goals.filter((g) => g.is_active && g.progress_pct < 100)

  const [selectedGoalId, setSelectedGoalId] = useState<number | ''>('')
  const [selectedCategory, setSelectedCategory] = useState('Dining')
  const [cutAmountRupees, setCutAmountRupees] = useState(3000)
  const [simulationResult, setSimulationResult] = useState<GoalSimulationResponse | null>(null)
  const [isSimulating, setIsSimulating] = useState(false)
  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    if (activeGoals.length > 0 && selectedGoalId === '') {
      setSelectedGoalId(activeGoals[0].id)
    }
  }, [activeGoals, selectedGoalId])

  // Debounced API simulation
  useEffect(() => {
    if (!selectedGoalId) return

    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current)
    }

    setIsSimulating(true)
    debounceTimerRef.current = setTimeout(() => {
      const cutMinor = cutAmountRupees * 100

      simulateGoal({
        goal_id: Number(selectedGoalId),
        cut_category: selectedCategory,
        cut_amount_minor: cutMinor,
      })
        .then((res) => setSimulationResult(res))
        .catch((err) => console.error('Simulation error:', err))
        .finally(() => setIsSimulating(false))
    }, 250)

    return () => {
      if (debounceTimerRef.current) clearTimeout(debounceTimerRef.current)
    }
  }, [selectedGoalId, selectedCategory, cutAmountRupees])

  if (activeGoals.length === 0) {
    return null
  }

  const selectedGoal = activeGoals.find((g) => g.id === selectedGoalId)

  return (
    <div className="rounded-xl border border-hairline bg-surface p-5 sm:p-6 shadow-2xs space-y-5">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-canvas border border-hairline text-content-muted flex items-center justify-center shrink-0">
          <AdjustmentsHorizontalIcon className="w-4 h-4" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-semibold text-content-primary">
              Goal Acceleration Simulator
            </h2>
            <span className="px-2 py-0.5 rounded-full text-[10px] font-medium uppercase tracking-wider bg-canvas border border-hairline text-content-muted">
              Interactive
            </span>
          </div>
          <p className="text-xs text-content-muted mt-0.5">
            Test how trimming discretionary monthly expenses accelerates your target savings milestone.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 items-stretch">
        {/* Controls Card */}
        <div className="space-y-4 bg-canvas rounded-lg border border-hairline p-4">
          {/* Select Goal */}
          <div>
            <label className="block text-xs font-medium text-content-primary mb-1">
              Select Target Goal
            </label>
            <select
              value={selectedGoalId}
              onChange={(e) => setSelectedGoalId(Number(e.target.value))}
              className="w-full rounded-lg border border-hairline bg-surface text-content-primary px-3 py-1.5 text-xs font-medium focus:outline-none focus:ring-1 focus:ring-[#4F46E5]"
            >
              {activeGoals.map((g) => (
                <option key={g.id} value={g.id}>
                  {g.name} (Target: {formatAmount(g.target_amount_minor, 'INR')})
                </option>
              ))}
            </select>
          </div>

          {/* Select Category */}
          <div>
            <label className="block text-xs font-medium text-content-primary mb-1">
              Category Spending to Trim
            </label>
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="w-full rounded-lg border border-hairline bg-surface text-content-primary px-3 py-1.5 text-xs font-medium focus:outline-none focus:ring-1 focus:ring-[#4F46E5]"
            >
              {DISCRETIONARY_CATEGORIES.map((cat) => (
                <option key={cat} value={cat}>
                  {cat}
                </option>
              ))}
            </select>
          </div>

          {/* Slider with Live Amount Indicator */}
          <div className="space-y-2 pt-1">
            <div className="flex justify-between items-baseline text-xs">
              <span className="font-medium text-content-primary">
                Monthly Savings Redirected:
              </span>
              <span className="font-semibold tabular-nums text-[#4F46E5] dark:text-[#818CF8] text-sm">
                ₹{cutAmountRupees.toLocaleString('en-IN')}/mo
              </span>
            </div>
            <input
              type="range"
              min="500"
              max="25000"
              step="500"
              value={cutAmountRupees}
              onChange={(e) => setCutAmountRupees(Number(e.target.value))}
              className="w-full accent-[#4F46E5] cursor-pointer h-1.5 bg-canvas border border-hairline rounded-lg"
            />
            <div className="flex justify-between text-[10px] text-content-muted tabular-nums">
              <span>₹500/mo</span>
              <span>₹12,500/mo</span>
              <span>₹25,000/mo</span>
            </div>
          </div>
        </div>

        {/* Flat Simulation Outcome Card */}
        <div className="bg-canvas rounded-lg p-5 border border-hairline flex flex-col justify-between space-y-4">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-medium uppercase tracking-wider text-content-muted flex items-center gap-1.5">
                <SparklesIcon className="w-3.5 h-3.5 text-[#4F46E5] dark:text-[#818CF8]" />
                <span>Projected Impact</span>
              </span>

              {isSimulating && (
                <span className="text-[10px] text-content-muted animate-pulse">
                  Computing...
                </span>
              )}
            </div>

            {simulationResult ? (
              <div className="space-y-3">
                <div className="flex items-baseline gap-2">
                  <span className="text-3xl font-semibold tabular-nums tracking-tight text-content-primary">
                    {simulationResult.months_saved}
                  </span>
                  <span className="text-xs font-medium text-content-muted">
                    month{simulationResult.months_saved !== 1 ? 's' : ''} saved to completion!
                  </span>
                </div>

                <p className="text-xs text-content-muted leading-relaxed bg-surface p-3 rounded-lg border border-hairline">
                  {simulationResult.narrative}
                </p>
              </div>
            ) : (
              <div className="py-6 text-center text-xs text-content-muted">
                Adjust the slider to simulate savings velocity.
              </div>
            )}
          </div>

          {/* Timeline Acceleration Comparison */}
          {simulationResult && simulationResult.simulated_target_date && (
            <div className="pt-2 border-t border-hairline flex items-center justify-between text-xs text-content-muted">
              <span className="flex items-center gap-1">
                <ClockIcon className="w-3.5 h-3.5" />
                <span>Completion:</span>
              </span>
              <span className="tabular-nums font-medium text-content-primary flex items-center gap-1.5">
                {selectedGoal?.target_date ? (
                  <>
                    <span className="line-through text-content-muted font-normal">
                      {selectedGoal.target_date}
                    </span>
                    <ArrowRightIcon className="w-3 h-3 text-content-muted" />
                  </>
                ) : null}
                <span>{simulationResult.simulated_target_date}</span>
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
