import React, { useState } from 'react'
import type { ColumnMapping } from '../../types'

interface MappingModalProps {
  documentId: number
  filename: string
  initialMapping?: ColumnMapping | null
  onConfirm: (docId: number, mapping: ColumnMapping) => Promise<void>
  onCancel: () => void
  isLoading: boolean
}

export function MappingModal({
  documentId,
  filename,
  initialMapping,
  onConfirm,
  onCancel,
  isLoading,
}: MappingModalProps) {
  const headers = initialMapping?.headers || []
  const previewRows = initialMapping?.preview_rows || []

  const [dateCol, setDateCol] = useState(initialMapping?.date_col || '')
  const [descCol, setDescCol] = useState(initialMapping?.description_col || '')
  const [debitCol, setDebitCol] = useState(initialMapping?.debit_col || '')
  const [creditCol, setCreditCol] = useState(initialMapping?.credit_col || '')
  const [amountCol, setAmountCol] = useState(initialMapping?.amount_col || '')
  const [balanceCol, setBalanceCol] = useState(initialMapping?.balance_col || '')
  const [directionCol, setDirectionCol] = useState(initialMapping?.direction_col || '')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const mapping: ColumnMapping = {
      date_col: dateCol.trim() || null,
      description_col: descCol.trim() || null,
      debit_col: debitCol.trim() || null,
      credit_col: creditCol.trim() || null,
      amount_col: amountCol.trim() || null,
      balance_col: balanceCol.trim() || null,
      direction_col: directionCol.trim() || null,
      confidence: 1.0,
      needs_confirmation: false,
    }
    await onConfirm(documentId, mapping)
  }

  const renderFieldSelector = (
    label: string,
    value: string,
    onChange: (val: string) => void,
    required = false,
    placeholder = 'Select column'
  ) => {
    if (headers.length > 0) {
      return (
        <div>
          <label className="block text-xs font-medium text-content-primary mb-1">
            {label} {required && <span className="text-rose-500">*</span>}
          </label>
          <select
            value={value}
            onChange={(e) => onChange(e.target.value)}
            className="w-full rounded-lg border border-hairline px-3 py-1.5 text-xs bg-canvas text-content-primary focus:outline-none focus:ring-1 focus:ring-[#4F46E5]"
          >
            <option value="">-- {placeholder} --</option>
            {headers.map((h) => (
              <option key={h} value={h}>
                {h}
              </option>
            ))}
          </select>
        </div>
      )
    }

    return (
      <div>
        <label className="block text-xs font-medium text-content-primary mb-1">
          {label} {required && <span className="text-rose-500">*</span>}
        </label>
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          className="w-full rounded-lg border border-hairline px-3 py-1.5 text-xs bg-canvas text-content-primary focus:outline-none focus:ring-1 focus:ring-[#4F46E5]"
        />
      </div>
    )
  }

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-black/40 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-surface border border-hairline rounded-xl max-w-2xl w-full p-6 shadow-xl space-y-5 animate-in fade-in zoom-in-95 duration-150 max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-start justify-between border-b border-hairline pb-3 flex-shrink-0">
          <div>
            <h2 className="text-base font-semibold text-content-primary">Confirm Column Mapping</h2>
            <p className="text-xs text-content-muted mt-0.5">
              We couldn't automatically detect columns in <span className="font-medium text-content-primary">{filename}</span> with high confidence. Please verify or match the columns below.
            </p>
          </div>
          <button
            onClick={onCancel}
            className="text-content-muted hover:text-content-primary rounded p-1 text-sm font-semibold"
          >
            ✕
          </button>
        </div>

        {/* Scrollable Content */}
        <div className="overflow-y-auto space-y-5 pr-1 flex-1">
          {/* Statement Preview Table */}
          {previewRows.length > 0 && (
            <div className="border border-hairline rounded-lg overflow-hidden bg-canvas">
              <div className="px-3 py-2 border-b border-hairline flex items-center justify-between">
                <span className="text-xs font-medium text-content-primary">Statement Preview (Top {previewRows.length} Rows)</span>
                <span className="text-[11px] text-content-muted tabular-nums">{headers.length} Columns detected</span>
              </div>
              <div className="overflow-x-auto max-h-48 text-xs">
                <table className="min-w-full divide-y divide-hairline">
                  <thead className="bg-surface">
                    <tr>
                      {headers.map((h) => (
                        <th
                          key={h}
                          className="px-3 py-2 text-left text-[11px] font-medium text-content-muted whitespace-nowrap"
                        >
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="bg-surface divide-y divide-hairline">
                    {previewRows.map((row, idx) => (
                      <tr key={idx} className="hover:bg-canvas/50">
                        {headers.map((h) => (
                          <td
                            key={h}
                            className="px-3 py-1.5 text-content-primary whitespace-nowrap tabular-nums text-[11px]"
                          >
                            {String(row[h] ?? '')}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Form */}
          <form id="mapping-form" onSubmit={handleSubmit} className="space-y-4 text-xs">
            {/* Required Core Columns */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {renderFieldSelector('Date Column', dateCol, setDateCol, true, 'Date / Txn Date')}
              {renderFieldSelector('Description Column', descCol, setDescCol, true, 'Narration / Description')}
            </div>

            {/* Option A: Debit & Credit */}
            <div className="border border-hairline rounded-lg p-3.5 bg-canvas/40 space-y-3">
              <p className="text-xs font-medium text-content-primary">
                Option A: Separate Debit & Credit columns
              </p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {renderFieldSelector('Debit / Withdrawal Column', debitCol, setDebitCol, false, 'Debit / Withdrawal')}
                {renderFieldSelector('Credit / Deposit Column', creditCol, setCreditCol, false, 'Credit / Deposit')}
              </div>
            </div>

            {/* Option B: Single Amount */}
            <div className="border border-hairline rounded-lg p-3.5 bg-canvas/40 space-y-3">
              <p className="text-xs font-medium text-content-primary">
                Option B: Single Amount column (signed or with Dr/Cr column)
              </p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {renderFieldSelector('Amount Column', amountCol, setAmountCol, false, 'Amount')}
                {renderFieldSelector('Direction (Dr/Cr) Column', directionCol, setDirectionCol, false, 'Type / Dr/Cr')}
              </div>
            </div>

            {/* Balance Column */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-1">
              {renderFieldSelector('Closing Balance Column (Optional)', balanceCol, setBalanceCol, false, 'Balance / Closing Balance')}
            </div>
          </form>
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-3 pt-3 border-t border-hairline flex-shrink-0">
          <button
            type="button"
            onClick={onCancel}
            className="px-3.5 py-1.5 text-xs text-content-muted hover:text-content-primary font-medium rounded-lg border border-hairline hover:bg-canvas transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            form="mapping-form"
            disabled={isLoading || !dateCol || !descCol || (!debitCol && !creditCol && !amountCol)}
            className="px-4 py-1.5 text-xs bg-[#4F46E5] text-white font-medium rounded-lg hover:bg-[#4338CA] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            {isLoading ? 'Importing...' : 'Confirm & Process'}
          </button>
        </div>
      </div>
    </div>
  )
}
