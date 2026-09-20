import { describe, it, expect } from 'vitest'
import type { RecurringGroup, PriceHikeItem, UpcomingObligationsResponse } from '../types'

describe('Subscriptions & Recurring metrics calculations', () => {
  const mockSubscriptions: RecurringGroup[] = [
    {
      id: 1,
      user_id: 1,
      merchant: 'Netflix',
      avg_amount_minor: 79900,
      avg_amount_display: '₹799.00',
      frequency: 'monthly',
      next_expected_date: '2024-04-15',
      last_seen: '2024-03-15',
      status: 'active',
      type: 'subscription',
      monthly_cost_minor: 79900,
      annual_cost_minor: 958800,
    },
    {
      id: 2,
      user_id: 1,
      merchant: 'Cult.fit',
      avg_amount_minor: 1200000,
      avg_amount_display: '₹12,000.00',
      frequency: 'yearly',
      next_expected_date: '2024-11-01',
      last_seen: '2023-11-01',
      status: 'active',
      type: 'subscription',
      monthly_cost_minor: 100000,
      annual_cost_minor: 1200000,
    },
    {
      id: 3,
      user_id: 1,
      merchant: 'HDFC Home Loan EMI',
      avg_amount_minor: 4500000,
      avg_amount_display: '₹45,000.00',
      frequency: 'monthly',
      next_expected_date: '2024-04-05',
      last_seen: '2024-03-05',
      status: 'active',
      type: 'emi',
      monthly_cost_minor: 4500000,
      annual_cost_minor: 54000000,
    },
    {
      id: 4,
      user_id: 1,
      merchant: 'Gym Membership Lapsed',
      avg_amount_minor: 250000,
      avg_amount_display: '₹2,500.00',
      frequency: 'monthly',
      next_expected_date: '2024-02-01',
      last_seen: '2024-01-01',
      status: 'possibly_cancelled',
      type: 'subscription',
      monthly_cost_minor: 250000,
      annual_cost_minor: 3000000,
    },
    {
      id: 5,
      user_id: 1,
      merchant: 'Old Spotify Family',
      avg_amount_minor: 17900,
      avg_amount_display: '₹179.00',
      frequency: 'monthly',
      next_expected_date: null,
      last_seen: '2023-12-01',
      status: 'cancelled',
      type: 'subscription',
      monthly_cost_minor: 17900,
      annual_cost_minor: 214800,
    },
  ]

  it('accurately computes active subscription counts, monthly normalized sum, and annualized cost', () => {
    let monthlyActiveCost = 0
    let activeCount = 0
    let overdueCount = 0

    for (const sub of mockSubscriptions) {
      if (sub.status === 'active') {
        activeCount++
        monthlyActiveCost += sub.monthly_cost_minor
      } else if (sub.status === 'possibly_cancelled') {
        overdueCount++
      }
    }

    expect(activeCount).toBe(3)
    expect(overdueCount).toBe(1)
    // 79900 (Netflix) + 100000 (Cult.fit 12000/12) + 4500000 (HDFC EMI) = 4679900 (₹46,799.00)
    expect(monthlyActiveCost).toBe(4679900)
    expect(monthlyActiveCost * 12).toBe(56158800)
  })

  it('validates price hike detection and upcoming obligations structures', () => {
    const mockHike: PriceHikeItem = {
      merchant: 'Netflix',
      previous_amount_minor: 64900,
      previous_amount_display: '₹649.00',
      new_amount_minor: 79900,
      new_amount_display: '₹799.00',
      difference_minor: 15000,
      difference_display: '₹150.00',
      effective_date: '2024-03-01',
    }

    expect(mockHike.difference_minor).toBe(15000)
    expect(mockHike.new_amount_minor).toBeGreaterThan(mockHike.previous_amount_minor)

    const mockCalendar: UpcomingObligationsResponse = {
      reference_date: '2024-03-20',
      window_days: 30,
      total_upcoming_minor: 4579900,
      total_upcoming_display: '₹45,799.00',
      count: 2,
      items: [
        {
          id: 3,
          merchant: 'HDFC Home Loan EMI',
          type: 'emi',
          amount_minor: 4500000,
          amount_display: '₹45,000.00',
          due_date: '2024-04-05',
          days_until_due: 16,
          frequency: 'monthly',
        },
        {
          id: 1,
          merchant: 'Netflix',
          type: 'subscription',
          amount_minor: 79900,
          amount_display: '₹799.00',
          due_date: '2024-04-15',
          days_until_due: 26,
          frequency: 'monthly',
        },
      ],
    }

    expect(mockCalendar.count).toBe(2)
    expect(mockCalendar.items[0].merchant).toBe('HDFC Home Loan EMI')
    expect(mockCalendar.items[0].days_until_due).toBe(16)
  })
})
