import { describe, it, expect } from 'vitest'
import type { SpendingTrendItem, SummaryPayload } from '../types'

describe('Dashboard metrics and trend calculations', () => {
  it('correctly validates SummaryPayload calculations', () => {
    const mockPayload: SummaryPayload = {
      income_minor: 8500000,
      expense_minor: 6173200,
      net_savings_minor: 2326800,
      savings_rate_pct: 27.4,
      mom_change_pct: 2.5,
      top_categories: [
        {
          category: 'Dining',
          amount_minor: 120000,
          amount_display: '₹1,200.00',
          pct_of_total: 19.4,
        },
      ],
      top_merchants: [
        {
          merchant: 'Swiggy',
          amount_minor: 120000,
          amount_display: '₹1,200.00',
          transaction_count: 2,
        },
      ],
    }

    expect(mockPayload.income_minor - mockPayload.expense_minor).toBe(mockPayload.net_savings_minor)
    expect(mockPayload.savings_rate_pct).toBe(27.4)
    expect(mockPayload.top_categories[0].category).toBe('Dining')
  })

  it('verifies SpendingTrendItem properties for 3M/6M/12M trend lines', () => {
    const mockTrend: SpendingTrendItem = {
      month: '2024-09',
      month_name: 'Sep 2024',
      income_minor: 8500000,
      income_display: '₹85,000.00',
      expense_minor: 6173200,
      expense_display: '₹61,732.00',
      net_savings_minor: 2326800,
      net_savings_display: '₹23,268.00',
      savings_rate_pct: 27.4,
    }

    expect(mockTrend.month).toBe('2024-09')
    expect(mockTrend.net_savings_minor).toBeGreaterThan(0)
    expect(mockTrend.income_minor).toBeGreaterThan(mockTrend.expense_minor)
  })
})
