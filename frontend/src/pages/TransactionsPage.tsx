import React, { useState, useEffect, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  SparklesIcon,
  ArrowDownTrayIcon,
  MagnifyingGlassIcon,
  FunnelIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline'
import {
  getTransactions,
  getCategories,
  updateTransactionCategory,
  triggerBatchCategorization,
} from '../api/transactions'
import type { Transaction } from '../types'
import { TransactionTable } from '../components/Transactions/TransactionTable'
import { CategoryEditModal } from '../components/Transactions/CategoryEditModal'
import { TransactionDetailDrawer } from '../components/Transactions/TransactionDetailDrawer'
import { LoadingSpinner } from '../components/common/LoadingSpinner'
import { useDebounce } from '../hooks/useDebounce'

export function TransactionsPage() {
  const [searchParams, setSearchParams] = useSearchParams()

  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [categories, setCategories] = useState<string[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(25)
  const [totalPages, setTotalPages] = useState(1)
  const [isLoading, setIsLoading] = useState(false)
  const [isCategorizing, setIsCategorizing] = useState(false)
  const [notification, setNotification] = useState<string | null>(null)

  // Sorting
  const [sortBy, setSortBy] = useState<'date' | 'amount_minor'>('date')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')

  // Filter States
  const [searchTerm, setSearchTerm] = useState(searchParams.get('q') || '')
  const debouncedSearch = useDebounce(searchTerm, 300)
  const [selectedCategory, setSelectedCategory] = useState<string>(
    searchParams.get('category') || ''
  )
  const [selectedDirection, setSelectedDirection] = useState<'income' | 'expense' | ''>('')
  const [isRecurringOnly, setIsRecurringOnly] = useState(false)
  const [isAnomalyOnly, setIsAnomalyOnly] = useState(false)
  const [startDate, setStartDate] = useState<string>('')
  const [endDate, setEndDate] = useState<string>('')

  // Drawer & Modal States
  const [selectedTransaction, setSelectedTransaction] = useState<Transaction | null>(null)
  const [editingTransaction, setEditingTransaction] = useState<Transaction | null>(null)
  const [isSavingCategory, setIsSavingCategory] = useState(false)

  // Load Categories on mount
  useEffect(() => {
    getCategories()
      .then(setCategories)
      .catch((err) => console.error('Failed to load categories:', err))
  }, [])

  // Sync URL search params if category or search term changed externally
  useEffect(() => {
    const q = searchParams.get('q')
    const cat = searchParams.get('category')
    if (q !== null && q !== searchTerm) setSearchTerm(q)
    if (cat !== null && cat !== selectedCategory) setSelectedCategory(cat)
  }, [searchParams])

  // Fetch Transactions
  const fetchTransactions = useCallback(async () => {
    setIsLoading(true)
    try {
      const data = await getTransactions({
        user_id: 1,
        search: debouncedSearch.trim() || undefined,
        category: selectedCategory || undefined,
        direction: selectedDirection || undefined,
        is_recurring: isRecurringOnly ? true : undefined,
        is_anomaly: isAnomalyOnly ? true : undefined,
        start_date: startDate || undefined,
        end_date: endDate || undefined,
        page,
        page_size: pageSize,
        sort_by: sortBy,
        sort_order: sortOrder,
      })
      setTransactions(data.items)
      setTotal(data.total)
      setTotalPages(data.total_pages)
    } catch (err) {
      console.error('Failed to fetch transactions:', err)
    } finally {
      setIsLoading(false)
    }
  }, [
    debouncedSearch,
    selectedCategory,
    selectedDirection,
    isRecurringOnly,
    isAnomalyOnly,
    startDate,
    endDate,
    page,
    pageSize,
    sortBy,
    sortOrder,
  ])

  useEffect(() => {
    fetchTransactions()
  }, [fetchTransactions])

  // Reset page when filters change
  useEffect(() => {
    setPage(1)
  }, [
    debouncedSearch,
    selectedCategory,
    selectedDirection,
    isRecurringOnly,
    isAnomalyOnly,
    startDate,
    endDate,
  ])

  const handleSort = (col: 'date' | 'amount_minor') => {
    if (sortBy === col) {
      setSortOrder((prev) => (prev === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortBy(col)
      setSortOrder('desc')
    }
  }

  const handleSaveCategory = async (txId: number, newCategory: string, createRule: boolean) => {
    setIsSavingCategory(true)
    try {
      const updated = await updateTransactionCategory(txId, newCategory, createRule, 1)
      setTransactions((prev) => prev.map((t) => (t.id === txId ? updated : t)))
      if (selectedTransaction?.id === txId) {
        setSelectedTransaction(updated)
      }
      setEditingTransaction(null)
      setNotification(`Category set to "${newCategory}"${createRule ? ' & rule created!' : '.'}`)
      setTimeout(() => setNotification(null), 4000)
    } catch (err) {
      alert('Failed to update category')
    } finally {
      setIsSavingCategory(false)
    }
  }

  const handleBatchCategorize = async () => {
    setIsCategorizing(true)
    try {
      const res = await triggerBatchCategorization(1)
      setNotification(res.message)
      await fetchTransactions()
      setTimeout(() => setNotification(null), 5000)
    } catch (err) {
      alert('Failed to run batch categorization')
    } finally {
      setIsCategorizing(false)
    }
  }

  const handleExportCSV = () => {
    if (transactions.length === 0) return
    const headers = ['ID', 'Date', 'Payee / Merchant', 'Raw Narration', 'Category', 'Direction', 'Amount (INR)', 'Payment Method', 'Notes']
    const rows = transactions.map((t) => [
      t.id,
      t.date,
      `"${(t.merchant_normalized || '').replace(/"/g, '""')}"`,
      `"${(t.raw_description || '').replace(/"/g, '""')}"`,
      `"${t.category || ''}"`,
      t.direction,
      (t.amount_minor / 100).toFixed(2),
      `"${t.payment_method || ''}"`,
      `"${(t.notes || '').replace(/"/g, '""')}"`,
    ])

    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map((r) => r.join(','))].join('\n')
    const encodedUri = encodeURI(csvContent)
    const link = document.createElement('a')
    link.setAttribute('href', encodedUri)
    link.setAttribute('download', `finpilot_transactions_${new Date().toISOString().slice(0, 10)}.csv`)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  const clearAllFilters = () => {
    setSearchTerm('')
    setSelectedCategory('')
    setSelectedDirection('')
    setIsRecurringOnly(false)
    setIsAnomalyOnly(false)
    setStartDate('')
    setEndDate('')
    setSearchParams({})
  }

  const hasActiveFilters = Boolean(
    searchTerm ||
    selectedCategory ||
    selectedDirection ||
    isRecurringOnly ||
    isAnomalyOnly ||
    startDate ||
    endDate
  )

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Header & Quick Action Hub */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-2 border-b border-hairline">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-content-primary">
            Transactions Ledger
          </h1>
          <p className="text-xs text-content-muted mt-1">
            Search, sort, filter, and inspect detailed transactions. Train custom categorization rules.
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          {/* CSV Export (Secondary Outlined) */}
          <button
            onClick={handleExportCSV}
            disabled={transactions.length === 0}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-hairline transition-colors
              bg-surface hover:bg-canvas text-content-primary disabled:opacity-40"
            title="Download visible transactions as CSV"
          >
            <ArrowDownTrayIcon className="w-3.5 h-3.5" />
            <span>Export CSV</span>
          </button>

          {/* AI Batch Categorization (Primary Accent) */}
          <button
            onClick={handleBatchCategorize}
            disabled={isCategorizing}
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 bg-[#4F46E5] hover:bg-[#4338CA] text-white text-xs font-medium rounded-lg shadow-2xs transition-colors disabled:opacity-40"
          >
            <SparklesIcon className={`w-3.5 h-3.5 ${isCategorizing ? 'animate-spin' : ''}`} />
            <span>{isCategorizing ? 'Categorizing...' : 'AI Auto-Categorize'}</span>
          </button>
        </div>
      </div>

      {/* Notification Toast */}
      {notification && (
        <div className="p-3 rounded-lg bg-emerald-500/8 border border-emerald-500/20 text-emerald-800 dark:text-emerald-300 text-xs flex items-center justify-between transition-colors">
          <span className="font-medium">{notification}</span>
          <button onClick={() => setNotification(null)} className="font-semibold ml-2">
            ✕
          </button>
        </div>
      )}

      {/* Filter Toolbar & Quick Chips */}
      <div className="rounded-xl border border-hairline p-4 bg-surface space-y-3">
        {/* Search Bar & Dropdowns */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-12 gap-3">
          {/* Search Box */}
          <div className="lg:col-span-5 relative">
            <MagnifyingGlassIcon className="w-4 h-4 text-content-muted absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search narration, merchant, or notes..."
              className="w-full text-xs rounded-lg border border-hairline pl-9 pr-8 py-2 bg-canvas text-content-primary placeholder:text-content-muted focus:outline-none focus:ring-1 focus:ring-[#4F46E5]"
            />
            {searchTerm && (
              <button
                onClick={() => setSearchTerm('')}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-content-muted hover:text-content-primary"
              >
                <XMarkIcon className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          {/* Category Dropdown */}
          <div className="lg:col-span-3">
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="w-full text-xs font-medium rounded-lg border border-hairline px-3 py-2 bg-canvas text-content-primary focus:outline-none focus:ring-1 focus:ring-[#4F46E5]"
            >
              <option value="">All Categories ({categories.length})</option>
              {categories.map((cat) => (
                <option key={cat} value={cat}>
                  {cat}
                </option>
              ))}
            </select>
          </div>

          {/* Direction Filter */}
          <div className="lg:col-span-2">
            <select
              value={selectedDirection}
              onChange={(e) => setSelectedDirection(e.target.value as 'income' | 'expense' | '')}
              className="w-full text-xs font-medium rounded-lg border border-hairline px-3 py-2 bg-canvas text-content-primary focus:outline-none focus:ring-1 focus:ring-[#4F46E5]"
            >
              <option value="">All Directions</option>
              <option value="expense">Expenses Only</option>
              <option value="income">Income Only</option>
            </select>
          </div>

          {/* Page Size */}
          <div className="lg:col-span-2">
            <select
              value={pageSize}
              onChange={(e) => setPageSize(Number(e.target.value))}
              className="w-full text-xs font-medium rounded-lg border border-hairline px-3 py-2 bg-canvas text-content-primary focus:outline-none focus:ring-1 focus:ring-[#4F46E5]"
            >
              <option value={25}>25 / page</option>
              <option value={50}>50 / page</option>
              <option value={100}>100 / page</option>
            </select>
          </div>
        </div>

        {/* Filter Chips Bar */}
        <div className="flex items-center justify-between gap-2 pt-2 border-t border-hairline flex-wrap">
          <div className="flex items-center gap-1.5 flex-wrap">
            <span className="text-[11px] font-medium text-content-muted mr-1 flex items-center gap-1">
              <FunnelIcon className="w-3.5 h-3.5" /> Filter:
            </span>

            {/* Recurring Chip */}
            <button
              onClick={() => setIsRecurringOnly(!isRecurringOnly)}
              className={`px-2.5 py-1 rounded-md text-xs font-medium transition-colors ${
                isRecurringOnly
                  ? 'bg-[#4F46E5]/10 text-[#4F46E5] dark:text-[#818CF8] border border-[#4F46E5]/30'
                  : 'bg-canvas border border-hairline text-content-muted hover:text-content-primary'
              }`}
            >
              🔄 Subscriptions Only
            </button>

            {/* Anomaly Chip */}
            <button
              onClick={() => setIsAnomalyOnly(!isAnomalyOnly)}
              className={`px-2.5 py-1 rounded-md text-xs font-medium transition-colors ${
                isAnomalyOnly
                  ? 'bg-rose-500/10 text-rose-700 dark:text-rose-400 border border-rose-500/30'
                  : 'bg-canvas border border-hairline text-content-muted hover:text-content-primary'
              }`}
            >
              ⚠️ Flagged Anomalies
            </button>

            {/* Date Range Inputs */}
            <div className="flex items-center gap-1.5 ml-2 text-xs text-content-muted">
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="rounded-md border border-hairline px-2 py-1 text-[11px] bg-canvas text-content-primary focus:outline-none focus:ring-1 focus:ring-[#4F46E5]"
              />
              <span>to</span>
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="rounded-md border border-hairline px-2 py-1 text-[11px] bg-canvas text-content-primary focus:outline-none focus:ring-1 focus:ring-[#4F46E5]"
              />
            </div>
          </div>

          {hasActiveFilters && (
            <button
              onClick={clearAllFilters}
              className="text-xs font-medium text-[#4F46E5] dark:text-[#818CF8] hover:underline"
            >
              Reset Filters
            </button>
          )}
        </div>
      </div>

      {/* Results Counter with Inter tabular nums */}
      <div className="flex items-center justify-between text-xs text-content-muted px-1">
        <span className="tabular-nums">
          Showing {transactions.length > 0 ? (page - 1) * pageSize + 1 : 0} –{' '}
          {Math.min(page * pageSize, total)} of{' '}
          <strong className="text-content-primary font-medium">{total}</strong> transactions
        </span>
        <span className="tabular-nums">
          Page {page} of {totalPages}
        </span>
      </div>

      {/* Main Transactions Table */}
      {isLoading ? (
        <div className="py-20 flex justify-center bg-surface rounded-xl border border-hairline">
          <LoadingSpinner />
        </div>
      ) : (
        <TransactionTable
          transactions={transactions}
          sortBy={sortBy}
          sortOrder={sortOrder}
          onSort={handleSort}
          onSelectTransaction={(tx) => setSelectedTransaction(tx)}
          onEditCategory={(tx) => setEditingTransaction(tx)}
        />
      )}

      {/* Pagination Controls */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between pt-2">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1 || isLoading}
            className="px-3.5 py-1.5 text-xs font-medium bg-surface border border-hairline rounded-lg hover:bg-canvas text-content-primary disabled:opacity-40 transition-colors"
          >
            ← Previous
          </button>

          <div className="flex items-center gap-1 text-xs">
            {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
              let pageNum = i + 1
              if (totalPages > 5 && page > 3) {
                pageNum = Math.min(page - 2 + i, totalPages)
              }
              return (
                <button
                  key={pageNum}
                  onClick={() => setPage(pageNum)}
                  className={`w-7 h-7 rounded-md text-xs font-medium tabular-nums flex items-center justify-center transition-colors ${
                    page === pageNum
                      ? 'bg-[#4F46E5] text-white'
                      : 'bg-surface text-content-primary hover:bg-canvas border border-hairline'
                  }`}
                >
                  {pageNum}
                </button>
              )
            })}
          </div>

          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page >= totalPages || isLoading}
            className="px-3.5 py-1.5 text-xs font-medium bg-surface border border-hairline rounded-lg hover:bg-canvas text-content-primary disabled:opacity-40 transition-colors"
          >
            Next →
          </button>
        </div>
      )}

      {/* Side Detail Drawer on Row Click */}
      {selectedTransaction && (
        <TransactionDetailDrawer
          transaction={selectedTransaction}
          categories={categories}
          onClose={() => setSelectedTransaction(null)}
          onUpdate={(updated) => {
            setTransactions((prev) => prev.map((t) => (t.id === updated.id ? updated : t)))
            setSelectedTransaction(updated)
          }}
        />
      )}

      {/* Inline Quick Category Edit Modal */}
      {editingTransaction && (
        <CategoryEditModal
          transaction={editingTransaction}
          categories={categories}
          onSave={handleSaveCategory}
          onClose={() => setEditingTransaction(null)}
          isLoading={isSavingCategory}
        />
      )}
    </div>
  )
}
