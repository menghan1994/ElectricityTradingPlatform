export type FreshnessStatus = 'fresh' | 'stale' | 'expired' | 'critical'
export type FetchStatus = 'pending' | 'success' | 'failed'
export type PriceSource = 'api' | 'manual_import'
export type ApiAuthType = 'api_key' | 'bearer' | 'none'

export const FRESHNESS_STATUS_LABELS: Record<FreshnessStatus, string> = {
  fresh: '正常',
  stale: '略过期',
  expired: '过期',
  critical: '严重过期',
}

export const PRICE_SOURCE_LABELS: Record<PriceSource, string> = {
  api: 'API获取',
  manual_import: '手动导入',
}

// --- 出清价格 ---

export interface MarketClearingPrice {
  id: string
  trading_date: string
  period: number
  province: string
  clearing_price: number
  source: PriceSource
  fetched_at: string
  import_job_id: string | null
  created_at: string
}

export interface MarketClearingPriceListResponse {
  items: MarketClearingPrice[]
  total: number
  page: number
  page_size: number
}

// --- 数据源配置 ---

export interface MarketDataSource {
  id: string
  province: string
  source_name: string
  api_endpoint: string | null
  api_auth_type: ApiAuthType
  fetch_schedule: string
  is_active: boolean
  last_fetch_at: string | null
  last_fetch_status: FetchStatus
  last_fetch_error: string | null
  cache_ttl_seconds: number
  created_at: string
  updated_at: string
}

export interface MarketDataSourceCreate {
  province: string
  source_name: string
  api_endpoint?: string | null
  api_key?: string | null
  api_auth_type?: ApiAuthType
  fetch_schedule?: string
  is_active?: boolean
  cache_ttl_seconds?: number
}

export interface MarketDataSourceUpdate {
  source_name?: string
  api_endpoint?: string | null
  api_key?: string | null
  api_auth_type?: ApiAuthType
  fetch_schedule?: string
  is_active?: boolean
  cache_ttl_seconds?: number
}

export interface MarketDataSourceListResponse {
  items: MarketDataSource[]
  total: number
  page: number
  page_size: number
}

// --- 数据新鲜度 ---

export interface MarketDataFreshness {
  province: string
  last_updated: string | null
  hours_ago: number | null
  status: FreshnessStatus
}

export interface MarketDataFreshnessListResponse {
  items: MarketDataFreshness[]
}

// --- 获取结果 ---

export interface MarketDataFetchResult {
  province: string
  trading_date: string
  records_count: number
  status: string
  error_message: string | null
}
