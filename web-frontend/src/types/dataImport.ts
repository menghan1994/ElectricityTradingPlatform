export type ImportJobStatus = 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled'
export type AnomalyType = 'missing' | 'format_error' | 'out_of_range' | 'duplicate'
export type AnomalyStatus = 'pending' | 'confirmed_normal' | 'corrected' | 'deleted'

export interface ImportJob {
  id: string
  file_name: string
  original_file_name: string
  file_size: number
  station_id: string
  status: ImportJobStatus
  total_records: number
  processed_records: number
  success_records: number
  failed_records: number
  data_completeness: number
  last_processed_row: number
  celery_task_id: string | null
  error_message: string | null
  started_at: string | null
  completed_at: string | null
  imported_by: string
  created_at: string
  updated_at: string
}

export interface ImportJobListResponse {
  items: ImportJob[]
  total: number
  page: number
  page_size: number
}

export interface ImportAnomaly {
  id: string
  import_job_id: string
  row_number: number
  anomaly_type: AnomalyType
  field_name: string
  raw_value: string | null
  description: string
  status: AnomalyStatus
  created_at: string
  updated_at: string
}

export interface AnomalySummary {
  anomaly_type: string
  count: number
}

export interface ImportResult {
  total_records: number
  success_records: number
  failed_records: number
  data_completeness: number
  anomaly_summary: AnomalySummary[]
}

export interface ImportAnomalyListResponse {
  items: ImportAnomaly[]
  total: number
  page: number
  page_size: number
}
