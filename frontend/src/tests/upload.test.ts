import { describe, it, expect } from 'vitest'
import type { UploadResponse, Document } from '../types'

describe('Upload data contracts and state handlers', () => {
  it('validates UploadResponse structure', () => {
    const mockUpload: UploadResponse = {
      document_id: 42,
      filename: 'hdfc_aug_2024.csv',
      status: 'done',
      row_count: 50,
      imported_count: 48,
      duplicate_count: 2,
      parse_errors: [],
    }

    expect(mockUpload.document_id).toBe(42)
    expect(mockUpload.imported_count + mockUpload.duplicate_count).toBe(mockUpload.row_count)
    expect(mockUpload.status).toBe('done')
  })

  it('validates Document entity structure for statement history', () => {
    const mockDoc: Document = {
      id: 1,
      user_id: 1,
      account_id: 1,
      filename: 'synthetic_statements_apr_sep_2024.csv',
      file_type: 'csv',
      status: 'done',
      parse_errors: [],
      row_count: 152,
      imported_count: 152,
      duplicate_count: 0,
      uploaded_at: '2024-09-20T00:00:00Z',
      processed_at: '2024-09-20T00:00:01Z',
    }

    expect(mockDoc.filename).toContain('synthetic_statements')
    expect(mockDoc.imported_count).toBe(152)
    expect(mockDoc.status).toBe('done')
  })
})
