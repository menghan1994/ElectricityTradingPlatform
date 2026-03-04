export type ImportJobStatus = 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled'
export type ImportType = 'trading_data' | 'station_output' | 'storage_operation'
export type EmsFormat = 'standard' | 'sungrow' | 'huawei' | 'catl'
export type AnomalyType = 'missing' | 'format_error' | 'out_of_range' | 'duplicate'
export type AnomalyStatus = 'pending' | 'confirmed_normal' | 'corrected' | 'deleted'

export const IMPORT_TYPE_LABELS: Record<ImportType, string> = {
  trading_data: '交易数据',
  station_output: '电站出力数据',
  storage_operation: '储能运行数据',
}

export interface ImportJob {
  id: string
  file_name: string
  original_file_name: string
  file_size: number
  station_id: string
  import_type: ImportType
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

// --- 异常管理 (Story 2.4) ---

export interface AnomalyCorrectRequest {
  corrected_value: string
}

export interface AnomalyBulkActionRequest {
  anomaly_ids: string[]
  action: 'delete' | 'confirm_normal'
}

export interface AnomalyBulkActionResponse {
  affected_count: number
  action: string
}

export interface AnomalyDetail extends ImportAnomaly {
  original_file_name?: string | null
  station_id?: string | null
}

export interface AnomalyStatsSummaryItem {
  anomaly_type: string
  count: number
}

// --- 电站出力与储能运行数据 (Story 2.5) ---

export interface StationOutputRecord {
  id: string
  trading_date: string
  period: number
  station_id: string
  actual_output_kw: number
  import_job_id: string
  created_at: string
}

export interface StationOutputRecordListResponse {
  items: StationOutputRecord[]
  total: number
  page: number
  page_size: number
}

export interface StorageOperationRecord {
  id: string
  trading_date: string
  period: number
  device_id: string
  soc: number
  charge_power_kw: number
  discharge_power_kw: number
  cycle_count: number
  import_job_id: string
  created_at: string
}

export interface StorageOperationRecordListResponse {
  items: StorageOperationRecord[]
  total: number
  page: number
  page_size: number
}
