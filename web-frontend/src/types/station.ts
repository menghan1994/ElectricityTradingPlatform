export type StationType = 'wind' | 'solar' | 'hybrid'

/**
 * 后端 Pydantic Decimal 字段序列化为 JSON string（如 "100.00"），
 * 因此 capacity_mw 等 Decimal 字段在 Read 类型中为 string。
 * 编辑时需用 Number() 转换（见 StationManagementView.openEditDialog）。
 */
export interface StationRead {
  id: string
  name: string
  province: string
  capacity_mw: string // Decimal → JSON string
  station_type: StationType
  has_storage: boolean
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface StationCreate {
  name: string
  province: string
  capacity_mw: number
  station_type: StationType
  has_storage: boolean
}

export interface StationUpdate {
  name?: string
  province?: string
  capacity_mw?: number
  station_type?: StationType
  has_storage?: boolean
  is_active?: boolean
}

export interface StationListResponse {
  items: StationRead[]
  total: number
  page: number
  page_size: number
}

export interface StorageDeviceRead {
  id: string
  station_id: string
  station_name: string | null
  name: string
  capacity_mwh: string
  max_charge_rate_mw: string
  max_discharge_rate_mw: string
  soc_upper_limit: string
  soc_lower_limit: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface UserStationBindingsRead {
  station_ids: string[]
  stations: StationRead[]
}

export interface UserDeviceBindingsRead {
  device_ids: string[]
  devices: StorageDeviceRead[]
}

export const stationTypeLabels: Record<StationType, string> = {
  wind: '风电',
  solar: '光伏',
  hybrid: '风光互补',
}
