import { apiFetch } from './client'
import type { Transaction, TransactionListResponse } from '../types'

export interface TransactionQueryParams {
  user_id?: number
  account_id?: number
  category?: string
  direction?: 'income' | 'expense'
  start_date?: string
  end_date?: string
  search?: string
  is_recurring?: boolean
  is_transfer?: boolean
  is_anomaly?: boolean
  page?: number
  page_size?: number
  sort_by?: 'date' | 'amount_minor'
  sort_order?: 'asc' | 'desc'
}

export async function getTransactions(
  params: TransactionQueryParams = {}
): Promise<TransactionListResponse> {
  const query = new URLSearchParams()
  query.set('user_id', String(params.user_id ?? 1))

  if (params.account_id !== undefined) query.set('account_id', String(params.account_id))
  if (params.category) query.set('category', params.category)
  if (params.direction) query.set('direction', params.direction)
  if (params.start_date) query.set('start_date', params.start_date)
  if (params.end_date) query.set('end_date', params.end_date)
  if (params.search) query.set('search', params.search)
  if (params.is_recurring !== undefined) query.set('is_recurring', String(params.is_recurring))
  if (params.is_transfer !== undefined) query.set('is_transfer', String(params.is_transfer))
  if (params.is_anomaly !== undefined) query.set('is_anomaly', String(params.is_anomaly))
  if (params.page !== undefined) query.set('page', String(params.page))
  if (params.page_size !== undefined) query.set('page_size', String(params.page_size))
  if (params.sort_by) query.set('sort_by', params.sort_by)
  if (params.sort_order) query.set('sort_order', params.sort_order)

  return apiFetch<TransactionListResponse>(`/api/transactions?${query.toString()}`)
}

export async function getTransaction(id: number, userId: number = 1): Promise<Transaction> {
  return apiFetch<Transaction>(`/api/transactions/${id}?user_id=${userId}`)
}

export async function updateTransactionCategory(
  txId: number,
  category: string,
  createRule: boolean = true,
  userId: number = 1
): Promise<Transaction> {
  return apiFetch<Transaction>(`/api/transactions/${txId}?user_id=${userId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ category, create_rule: createRule }),
  })
}

export async function updateTransactionNotes(
  txId: number,
  notes: string,
  userId: number = 1
): Promise<Transaction> {
  return apiFetch<Transaction>(`/api/transactions/${txId}?user_id=${userId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ notes }),
  })
}

export async function getCategories(): Promise<string[]> {
  return apiFetch<string[]>('/api/categories')
}

export async function triggerBatchCategorization(userId: number = 1): Promise<{ categorized_count: number; message: string }> {
  return apiFetch<{ categorized_count: number; message: string }>(
    `/api/transactions/categorize-pending?user_id=${userId}`,
    { method: 'POST' }
  )
}

