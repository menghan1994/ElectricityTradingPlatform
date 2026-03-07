export type ModelType = 'wind' | 'solar' | 'hybrid'
export type ModelStatus = 'running' | 'error' | 'disabled'
export type ApiAuthType = 'api_key' | 'bearer' | 'none'
export type FetchStatus = 'success' | 'failed' | 'partial'

export const MODEL_TYPE_LABELS: Record<ModelType, string> = {
  wind: '风电',
  solar: '光伏',
  hybrid: '混合',
}

export const MODEL_STATUS_LABELS: Record<ModelStatus, string> = {
  running: '运行中',
  error: '异常',
  disabled: '已停用',
}

export const MODEL_STATUS_COLORS: Record<ModelStatus, string> = {
  running: 'green',
  error: 'red',
  disabled: 'default',
}

export const AUTH_TYPE_LABELS: Record<ApiAuthType, string> = {
  api_key: 'API Key',
  bearer: 'Bearer Token',
  none: '无认证',
}

export const FETCH_STATUS_COLORS: Record<FetchStatus, string> = {
  success: 'green',
  failed: 'red',
  partial: 'orange',
}

export const FETCH_STATUS_LABELS: Record<FetchStatus, string> = {
  success: '成功',
  failed: '失败',
  partial: '部分成功',
}

// --- 预测模型配置 ---

export interface PredictionModel {
  id: string
  station_id: string
  model_name: string
  model_type: ModelType
  api_endpoint: string
  api_key_display: string | null
  api_auth_type: ApiAuthType
  call_frequency_cron: string
  timeout_seconds: number
  is_active: boolean
  status: ModelStatus
  last_check_at: string | null
  last_check_status: string | null
  last_check_error: string | null
  last_fetch_at: string | null
  last_fetch_status: FetchStatus | null
  last_fetch_error: string | null
  created_at: string
  updated_at: string
}

export interface PredictionModelCreate {
  model_name: string
  model_type: ModelType
  api_endpoint: string
  api_key?: string | null
  api_auth_type?: ApiAuthType
  call_frequency_cron?: string
  timeout_seconds?: number
  station_id: string
}

export interface PredictionModelUpdate {
  model_name?: string
  model_type?: ModelType
  api_endpoint?: string
  api_key?: string | null
  api_auth_type?: ApiAuthType
  call_frequency_cron?: string
  timeout_seconds?: number
  is_active?: boolean
}

export interface PredictionModelListResponse {
  items: PredictionModel[]
  total: number
  page: number
  page_size: number
}

// --- 模型运行状态 ---

export interface PredictionModelStatus {
  model_id: string
  model_name: string
  station_name: string | null
  status: ModelStatus
  last_check_at: string | null
  last_check_error: string | null
  last_fetch_at: string | null
  last_fetch_status: FetchStatus | null
  last_fetch_error: string | null
}

export interface PredictionModelStatusListResponse {
  items: PredictionModelStatus[]
}

// --- 连接测试结果 ---

export interface ConnectionTestResult {
  success: boolean
  latency_ms: number | null
  error_message: string | null
  tested_at: string
}

// --- 功率预测数据 ---

export interface PowerPrediction {
  prediction_date: string
  period: number
  predicted_power_kw: number
  confidence_upper_kw: number
  confidence_lower_kw: number
  source: string
  fetched_at: string
}

export interface PowerPredictionListResponse {
  items: PowerPrediction[]
  total: number
}

// --- 拉取结果 ---

export interface FetchResult {
  model_id: string
  model_name: string
  station_name: string | null
  success: boolean
  records_count: number
  error_message: string | null
  fetched_at: string
}
