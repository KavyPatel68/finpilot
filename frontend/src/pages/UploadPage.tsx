import React, { useState, useEffect } from 'react'
import {
  SparklesIcon,
  DocumentArrowUpIcon,
  TrashIcon,
  ArrowPathIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
  DocumentTextIcon,
  InformationCircleIcon,
} from '@heroicons/react/24/outline'
import { UploadZone } from '../components/Upload/UploadZone'
import { ParseStatusTable } from '../components/Upload/ParseStatusTable'
import { MappingModal } from '../components/Upload/MappingModal'
import {
  uploadDocument,
  confirmMapping,
  getDocuments,
  deleteDocument,
  seedDemoData,
} from '../api/upload'
import type { Document, UploadResponse, ColumnMapping } from '../types'
import { useMonth } from '../context/MonthContext'
import { LoadingSpinner } from '../components/common/LoadingSpinner'

export function UploadPage() {
  const [documents, setDocuments] = useState<Document[]>([])
  const [isLoadingList, setIsLoadingList] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [isSeedingDemo, setIsSeedingDemo] = useState(false)
  const [lastUploadResult, setLastUploadResult] = useState<UploadResponse | null>(null)
  const [notification, setNotification] = useState<{ type: 'success' | 'error'; message: string } | null>(null)
  const [mappingModalDoc, setMappingModalDoc] = useState<{
    id: number
    filename: string
    mapping?: ColumnMapping | null
  } | null>(null)

  const { refreshMonths } = useMonth()

  const loadDocuments = async () => {
    setIsLoadingList(true)
    try {
      const data = await getDocuments(1)
      setDocuments(data)
    } catch (err) {
      console.error('Failed to load documents:', err)
    } finally {
      setIsLoadingList(false)
    }
  }

  useEffect(() => {
    loadDocuments()
  }, [])

  const handleUpload = async (file: File, accountId: number, password?: string) => {
    setIsUploading(true)
    setNotification(null)
    try {
      const result = await uploadDocument(file, accountId, 1, password)
      setLastUploadResult(result)

      if (result.status === 'needs_mapping') {
        setMappingModalDoc({
          id: result.document_id,
          filename: result.filename,
          mapping: {
            ...result.mapping_suggestion,
            headers: result.headers || result.mapping_suggestion?.headers || [],
            preview_rows: result.preview_rows || result.mapping_suggestion?.preview_rows || [],
          },
        })
      } else {
        await loadDocuments()
        await refreshMonths()
        setNotification({
          type: 'success',
          message: `Successfully imported ${result.imported_count} transactions from ${result.filename} (${result.duplicate_count} duplicates skipped).`,
        })
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Upload failed'
      setNotification({ type: 'error', message: msg })
    } finally {
      setIsUploading(false)
    }
  }

  const handleConfirmMapping = async (docId: number, mapping: ColumnMapping) => {
    setIsUploading(true)
    setNotification(null)
    try {
      const result = await confirmMapping(docId, mapping)
      setLastUploadResult(result)
      setMappingModalDoc(null)
      await loadDocuments()
      await refreshMonths()
      setNotification({
        type: 'success',
        message: `Mapped and imported ${result.imported_count} transactions from ${result.filename}.`,
      })
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to confirm mapping'
      setNotification({ type: 'error', message: msg })
    } finally {
      setIsUploading(false)
    }
  }

  const handleLoadDemo = async () => {
    setIsSeedingDemo(true)
    setNotification(null)
    try {
      const res = await seedDemoData(1)
      await loadDocuments()
      await refreshMonths()
      setNotification({
        type: 'success',
        message: `${res.message} Interactive charts, recurring items, and ledger are ready!`,
      })
    } catch (err) {
      setNotification({
        type: 'error',
        message: 'Failed to load demo data. Make sure backend is running.',
      })
    } finally {
      setIsSeedingDemo(false)
    }
  }

  const handleDelete = async (docId: number) => {
    if (!confirm('Delete this statement document and remove all its imported transactions?')) return
    try {
      await deleteDocument(docId)
      await loadDocuments()
      await refreshMonths()
      if (lastUploadResult?.document_id === docId) {
        setLastUploadResult(null)
      }
      setNotification({
        type: 'success',
        message: 'Statement deleted successfully.',
      })
    } catch (err) {
      setNotification({
        type: 'error',
        message: 'Failed to delete statement.',
      })
    }
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'done':
      case 'completed':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-500/20">
            <CheckCircleIcon className="w-3 h-3" /> Processed
          </span>
        )
      case 'processing':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium bg-indigo-500/10 text-indigo-700 dark:text-indigo-400 border border-indigo-500/20">
            <ArrowPathIcon className="w-3 h-3 animate-spin" /> Processing
          </span>
        )
      case 'needs_mapping':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium bg-amber-500/10 text-amber-700 dark:text-amber-400 border border-amber-500/20">
            <InformationCircleIcon className="w-3 h-3" /> Needs Mapping
          </span>
        )
      case 'error':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium bg-rose-500/10 text-rose-700 dark:text-rose-400 border border-rose-500/20">
            <ExclamationCircleIcon className="w-3 h-3" /> Failed
          </span>
        )
      default:
        return (
          <span className="px-2 py-0.5 rounded-full text-[11px] font-medium bg-canvas text-content-muted border border-hairline">
            {status}
          </span>
        )
    }
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Page Header with Minimal Secondary Outlined Demo Loader */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-2 border-b border-hairline">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-content-primary">
            Upload Financial Statements
          </h1>
          <p className="text-xs text-content-muted mt-1">
            Import CSV, Excel (.xlsx), or PDF statements. FinPilot deduplicates, maps columns, and
            auto-categorizes transactions.
          </p>
        </div>

        {/* Load Demo Data Button (Clean Outline Button) */}
        <button
          onClick={handleLoadDemo}
          disabled={isSeedingDemo || isUploading}
          className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-medium transition-colors
            border border-hairline bg-surface hover:bg-canvas text-content-primary
            disabled:opacity-40 disabled:cursor-not-allowed"
          title="Instantly load 6 months of pre-built synthetic transactions with planted scenarios"
        >
          <SparklesIcon className={`w-3.5 h-3.5 text-[#4F46E5] dark:text-[#818CF8] ${isSeedingDemo ? 'animate-spin' : ''}`} />
          <span>{isSeedingDemo ? 'Loading Demo...' : 'Load Demo Data (6 Months)'}</span>
        </button>
      </div>

      {/* Notification Toast */}
      {notification && (
        <div
          className={`p-3 rounded-lg border text-xs flex items-center justify-between transition-colors ${
            notification.type === 'success'
              ? 'bg-emerald-500/8 border-emerald-500/20 text-emerald-800 dark:text-emerald-300'
              : 'bg-rose-500/8 border-rose-500/20 text-rose-800 dark:text-rose-300'
          }`}
        >
          <div className="flex items-center gap-2">
            {notification.type === 'success' ? (
              <CheckCircleIcon className="w-4 h-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
            ) : (
              <ExclamationCircleIcon className="w-4 h-4 text-rose-600 dark:text-rose-400 shrink-0" />
            )}
            <span className="font-medium">{notification.message}</span>
          </div>
          <button
            onClick={() => setNotification(null)}
            className="p-1 opacity-60 hover:opacity-100 font-medium ml-2"
          >
            ✕
          </button>
        </div>
      )}

      {/* Main Drag & Drop Zone */}
      <UploadZone onUpload={handleUpload} isLoading={isUploading} />

      {/* Last Upload Outcome Summary */}
      {lastUploadResult && (
        <div className="rounded-xl border border-hairline p-5 bg-surface space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-hairline">
            <div className="flex items-center gap-2.5">
              <div className="w-7 h-7 rounded-lg bg-canvas border border-hairline flex items-center justify-center text-content-muted">
                <DocumentArrowUpIcon className="w-4 h-4" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-content-primary">
                  Ingestion Report: {lastUploadResult.filename}
                </h3>
                <p className="text-[11px] text-content-muted">Deduplication and ledger intake summary</p>
              </div>
            </div>
            {getStatusBadge(lastUploadResult.status)}
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div className="p-3 rounded-lg bg-canvas border border-hairline text-center">
              <span className="text-[11px] font-medium text-content-muted block">
                Total Rows
              </span>
              <span className="text-2xl font-semibold tabular-nums text-content-primary mt-1 block">
                {lastUploadResult.row_count}
              </span>
            </div>

            <div className="p-3 rounded-lg bg-canvas border border-hairline text-center">
              <span className="text-[11px] font-medium text-emerald-700 dark:text-emerald-400 block">
                Imported Transactions
              </span>
              <span className="text-2xl font-semibold tabular-nums text-emerald-700 dark:text-emerald-400 mt-1 block">
                {lastUploadResult.imported_count}
              </span>
            </div>

            <div className="p-3 rounded-lg bg-canvas border border-hairline text-center">
              <span className="text-[11px] font-medium text-content-muted block">
                Duplicates Skipped
              </span>
              <span className="text-2xl font-semibold tabular-nums text-content-muted mt-1 block">
                {lastUploadResult.duplicate_count}
              </span>
            </div>
          </div>

          {/* Parse warnings & skipped rows */}
          <ParseStatusTable errors={lastUploadResult.parse_errors} />
        </div>
      )}

      {/* Statement Intake History */}
      <div className="rounded-xl border border-hairline bg-surface overflow-hidden">
        <div className="px-5 py-4 border-b border-hairline flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold text-content-primary">
              Statement Import History
            </h3>
            <p className="text-[11px] text-content-muted">Previously uploaded files and record counts</p>
          </div>

          <button
            onClick={loadDocuments}
            disabled={isLoadingList}
            className="flex items-center gap-1.5 text-xs font-medium text-[#4F46E5] dark:text-[#818CF8] hover:underline"
          >
            <ArrowPathIcon className={`w-3.5 h-3.5 ${isLoadingList ? 'animate-spin' : ''}`} />
            <span>Refresh History</span>
          </button>
        </div>

        {isLoadingList ? (
          <div className="p-12 flex justify-center">
            <LoadingSpinner />
          </div>
        ) : documents.length === 0 ? (
          <div className="p-12 text-center text-xs text-content-muted">
            No statements uploaded yet. Drag and drop a file above or click &ldquo;Load Demo
            Data&rdquo; to begin.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead className="bg-canvas text-content-muted font-medium border-b border-hairline">
                <tr>
                  <th className="px-5 py-3">Statement File</th>
                  <th className="px-4 py-3">Type</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3 text-right">Imported</th>
                  <th className="px-4 py-3 text-right">Duplicates</th>
                  <th className="px-4 py-3">Uploaded</th>
                  <th className="px-5 py-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-hairline text-content-primary">
                {documents.map((doc) => (
                  <tr
                    key={doc.id}
                    className="hover:bg-canvas/50 transition-colors"
                  >
                    <td className="px-5 py-3.5 font-medium text-content-primary flex items-center gap-2">
                      <DocumentTextIcon className="w-4 h-4 text-content-muted shrink-0" />
                      <span className="truncate max-w-xs">{doc.filename}</span>
                    </td>
                    <td className="px-4 py-3.5">
                      <span className="px-1.5 py-0.5 rounded text-[10px] font-medium uppercase tracking-wider bg-canvas border border-hairline text-content-muted">
                        {doc.file_type}
                      </span>
                    </td>
                    <td className="px-4 py-3.5">{getStatusBadge(doc.status)}</td>
                    <td className="px-4 py-3.5 text-right font-medium tabular-nums text-emerald-700 dark:text-emerald-400">
                      {doc.imported_count ?? '—'}
                    </td>
                    <td className="px-4 py-3.5 text-right tabular-nums text-content-muted">
                      {doc.duplicate_count ?? '—'}
                    </td>
                    <td className="px-4 py-3.5 text-content-muted tabular-nums text-[11px]">
                      {new Date(doc.uploaded_at).toLocaleDateString()}
                    </td>
                    <td className="px-5 py-3.5 text-right">
                      <button
                        onClick={() => handleDelete(doc.id)}
                        className="p-1 text-content-muted hover:text-rose-600 dark:hover:text-rose-400 rounded transition-colors"
                        title="Delete statement and transactions"
                      >
                        <TrashIcon className="w-3.5 h-3.5" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Column Mapping Modal */}
      {mappingModalDoc && (
        <MappingModal
          documentId={mappingModalDoc.id}
          filename={mappingModalDoc.filename}
          initialMapping={mappingModalDoc.mapping}
          onConfirm={handleConfirmMapping}
          onCancel={() => setMappingModalDoc(null)}
          isLoading={isUploading}
        />
      )}
    </div>
  )
}
