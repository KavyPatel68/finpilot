import React from 'react'
import { ShieldCheckIcon } from '@heroicons/react/24/outline'

export function DisclaimerBanner() {
  return (
    <aside
      aria-label="Non-Advisor Notice"
      className="bg-amber-50/90 dark:bg-amber-950/40 border-b border-amber-200/80 dark:border-amber-900/50 px-4 py-1.5 text-center text-[11px] text-amber-900 dark:text-amber-200/90 flex items-center justify-center gap-1.5 transition-colors"
    >
      <ShieldCheckIcon className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400 shrink-0" />
      <span>
        <strong>Informational only.</strong> FinPilot is not a financial or investment advisor.
        It provides data analytics & decision support, never recommendations of securities, loans, or financial products.
      </span>
    </aside>
  )
}
