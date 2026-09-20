import { useState } from 'react'
import {
  ArrowDownTrayIcon,
  PrinterIcon,
  ShieldExclamationIcon,
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon,
  ExclamationTriangleIcon,
  CalendarDaysIcon,
  SparklesIcon,
} from '@heroicons/react/24/outline'
import { MonthlyReportResponse, ReportMonth } from '../../types'
import { ActionChecklist } from './ActionChecklist'
import { downloadReportPdf } from '../../api/reports'

interface ReportViewProps {
  report: MonthlyReportResponse
  months: ReportMonth[]
  selectedMonth: string
  onSelectMonth: (month: string) => void
}

export function ReportView({
  report,
  months,
  selectedMonth,
  onSelectMonth,
}: ReportViewProps) {
  const [downloading, setDownloading] = useState(false)
  const [downloadError, setDownloadError] = useState<string | null>(null)

  const handleDownload = async () => {
    try {
      setDownloading(true)
      setDownloadError(null)
      await downloadReportPdf(selectedMonth)
    } catch (err) {
      setDownloadError(err instanceof Error ? err.message : 'Failed to download PDF')
    } finally {
      setDownloading(false)
    }
  }

  const { cash_flow } = report
  const isPositiveSavings = cash_flow.net_savings_minor >= 0

  return (
    <div className="space-y-6 max-w-7xl mx-auto print:p-0 animate-in fade-in duration-200">
      {/* 1. Header Toolbar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-hairline print:border-none print:p-0">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-semibold tracking-tight text-content-primary">
              Financial Statement Audit Report
            </h1>
            <span className="text-[10px] font-medium px-2 py-0.5 rounded-full uppercase tracking-wider bg-canvas border border-hairline text-content-muted">
              {report.currency}
            </span>
          </div>
          <p className="text-xs text-content-muted mt-1">
            Comprehensive executive summary, budget variance, and decision support for {report.month_name}
          </p>
        </div>

        <div className="flex items-center gap-2 print:hidden self-start sm:self-auto flex-wrap">
          {/* Month Selector */}
          <div className="relative">
            <select
              value={selectedMonth}
              onChange={(e) => onSelectMonth(e.target.value)}
              className="appearance-none bg-surface border border-hairline text-content-primary text-xs font-medium rounded-lg pl-8 pr-7 py-1.5 hover:bg-canvas focus:outline-none focus:ring-1 focus:ring-[#4F46E5] cursor-pointer"
            >
              {months.map((m) => (
                <option key={m.month} value={m.month}>
                  {m.month_name} ({m.transaction_count} txns)
                </option>
              ))}
            </select>
            <CalendarDaysIcon className="w-3.5 h-3.5 text-content-muted absolute left-2.5 top-2 pointer-events-none" />
          </div>

          {/* Print Button */}
          <button
            type="button"
            onClick={() => window.print()}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-content-primary bg-surface border border-hairline rounded-lg hover:bg-canvas transition-colors cursor-pointer"
            title="Print Report"
          >
            <PrinterIcon className="w-3.5 h-3.5 text-content-muted" />
            <span className="hidden sm:inline">Print</span>
          </button>

          {/* Download PDF */}
          <button
            type="button"
            onClick={handleDownload}
            disabled={downloading}
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-medium text-white bg-[#4F46E5] hover:bg-[#4338CA] rounded-lg disabled:opacity-40 transition-colors cursor-pointer"
          >
            <ArrowDownTrayIcon className="w-3.5 h-3.5" />
            <span>{downloading ? 'Exporting PDF...' : 'Download PDF'}</span>
          </button>
        </div>
      </div>

      {downloadError && (
        <div className="p-3 bg-rose-500/8 border border-rose-500/20 text-rose-800 dark:text-rose-300 rounded-lg text-xs print:hidden">
          {downloadError}
        </div>
      )}

      {/* 2. Non-Advisor Disclaimer Banner */}
      <div className="flex items-start gap-3 p-3.5 bg-canvas border border-hairline rounded-xl text-content-muted text-xs">
        <ShieldExclamationIcon className="w-4 h-4 text-content-muted shrink-0 mt-0.5" />
        <div className="leading-relaxed">
          <span className="font-medium text-content-primary">INFORMATIONAL USE ONLY: </span>
          {report.disclaimer}
        </div>
      </div>

      {/* 3. Executive Cash Flow Summary Stats (Zero-box style or clean hairline row) */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 py-2">
        <div className="space-y-1">
          <span className="text-[11px] font-medium text-content-muted block">
            Total Inflow
          </span>
          <div className="text-2xl font-semibold tabular-nums text-emerald-600 dark:text-emerald-400">
            {cash_flow.income_display}
          </div>
          <span className="text-[11px] text-content-muted block">Credits & income</span>
        </div>

        <div className="space-y-1 sm:border-l sm:border-hairline sm:pl-4">
          <span className="text-[11px] font-medium text-content-muted block">
            Total Outflow
          </span>
          <div className="text-2xl font-semibold tabular-nums text-content-primary">
            {cash_flow.expense_display}
          </div>
          <div className="flex items-center gap-1 text-[11px] text-content-muted">
            {cash_flow.mom_change_pct !== null && (
              <>
                {cash_flow.mom_change_pct > 0 ? (
                  <span className="flex items-center text-rose-600 dark:text-rose-400 font-medium tabular-nums">
                    <ArrowTrendingUpIcon className="w-3 h-3 mr-0.5" />
                    +{cash_flow.mom_change_pct}% MoM
                  </span>
                ) : (
                  <span className="flex items-center text-emerald-600 dark:text-emerald-400 font-medium tabular-nums">
                    <ArrowTrendingDownIcon className="w-3 h-3 mr-0.5" />
                    {cash_flow.mom_change_pct}% MoM
                  </span>
                )}
              </>
            )}
          </div>
        </div>

        <div className="space-y-1 lg:border-l lg:border-hairline lg:pl-4">
          <span className="text-[11px] font-medium text-content-muted block">
            Net Surplus / Savings
          </span>
          <div
            className={`text-2xl font-semibold tabular-nums ${
              isPositiveSavings
                ? 'text-[#4F46E5] dark:text-[#818CF8]'
                : 'text-rose-600 dark:text-rose-400'
            }`}
          >
            {cash_flow.net_savings_display}
          </div>
          <span className="text-[11px] text-content-muted block">
            {isPositiveSavings ? 'Unallocated capital' : 'Net period deficit'}
          </span>
        </div>

        <div className="space-y-1 border-l border-hairline pl-4">
          <span className="text-[11px] font-medium text-content-muted block">
            Savings Rate
          </span>
          <div className="text-2xl font-semibold tabular-nums text-content-primary">
            {cash_flow.savings_rate_pct}%
          </div>
          <span className="text-[11px] text-content-muted block truncate tabular-nums">
            Fixed: {cash_flow.recurring_spend_display}
          </span>
        </div>
      </div>

      {/* 4. Executive Narrative Highlight Card */}
      <div className="bg-surface p-5 rounded-xl border border-hairline shadow-2xs space-y-2">
        <div className="flex items-center gap-2">
          <SparklesIcon className="w-4 h-4 text-[#4F46E5] dark:text-[#818CF8]" />
          <h3 className="text-xs font-semibold uppercase tracking-wider text-content-primary">
            Executive Financial Narrative
          </h3>
        </div>
        <p className="text-xs sm:text-sm text-content-primary leading-relaxed font-normal">
          {report.narrative}
        </p>
      </div>

      {/* 5. Main 2-Column Content Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column (7 cols): Categories, Budgets, Recurring */}
        <div className="lg:col-span-7 space-y-6">
          {/* Top Spending Categories */}
          <div className="bg-surface rounded-xl border border-hairline p-5 shadow-2xs">
            <h3 className="font-semibold text-content-primary text-sm mb-3">
              Top Spending Categories
            </h3>
            <div className="space-y-3">
              {report.top_categories.map((c) => (
                <div key={c.category} className="space-y-1">
                  <div className="flex justify-between text-xs">
                    <span className="font-medium text-content-primary">
                      {c.category}
                    </span>
                    <div className="flex items-center gap-2">
                      <span className="text-[11px] text-content-muted tabular-nums">
                        {c.transaction_count} txns ({c.pct_of_total}%)
                      </span>
                      <span className="font-semibold tabular-nums text-content-primary">
                        {c.amount_display}
                      </span>
                    </div>
                  </div>
                  <div className="w-full bg-canvas border border-hairline rounded-full h-1.5 overflow-hidden">
                    <div
                      className="bg-[#4F46E5] dark:bg-[#818CF8] h-full rounded-full transition-all duration-300"
                      style={{ width: `${Math.min(100, c.pct_of_total)}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Budget Adherence */}
          {report.budgets.length > 0 && (
            <div className="bg-surface rounded-xl border border-hairline p-5 shadow-2xs">
              <h3 className="font-semibold text-content-primary text-sm mb-3">
                Budget Health & Variance
              </h3>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-hairline text-xs">
                  <thead>
                    <tr className="text-left font-medium text-content-muted uppercase tracking-wider text-[10px]">
                      <th className="pb-2.5">Category</th>
                      <th className="pb-2.5 text-right">Limit</th>
                      <th className="pb-2.5 text-right">Spent</th>
                      <th className="pb-2.5 text-right">Remaining</th>
                      <th className="pb-2.5 text-right">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-hairline text-content-primary">
                    {report.budgets.map((b) => {
                      const isExceeded = b.status === 'exceeded'
                      const isWarning = b.status === 'warning'
                      return (
                        <tr key={b.category} className="hover:bg-canvas/50 transition-colors">
                          <td className="py-2.5 font-medium text-content-primary">
                            {b.category}
                          </td>
                          <td className="py-2.5 text-right tabular-nums text-content-muted">
                            {b.monthly_limit_display}
                          </td>
                          <td className="py-2.5 text-right tabular-nums font-semibold text-content-primary">
                            {b.spent_display}
                          </td>
                          <td className="py-2.5 text-right tabular-nums text-content-muted">
                            {b.remaining_display}
                          </td>
                          <td className="py-2.5 text-right">
                            <span
                              className={`text-[9px] font-medium uppercase tracking-wider px-2 py-0.5 rounded-full ${
                                isExceeded
                                  ? 'bg-rose-500/10 text-rose-700 dark:text-rose-400 border border-rose-500/20'
                                  : isWarning
                                  ? 'bg-amber-500/10 text-amber-700 dark:text-amber-400 border border-amber-500/20'
                                  : 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-500/20'
                              }`}
                            >
                              {b.status?.replace('_', ' ')} ({b.spent_pct}%)
                            </span>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Subscriptions */}
          {report.recurring.length > 0 && (
            <div className="bg-surface rounded-xl border border-hairline p-5 shadow-2xs">
              <h3 className="font-semibold text-content-primary text-sm mb-3">
                Recurring Commitments
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                {report.recurring.map((r) => (
                  <div
                    key={r.id}
                    className="p-3 bg-canvas rounded-lg border border-hairline flex items-center justify-between"
                  >
                    <div>
                      <div className="text-xs font-medium text-content-primary">
                        {r.merchant}
                      </div>
                      <div className="text-[10px] text-content-muted capitalize">
                        {r.frequency} • {r.status.replace('_', ' ')}
                      </div>
                    </div>
                    <div className="text-xs font-semibold tabular-nums text-content-primary">
                      {r.avg_amount_display}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right Column (5 cols): Action Checklist, Anomalies, Goals */}
        <div className="lg:col-span-5 space-y-6">
          {/* Actionable Decision Checklist */}
          <ActionChecklist items={report.action_items} month={report.month} />

          {/* Detected Anomalies */}
          {report.anomalies.length > 0 && (
            <div className="bg-surface rounded-xl border border-amber-500/20 p-5 shadow-2xs">
              <div className="flex items-center gap-2 mb-3">
                <ExclamationTriangleIcon className="w-4 h-4 text-amber-600 dark:text-amber-400" />
                <h3 className="font-semibold text-content-primary text-sm">
                  Statement Flags & Anomalies
                </h3>
              </div>
              <div className="space-y-2">
                {report.anomalies.map((a) => (
                  <div
                    key={a.id}
                    className="p-3 bg-canvas rounded-lg border border-hairline text-xs text-content-primary"
                  >
                    <span className="font-medium text-rose-600 dark:text-rose-400 uppercase tracking-wider text-[10px] block mb-0.5">
                      {a.type.replace('_', ' ')}
                    </span>
                    {a.text}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Savings Goals Status */}
          {report.goals.length > 0 && (
            <div className="bg-surface rounded-xl border border-hairline p-5 shadow-2xs">
              <h3 className="font-semibold text-content-primary text-sm mb-3">
                Savings Goals Pace
              </h3>
              <div className="space-y-3">
                {report.goals.map((g) => (
                  <div
                    key={g.id}
                    className="p-3 bg-canvas rounded-lg border border-hairline space-y-1.5"
                  >
                    <div className="flex justify-between text-xs">
                      <span className="font-medium text-content-primary">{g.name}</span>
                      <span className="font-semibold tabular-nums text-[#4F46E5] dark:text-[#818CF8]">
                        {g.progress_pct}%
                      </span>
                    </div>
                    <div className="w-full bg-surface border border-hairline rounded-full h-1.5 overflow-hidden">
                      <div
                        className="bg-[#4F46E5] dark:bg-[#818CF8] h-full rounded-full"
                        style={{ width: `${g.progress_pct}%` }}
                      />
                    </div>
                    <div className="flex justify-between text-[10px] text-content-muted tabular-nums">
                      <span>Saved: {g.current_amount_display}</span>
                      <span>Target: {g.target_amount_display}</span>
                    </div>
                    {g.required_monthly_savings_display && (
                      <div className="text-[10px] text-content-muted pt-0.5 tabular-nums">
                        Required:{' '}
                        <strong className="text-content-primary font-medium">
                          {g.required_monthly_savings_display}/mo
                        </strong>
                        {g.on_track === true && (
                          <span className="ml-1 text-emerald-600 dark:text-emerald-400 font-medium">
                            (On pace)
                          </span>
                        )}
                        {g.on_track === false && (
                          <span className="ml-1 text-amber-600 dark:text-amber-400 font-medium">
                            (Behind pace)
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
