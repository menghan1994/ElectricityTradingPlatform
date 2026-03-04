import apiClient from './client'
import type {
  AnomalyBulkActionRequest,
  AnomalyBulkActionResponse,
  AnomalyCorrectRequest,
  AnomalyDetail,
  AnomalyStatsSummaryItem,
  ImportAnomaly,
  ImportAnomalyListResponse,
} from '@/types/dataImport'

export const anomalyApi = {
  async listAnomalies(params: {
    page?: number
    page_size?: number
    anomaly_type?: string
    status?: string
    import_job_id?: string
  }): Promise<ImportAnomalyListResponse> {
    const response = await apiClient.get<ImportAnomalyListResponse>('/anomalies', { params })
    return response.data
  },

  async getAnomaly(anomalyId: string): Promise<AnomalyDetail> {
    const response = await apiClient.get<AnomalyDetail>(`/anomalies/${anomalyId}`)
    return response.data
  },

  async correctAnomaly(anomalyId: string, data: AnomalyCorrectRequest): Promise<ImportAnomaly> {
    const response = await apiClient.patch<ImportAnomaly>(
      `/anomalies/${anomalyId}/correct`,
      data,
    )
    return response.data
  },

  async confirmAnomalyNormal(anomalyId: string): Promise<ImportAnomaly> {
    const response = await apiClient.patch<ImportAnomaly>(
      `/anomalies/${anomalyId}/confirm-normal`,
    )
    return response.data
  },

  async bulkAction(data: AnomalyBulkActionRequest): Promise<AnomalyBulkActionResponse> {
    const response = await apiClient.post<AnomalyBulkActionResponse>(
      '/anomalies/bulk-action',
      data,
    )
    return response.data
  },

  async getSummary(params?: {
    import_job_id?: string
    status?: string
  }): Promise<AnomalyStatsSummaryItem[]> {
    const response = await apiClient.get<AnomalyStatsSummaryItem[]>('/anomalies/summary', { params })
    return response.data
  },
}
