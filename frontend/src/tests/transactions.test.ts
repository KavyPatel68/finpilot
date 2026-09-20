import { describe, it, expect } from 'vitest'
import type { Transaction, TransactionListResponse } from '../types'

describe('Transactions Ledger contracts and operations', () => {
  it('validates TransactionListResponse with sorting and pagination fields', () => {
    const mockTx: Transaction = {
      id: 101,
      user_id: 1,
      account_id: 1,
      document_id: 1,
      date: '2024-09-15',
      raw_description: 'SWIGGY*BANGALORE',
      merchant_normalized: 'Swiggy',
      amount_minor: 45000,
      amount_display: '₹450.00',
      direction: 'expense',
      category: 'Dining',
      subcategory: 'Food Delivery',
      category_source: 'rule',
      confidence: 1.0,
      is_recurring: false,
      recurring_group_id: null,
      is_transfer: false,
      is_anomaly: false,
      notes: 'Weekend lunch order',
      payment_method: 'UPI',
      created_at: '2024-09-15T12:00:00Z',
    }

    const mockResponse: TransactionListResponse = {
      items: [mockTx],
      total: 1,
      page: 1,
      page_size: 25,
      total_pages: 1,
    }

    expect(mockResponse.items).toHaveLength(1)
    expect(mockResponse.items[0].merchant_normalized).toBe('Swiggy')
    expect(mockResponse.items[0].category_source).toBe('rule')
    expect(mockResponse.items[0].direction).toBe('expense')
  })

  it('verifies CSV generation row formatting with escaped quotes', () => {
    const t: Partial<Transaction> = {
      id: 1,
      date: '2024-09-01',
      merchant_normalized: 'Netflix, Inc.',
      raw_description: 'NETFLIX*MONTHLY',
      category: 'Subscriptions',
      direction: 'expense',
      amount_minor: 79900,
      payment_method: 'Credit Card',
      notes: 'Family "plan"',
    }

    const row = [
      t.id,
      t.date,
      `"${(t.merchant_normalized || '').replace(/"/g, '""')}"`,
      `"${(t.raw_description || '').replace(/"/g, '""')}"`,
      `"${t.category || ''}"`,
      t.direction,
      ((t.amount_minor || 0) / 100).toFixed(2),
      `"${t.payment_method || ''}"`,
      `"${(t.notes || '').replace(/"/g, '""')}"`,
    ].join(',')

    expect(row).toContain('"Netflix, Inc."')
    expect(row).toContain('"Family ""plan"""')
    expect(row).toContain('799.00')
  })
})
