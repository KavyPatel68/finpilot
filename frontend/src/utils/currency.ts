export type Currency = 'INR' | 'USD' | 'EUR' | 'GBP'

const SYMBOLS: Record<Currency, string> = {
  INR: '₹', USD: '$', EUR: '€', GBP: '£',
}

const MINOR_UNITS: Record<Currency, number> = {
  INR: 100, USD: 100, EUR: 100, GBP: 100,
}

export function fromMinor(minor: number, currency: Currency = 'INR'): number {
  return minor / MINOR_UNITS[currency]
}

/**
 * Format minor units to display string.
 * INR uses Indian comma system: ₹1,23,456.78
 * Others use western: $1,234.56
 */
export function formatAmount(minor: number, currency: Currency = 'INR'): string {
  const amount = fromMinor(minor, currency)
  const symbol = SYMBOLS[currency]
  if (currency === 'INR') {
    return symbol + formatIndian(amount)
  }
  return symbol + amount.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function formatIndian(n: number): string {
  const [intPart, decPart] = n.toFixed(2).split('.')
  const lastThree = intPart.slice(-3)
  const rest = intPart.slice(0, -3)
  const formatted = rest.length > 0
    ? rest.replace(/\B(?=(\d{2})+(?!\d))/g, ',') + ',' + lastThree
    : lastThree
  return `${formatted}.${decPart}`
}
