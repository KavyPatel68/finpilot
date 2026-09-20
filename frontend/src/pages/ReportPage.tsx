import { useState, useEffect } from 'react'
import { getAvailableReportMonths, getMonthlyReport } from '../api/reports'
import { useMonth } from '../context/MonthContext'
import { MonthlyReportResponse, ReportMonth } from '../types'
import { ReportView } from '../components/Report/ReportView'
import { LoadingSpinner } from '../components/common/LoadingSpinner'
import { EmptyState } from '../components/common/EmptyState'
import { ErrorState } from '../components/common/ErrorState'

export function ReportPage() {
  const { selectedMonth, setSelectedMonth } = useMonth()
  const [months, setMonths] = useState<ReportMonth[]>([])
  const [report, setReport] = useState<MonthlyReportResponse | null>(null)
  const [loadingMonths, setLoadingMonths] = useState(true)
  const [loadingReport, setLoadingReport] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // 1. Fetch available report months on mount
  useEffect(() => {
    let isMounted = true
    async function fetchMonths() {
      try {
        setLoadingMonths(true)
        setError(null)
        const data = await getAvailableReportMonths()
        if (isMounted) {
          setMonths(data)
          // If global month is not in available report months, set to latest report month
          if (data.length > 0 && (!selectedMonth || !data.some((m) => m.month === selectedMonth))) {
            setSelectedMonth(data[0].month)
          }
        }
      } catch (err) {
        if (isMounted) {
          setError(err instanceof Error ? err.message : 'Failed to load report periods')
        }
      } finally {
        if (isMounted) {
          setLoadingMonths(false)
        }
      }
    }
    fetchMonths()
    return () => {
      isMounted = false
    }
  }, [])

  // 2. Fetch report data when selectedMonth changes
  useEffect(() => {
    if (!selectedMonth) return

    let isMounted = true
    async function fetchReport() {
      try {
        setLoadingReport(true)
        setError(null)
        const data = await getMonthlyReport(selectedMonth)
        if (isMounted) {
          setReport(data)
        }
      } catch (err) {
        if (isMounted) {
          setError(err instanceof Error ? err.message : 'Failed to load monthly report')
        }
      } finally {
        if (isMounted) {
          setLoadingReport(false)
        }
      }
    }
    fetchReport()
    return () => {
      isMounted = false
    }
  }, [selectedMonth])

  if (loadingMonths) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] gap-3">
        <LoadingSpinner />
        <span className="text-xs text-content-muted font-medium">Loading statement audit periods...</span>
      </div>
    )
  }

  if (error && !report) {
    return (
      <div className="p-6 max-w-7xl mx-auto">
        <ErrorState
          message={error}
          onRetry={() => {
            if (selectedMonth) {
              setReport(null)
              getMonthlyReport(selectedMonth).then(setReport).catch((e) => setError(e.message))
            }
          }}
        />
      </div>
    )
  }

  if (months.length === 0) {
    return (
      <div className="p-6 max-w-7xl mx-auto">
        <EmptyState
          title="No Statement Periods Available"
          description="Upload bank or credit card statements to generate comprehensive monthly audit reports, budget variance, and actionable decision checklists."
          action={{
            label: 'Upload Statements',
            href: '/upload',
          }}
        />
      </div>
    )
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-10">
      {loadingReport ? (
        <div className="flex flex-col items-center justify-center min-h-[400px] gap-3">
          <LoadingSpinner />
          <span className="text-xs text-content-muted font-medium">
            Generating statement audit report for {selectedMonth}...
          </span>
        </div>
      ) : report ? (
        <ReportView
          report={report}
          months={months}
          selectedMonth={selectedMonth}
          onSelectMonth={setSelectedMonth}
        />
      ) : null}
    </div>
  )
}
