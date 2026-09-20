import React from 'react'
import { ExclamationTriangleIcon } from '@heroicons/react/24/outline'
import type { ParseError } from '../../types'

interface ParseStatusTableProps {
  errors: ParseError[]
}

export function ParseStatusTable({ errors }: ParseStatusTableProps) {
  if (!errors || errors.length === 0) return null

  return (
    <div className="rounded-xl border border-amber-200/70 dark:border-amber-900/40 bg-amber-50/50 dark:bg-amber-950/20 p-4 space-y-3">
      <div className="flex items-center gap-2">
        <ExclamationTriangleIcon className="w-4 h-4 text-amber-600 dark:text-amber-400 shrink-0" />
        <h3 className="font-semibold text-amber-900 dark:text-amber-300 text-xs">
          Parse Warnings & Skipped Rows ({errors.length})
        </h3>
      </div>
      <p className="text-[11px] text-amber-800/80 dark:text-amber-300/70">
        The following rows could not be parsed as valid financial transactions and were skipped:
      </p>
      <div className="overflow-x-auto max-h-56 border border-hairline rounded-lg bg-surface">
        <table className="min-w-full divide-y divide-hairline text-xs text-left">
          <thead className="bg-canvas text-content-muted font-medium">
            <tr>
              <th className="px-3 py-2 w-24 text-[11px]">Row #</th>
              <th className="px-3 py-2 text-[11px]">Details / Reason</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-hairline text-content-primary">
            {errors.map((err, idx) => (
              <tr key={idx} className="hover:bg-canvas/50 transition-colors">
                <td className="px-3 py-1.5 font-medium tabular-nums text-content-muted text-[11px]">
                  {err.row !== null && err.row !== undefined ? `Row ${err.row + 1}` : '—'}
                </td>
                <td className="px-3 py-1.5 text-rose-600 dark:text-rose-400 text-[11px]">{err.message}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
