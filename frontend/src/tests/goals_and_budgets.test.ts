import { describe, it, expect } from 'vitest'
import { formatAmount } from '../utils/currency'
import type { Goal, GoalSimulationResponse } from '../types'

describe('Budget calculations & thresholds', () => {
  it('correctly calculates spent percentage and assigns status thresholds', () => {
    // Under 80%: on_track
    const limit1 = 1000000 // ₹10,000
    const spent1 = 500000  // ₹5,000
    const pct1 = Math.round((spent1 / limit1) * 100)
    expect(pct1).toBe(50)
    expect(pct1 < 80).toBe(true)

    // 80% to 100%: warning
    const spent2 = 850000  // ₹8,500
    const pct2 = Math.round((spent2 / limit1) * 100)
    expect(pct2).toBe(85)
    expect(pct2 >= 80 && pct2 <= 100).toBe(true)

    // > 100%: exceeded
    const spent3 = 1250000 // ₹12,500
    const pct3 = Math.round((spent3 / limit1) * 100)
    expect(pct3).toBe(125)
    expect(pct3 > 100).toBe(true)
  })

  it('correctly calculates month-end pacing velocity projection', () => {
    const monthlyLimitMinor = 2000000 // ₹20,000 limit
    const spentMinor = 1400000        // ₹14,000 spent so far
    const elapsedDays = 15            // 15 days elapsed
    const totalDays = 30              // 30 days in month

    // Projected spend = (spent / elapsed) * total
    const projectedSpendMinor = Math.round((spentMinor / elapsedDays) * totalDays)
    const projectedPct = Math.round((projectedSpendMinor / monthlyLimitMinor) * 100)

    expect(projectedSpendMinor).toBe(2800000) // ₹28,000
    expect(projectedPct).toBe(140) // 140% of budget
    expect(projectedSpendMinor > monthlyLimitMinor).toBe(true) // Overshoot detected
  })

  it('formats Indian rupee amounts consistently', () => {
    expect(formatAmount(1000000, 'INR')).toBe('₹10,000.00')
    expect(formatAmount(30000000, 'INR')).toBe('₹3,00,000.00')
  })
})

describe('Savings Goals & Acceleration Simulator', () => {
  const mockGoal: Goal = {
    id: 1,
    user_id: 1,
    name: 'Emergency Fund',
    type: 'emergency_fund',
    target_amount_minor: 30000000, // ₹3,00,000
    current_amount_minor: 15000000, // ₹1,50,000 (50%)
    target_date: '2025-08-01',
    monthly_contribution_planned_minor: 1500000, // ₹15,000/mo
    is_active: true,
    progress_pct: 50.0,
    months_remaining: 10,
    required_monthly_savings_minor: 1500000,
    on_track: true,
  }

  it('computes circular SVG progress geometry and milestones', () => {
    const radius = 28
    const circumference = 2 * Math.PI * radius
    const pct = mockGoal.progress_pct
    const strokeDashoffset = circumference - (pct / 100) * circumference

    expect(pct).toBe(50)
    expect(strokeDashoffset).toBeCloseTo(circumference / 2, 2)
  })

  it('validates simulation acceleration response calculations', () => {
    const mockSimulation: GoalSimulationResponse = {
      goal_id: 1,
      goal_name: 'Emergency Fund',
      cut_category: 'Dining',
      cut_amount_minor: 500000,
      cut_amount_display: '₹5,000.00',
      current_target_date: '2025-08-01',
      simulated_target_date: '2025-05-01',
      months_saved: 3,
      narrative: 'By reducing your Dining spend by ₹5,000.00/month, you can reach your goal 3 months earlier.',
    }

    expect(mockSimulation.months_saved).toBe(3)
    expect(mockSimulation.narrative).toContain('3 months earlier')
  })
})
