import axios from 'axios'

export function getErrorMessage(err: unknown, fallback: string): string {
  if (axios.isAxiosError(err)) {
    return err.response?.data?.message || fallback
  }
  return err instanceof Error ? err.message : fallback
}

export function getErrorCode(err: unknown): string | null {
  if (axios.isAxiosError(err)) {
    return err.response?.data?.code || null
  }
  return null
}
