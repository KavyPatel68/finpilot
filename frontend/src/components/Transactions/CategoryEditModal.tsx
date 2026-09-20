import React, { useState } from 'react'
import { XMarkIcon } from '@heroicons/react/24/outline'
import type { Transaction } from '../../types'

interface CategoryEditModalProps {
  transaction: Transaction
  categories: string[]
  onSave: (txId: number, newCategory: string, createRule: boolean) => Promise<void>
  onClose: () => void
  isLoading: boolean
}

export function CategoryEditModal({
  transaction,
  categories,
  onSave,
  onClose,
  isLoading,
}: CategoryEditModalProps) {
  const [selectedCategory, setSelectedCategory] = useState(transaction.category || 'Other')
  const [createRule, setCreateRule] = useState(true)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    await onSave(transaction.id, selectedCategory, createRule)
  }

  const merchantDisplayName =
    transaction.merchant_normalized || transaction.raw_description.split('/')[0]

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-black/40 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-surface border border-hairline rounded-xl max-w-md w-full p-6 shadow-xl space-y-4 animate-in fade-in zoom-in-95 duration-150">
        <div className="flex items-start justify-between border-b pb-3 border-hairline">
          <div>
            <h2 className="text-sm font-semibold text-content-primary">Edit Category</h2>
            <p className="text-[11px] text-content-muted mt-0.5 truncate max-w-xs">
              {transaction.raw_description}
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-content-muted hover:text-content-primary rounded p-1"
          >
            <XMarkIcon className="w-4 h-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-content-primary mb-1">
              Select Category
            </label>
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="w-full rounded-lg border border-hairline px-3 py-1.5 text-xs font-medium bg-canvas text-content-primary focus:outline-none focus:ring-1 focus:ring-[#4F46E5]"
            >
              {categories.map((cat) => (
                <option key={cat} value={cat}>
                  {cat}
                </option>
              ))}
            </select>
          </div>

          <div className="bg-canvas border border-hairline rounded-lg p-3 text-xs text-content-muted space-y-1">
            <div className="flex justify-between">
              <span>Current Source:</span>
              <span className="font-medium text-content-primary uppercase text-[10px]">
                {transaction.category_source || 'unclassified'}
              </span>
            </div>
            {transaction.confidence !== null && (
              <div className="flex justify-between">
                <span>Confidence:</span>
                <span className="font-medium tabular-nums text-content-primary">
                  {Math.round((transaction.confidence || 0) * 100)}%
                </span>
              </div>
            )}
          </div>

          <div className="flex items-start gap-2 pt-1">
            <input
              type="checkbox"
              id="createRule"
              checked={createRule}
              onChange={(e) => setCreateRule(e.target.checked)}
              className="mt-0.5 rounded border-hairline text-[#4F46E5] focus:ring-[#4F46E5]"
            />
            <label htmlFor="createRule" className="text-xs text-content-muted leading-tight">
              Remember rule for{' '}
              <span className="font-medium text-content-primary">"{merchantDisplayName}"</span> (apply to future statements)
            </label>
          </div>

          <div className="flex justify-end gap-2.5 pt-3 border-t border-hairline">
            <button
              type="button"
              onClick={onClose}
              className="px-3.5 py-1.5 text-xs font-medium text-content-muted hover:text-content-primary rounded-lg border border-hairline hover:bg-canvas transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading || selectedCategory === transaction.category}
              className="px-4 py-1.5 text-xs font-medium bg-[#4F46E5] text-white rounded-lg hover:bg-[#4338CA] disabled:opacity-40 transition-colors"
            >
              {isLoading ? 'Saving...' : 'Save Category'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
