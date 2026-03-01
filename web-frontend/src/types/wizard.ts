import type { BatteryType, StationRead, StationType, StorageDeviceRead } from './station'

export interface WizardStorageDeviceInput {
  name: string
  capacity_mwh: number
  max_charge_rate_mw: number
  max_discharge_rate_mw: number
  soc_upper_limit: number
  soc_lower_limit: number
  battery_type: BatteryType | null
}

export interface StationWizardCreate {
  name: string
  province: string
  capacity_mw: number
  station_type: StationType
  grid_connection_point: string | null
  has_storage: boolean
  storage_devices: WizardStorageDeviceInput[]
}

export interface StationWizardResponse {
  station: StationRead
  devices: StorageDeviceRead[]
}
