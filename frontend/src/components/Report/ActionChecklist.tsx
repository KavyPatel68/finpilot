import { useState } from 'react'
import { CheckIcon } from '@heroicons/react/24/outline'
import { ReportActionItem } from '../../types'

interface ActionChecklistProps {
  items: ReportActionItem[]
  month: string
}

export function ActionChecklist({ items, month }: ActionChecklistProps) {
  const [completed, setCompleted] = useState<Record<string, boolean>>(() => {
    try {
      const saved = localStorage.getItem(`finpilot_actions_${month}`)
      return saved ? JSON.parse(saved) : {}
    } catch {
      return {}
    }
  })

  const toggleItem = (id: string) => {
    setCompleted((prev) => {
      const next = { ...prev, [id]: !prev[id] }
      try {
        localStorage.setItem(`finpilot_actions_${month}`, JSON.stringify(next))
      } catch {
        // ignore storage errors
      }
      return next
    })
  }

  const completedCount = items.filter((i) => completed[i.id]).length
  const totalCount = items.length
  const progressPct = totalCount > 0 ? Math.round((completedCount / totalCount) * 100) : 0
  const allCompleted = totalCount > 0 && completedCount === totalCount

  if (!items.length) {
    return (
      <div className="rounded-xl border bg-surface border-hairline p-5 shadow-2xs">
        <h3 className="font-semibold text-content-primary text-sm mb-1">
          Actionable Decision Checklist
        </h3>
        <p className="text-xs text-content-muted">
          No optimization flags or action items detected for this statement period.
        </p>
      </div>
    )
  }

  return (
    <div className="rounded-xl border bg-surface border-hairline p-5 shadow-2xs space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-hairline pb-3">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="font-semibold text-content-primary text-sm">
              Actionable Decision Checklist
            </h3>
            {allCompleted && (
              <span className="px-2 py-0.5 rounded-full text-[10px] font-medium uppercase tracking-wider bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-500/20">
                All Done
              </span>
            )}
          </div>
          <p className="text-xs text-content-muted mt-0.5">
            Data-driven decisions to curtail leaks and accelerate goals
          </p>
        </div>

        <div className="text-left sm:text-right">
          <span className="text-xs font-medium text-content-muted tabular-nums">
            {completedCount} of {totalCount} completed ({progressPct}%)
          </span>
          <div className="w-28 bg-canvas border border-hairline rounded-full h-1.5 mt-1 overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-300 ${
                allCompleted ? 'bg-emerald-500' : 'bg-[#4F46E5] dark:bg-[#818CF8]'
              }`}
              style={{ width: `${progressPct}%` }}
            />
          </div>
        </div>
      </div>

      <div className="space-y-2">
        {items.map((item) => {
          const isDone = !!completed[item.id]
          const isHigh = item.impact_type === 'high'
          const isMedium = item.impact_type === 'medium'

          return (
            <div
              key={item.id}
              onClick={() => toggleItem(item.id)}
              className={`flex items-start gap-3 p-3 rounded-lg border transition-colors cursor-pointer select-none ${
                isDone
                  ? 'bg-canvas border-hairline opacity-60'
                  : 'bg-surface border-hairline hover:bg-canvas/60'
              }`}
            >
              <button
                type="button"
                className={`mt-0.5 w-4 h-4 rounded border flex items-center justify-center transition-colors shrink-0 ${
                  isDone
                    ? 'bg-[#4F46E5] border-[#4F46E5] text-white'
                    : 'border-hairline bg-surface hover:border-[#4F46E5]'
                }`}
              >
                {isDone ? <CheckIcon className="w-3 h-3 stroke-[2.5]" /> : null}
              </button>

              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap mb-0.5">
                  <span
                    className={`text-xs font-medium ${
                      isDone
                        ? 'line-through text-content-muted'
                        : 'text-content-primary'
                    }`}
                  >
                    {item.title}
                  </span>

                  {isHigh && (
                    <span className="text-[9px] uppercase font-medium tracking-wider px-1.5 py-0.2 rounded bg-rose-500/10 text-rose-700 dark:text-rose-400 border border-rose-500/20">
                      High Priority
                    </span>
                  )}
                  {isMedium && (
                    <span className="text-[9px] uppercase font-medium tracking-wider px-1.5 py-0.2 rounded bg-amber-500/10 text-amber-700 dark:text-amber-400 border border-amber-500/20">
                      Medium
                    </span>
                  )}
                  {!isHigh && !isMedium && (
                    <span className="text-[9px] uppercase font-medium tracking-wider px-1.5 py-0.2 rounded bg-canvas text-content-muted border border-hairline">
                      Savings Tip
                    </span>
                  )}

                  {item.potential_savings_display && (
                    <span className="text-[10px] tabular-nums font-medium text-emerald-700 dark:text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.2 rounded-full ml-auto">
                      +{item.potential_savings_display}/mo
                    </span>
                  )}
                </div>

                <p
                  className={`text-[11px] leading-relaxed ${
                    isDone
                      ? 'line-through text-content-muted'
                      : 'text-content-muted'
                  }`}
                >
                  {item.description}
                </p>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
