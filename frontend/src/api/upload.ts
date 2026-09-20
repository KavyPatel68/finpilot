import { apiFetch } from './client'
import type { Document, UploadResponse, ColumnMapping } from '../types'

const BASE_URL = import.meta.env.VITE_API_URL ?? (import.meta.env.PROD ? '' : 'http://localhost:8000')

export async function uploadDocument(
  file: File,
  accountId: number = 1,
  userId: number = 1,
  pdfPassword?: string
): Promise<UploadResponse> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('account_id', String(accountId))
  formData.append('user_id', String(userId))
  if (pdfPassword) {
    formData.append('pdf_password', pdfPassword)
  }

  const res = await fetch(`${BASE_URL}/api/upload`, {
    method: 'POST',
    body: formData,
  })

  if (!res.ok) {
    const errText = await res.text()
    throw new Error(`Upload failed (${res.status}): ${errText || res.statusText}`)
  }
  return res.json()
}

export async function loadSampleStatement(
  accountId: number = 1,
  userId: number = 1
): Promise<UploadResponse> {
  return apiFetch<UploadResponse>(`/api/upload/sample-statement?account_id=${accountId}&user_id=${userId}`, {
    method: 'POST',
  })
}

export async function confirmMapping(
  docId: number,
  mapping: ColumnMapping
): Promise<UploadResponse> {
  return apiFetch<UploadResponse>(`/api/documents/${docId}/confirm-mapping`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(mapping),
  })
}

export async function getDocuments(userId: number = 1): Promise<Document[]> {
  return apiFetch<Document[]>(`/api/documents?user_id=${userId}`)
}

export async function getDocument(docId: number): Promise<Document> {
  return apiFetch<Document>(`/api/documents/${docId}`)
}

export async function deleteDocument(docId: number): Promise<{ status: string }> {
  return apiFetch<{ status: string }>(`/api/documents/${docId}`, {
    method: 'DELETE',
  })
}

export async function seedDemoData(
  userId: number = 1
): Promise<{ status: string; imported_count: number; months_covered: number; message: string }> {
  return apiFetch<{ status: string; imported_count: number; months_covered: number; message: string }>(
    `/api/upload/seed-demo?user_id=${userId}`,
    {
      method: 'POST',
    }
  )
}
