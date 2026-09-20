import { describe, it, expect } from 'vitest'
import { MonthlyReportResponse } from '../types'

describe('Monthly Report formatting and contracts', () => {
  it('correctly parses and validates a mock MonthlyReportResponse', () => {
    const mockReport: MonthlyReportResponse = {
      month: '2024-08',
      month_name: 'August 2024',
      user_id: 1,
      currency: 'INR',
      cash_flow: {
        income_minor: 10000000,
        income_display: '₹1,00,000.00',
        expense_minor: 649900,
        expense_display: '₹6,499.00',
        net_savings_minor: 9350100,
        net_savings_display: '₹93,501.00',
        savings_rate_pct: 93.5,
        mom_change_pct: -5.2,
        recurring_spend_minor: 79900,
        recurring_spend_display: '₹799.00',
      },
      narrative: 'In August 2024, you had net savings of ₹93,501.00.',
      top_categories: [
        {
          category: 'Dining',
          amount_minor: 120000,
          amount_display: '₹1,200.00',
          pct_of_total: 18.5,
          transaction_count: 2,
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
      budgets: [
        {
          category: 'Dining',
          monthly_limit_minor: 100000,
          monthly_limit_display: '₹1,000.00',
          spent_minor: 120000,
          spent_display: '₹1,200.00',
          remaining_minor: 0,
          remaining_display: '₹0.00',
          spent_pct: 120.0,
          status: 'exceeded',
        },
      ],
      goals: [
        {
          id: 1,
          name: 'Emergency Fund',
          type: 'emergency_fund',
          target_amount_minor: 30000000,
          target_amount_display: '₹3,00,000.00',
          current_amount_minor: 15000000,
          current_amount_display: '₹1,50,000.00',
          progress_pct: 50.0,
          target_date: '2025-08-01',
          months_remaining: 11,
          required_monthly_savings_minor: 1363637,
          required_monthly_savings_display: '₹13,636.37',
          on_track: true,
        },
      ],
      recurring: [
        {
          id: 1,
          merchant: 'Netflix',
          avg_amount_minor: 79900,
          avg_amount_display: '₹799.00',
          frequency: 'monthly',
          status: 'active',
          type: 'subscription',
        },
      ],
      anomalies: [
        {
          id: 1,
          type: 'duplicate_charge',
          severity: 'warning',
          text: 'Possible duplicate charge at Netflix',
        },
      ],
      action_items: [
        {
          id: 'act-1',
          category: 'anomaly',
          title: 'Review Potential Duplicate Charge (Netflix)',
          description: 'A duplicate charge was detected.',
          impact_type: 'high',
          potential_savings_minor: 79900,
          potential_savings_display: '₹799.00',
        },
      ],
      disclaimer: 'FinPilot is NOT a registered financial advisor.',
    }

    expect(mockReport.month).toBe('2024-08')
    expect(mockReport.cash_flow.income_minor).toBe(10000000)
    expect(mockReport.cash_flow.net_savings_minor).toBe(9350100)
    expect(mockReport.budgets[0].status).toBe('exceeded')
    expect(mockReport.action_items[0].impact_type).toBe('high')
    expect(mockReport.disclaimer).toContain('NOT a registered financial advisor')
  })
})
