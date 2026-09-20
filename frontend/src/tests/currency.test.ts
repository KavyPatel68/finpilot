import { describe, it, expect } from 'vitest'
import { formatAmount } from '../utils/currency'

describe('formatAmount', () => {
  it('formats INR in Indian comma style', () => {
    expect(formatAmount(12345678, 'INR')).toBe('₹1,23,456.78')
  })
  it('formats small INR amounts', () => {
    expect(formatAmount(64900, 'INR')).toBe('₹649.00')
  })
  it('formats USD in western style', () => {
    expect(formatAmount(100000, 'USD')).toBe('$1,000.00')
  })
})
