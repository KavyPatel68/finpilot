import { apiFetch } from './client'
import { MonthlyReportResponse, ReportMonth } from '../types'

export async function getAvailableReportMonths(userId = 1): Promise<ReportMonth[]> {
  const data = await apiFetch<{ months: ReportMonth[] }>(`/api/reports/months?user_id=${userId}`)
  return data.months
}

export async function getMonthlyReport(month: string, userId = 1): Promise<MonthlyReportResponse> {
  return apiFetch<MonthlyReportResponse>(`/api/reports/${month}?user_id=${userId}`)
}

export function getReportPdfUrl(month: string, userId = 1): string {
  return `/api/reports/${month}/pdf?user_id=${userId}`
}

export async function downloadReportPdf(month: string, userId = 1): Promise<void> {
  const url = getReportPdfUrl(month, userId)
  const response = await fetch(url)
  if (!response.ok) {
    throw new Error(`Failed to generate PDF: ${response.statusText}`)
  }
  const blob = await response.blob()
  const downloadUrl = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = downloadUrl
  a.download = `FinPilot_Report_${month}.pdf`
  document.body.appendChild(a)
  a.click()
  window.URL.revokeObjectURL(downloadUrl)
  document.body.removeChild(a)
}
