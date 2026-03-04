import apiClient from './client'
import type {
  EmsFormat,
  ImportAnomalyListResponse,
  ImportJob,
  ImportJobListResponse,
  ImportResult,
  ImportType,
  StationOutputRecordListResponse,
  StorageOperationRecordListResponse,
} from '@/types/dataImport'

export const dataImportApi = {
  async uploadImportData(
    file: File,
    stationId: string,
    importType: ImportType = 'trading_data',
    emsFormat?: EmsFormat,
  ): Promise<ImportJob> {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('station_id', stationId)
    formData.append('import_type', importType)
    if (emsFormat) {
      formData.append('ems_format', emsFormat)
    }
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
    import_type?: ImportType
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

  async getOutputRecords(
    jobId: string,
    params: { page?: number; page_size?: number },
  ): Promise<StationOutputRecordListResponse> {
    const response = await apiClient.get<StationOutputRecordListResponse>(
      `/data-imports/${jobId}/output-records`,
      { params },
    )
    return response.data
  },

  async getStorageRecords(
    jobId: string,
    params: { page?: number; page_size?: number },
  ): Promise<StorageOperationRecordListResponse> {
    const response = await apiClient.get<StorageOperationRecordListResponse>(
      `/data-imports/${jobId}/storage-records`,
      { params },
    )
    return response.data
  },
}
