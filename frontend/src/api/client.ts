const BASE_URL = import.meta.env.VITE_API_URL ?? (import.meta.env.PROD ? '' : 'http://localhost:8000')

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
    this.name = 'ApiError'
  }
}

export async function apiFetch<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  })
  if (!res.ok) {
    const body = await res.text()
    throw new ApiError(res.status, body)
  }
  return res.json() as Promise<T>
}

export async function resetDemoData(userId: number = 1): Promise<{ status: string; message: string; transaction_count: number }> {
  return apiFetch<{ status: string; message: string; transaction_count: number }>(`/api/demo/reset?user_id=${userId}`, {
    method: 'POST',
  })
}

export async function getDemoStatus(): Promise<{ demo_mode: boolean; transaction_count: number; seeded: boolean }> {
  return apiFetch<{ demo_mode: boolean; transaction_count: number; seeded: boolean }>('/api/demo/status')
}
