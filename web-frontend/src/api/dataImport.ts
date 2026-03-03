import apiClient from './client'
import type {
  ImportAnomalyListResponse,
  ImportJob,
  ImportJobListResponse,
  ImportResult,
} from '@/types/dataImport'

export const dataImportApi = {
  async uploadTradingData(file: File, stationId: string): Promise<ImportJob> {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('station_id', stationId)
    const response = await apiClient.post<ImportJob>('/data-imports/upload', formData, {
      timeout: 120000,
    })
    return response.data
  },

  async listImportJobs(params: {
    station_id?: string
    page?: number
    page_size?: number
    status?: string
  }): Promise<ImportJobListResponse> {
    const response = await apiClient.get<ImportJobListResponse>('/data-imports', { params })
    return response.data
  },

  async getImportJob(jobId: string): Promise<ImportJob> {
    const response = await apiClient.get<ImportJob>(`/data-imports/${jobId}`)
    return response.data
  },

  async getImportResult(jobId: string): Promise<ImportResult> {
    const response = await apiClient.get<ImportResult>(`/data-imports/${jobId}/result`)
    return response.data
  },

  async getImportAnomalies(
    jobId: string,
    params: { page?: number; page_size?: number; anomaly_type?: string },
  ): Promise<ImportAnomalyListResponse> {
    const response = await apiClient.get<ImportAnomalyListResponse>(
      `/data-imports/${jobId}/anomalies`,
      { params },
    )
    return response.data
  },

  async resumeImport(jobId: string): Promise<ImportJob> {
    const response = await apiClient.post<ImportJob>(`/data-imports/${jobId}/resume`)
    return response.data
  },

  async cancelImport(jobId: string): Promise<ImportJob> {
    const response = await apiClient.post<ImportJob>(`/data-imports/${jobId}/cancel`)
    return response.data
  },
}
