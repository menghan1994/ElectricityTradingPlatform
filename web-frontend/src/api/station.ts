import apiClient from './client'
import type {
  StationCreate,
  StationListResponse,
  StationRead,
  StationType,
  StationUpdate,
  StorageDeviceRead,
  UserDeviceBindingsRead,
  UserStationBindingsRead,
} from '@/types/station'

export const stationApi = {
  // ── 电站 CRUD ──

  async listStations(
    page: number = 1,
    pageSize: number = 20,
    search?: string,
    province?: string,
    stationType?: StationType,
  ): Promise<StationListResponse> {
    const params: Record<string, string | number> = { page, page_size: pageSize }
    if (search) params.search = search
    if (province) params.province = province
    if (stationType) params.station_type = stationType
    const response = await apiClient.get<StationListResponse>('/stations', { params })
    return response.data
  },

  async getStation(stationId: string): Promise<StationRead> {
    const response = await apiClient.get<StationRead>(`/stations/${stationId}`)
    return response.data
  },

  async createStation(data: StationCreate): Promise<StationRead> {
    const response = await apiClient.post<StationRead>('/stations', data)
    return response.data
  },

  async updateStation(stationId: string, data: StationUpdate): Promise<StationRead> {
    const response = await apiClient.put<StationRead>(`/stations/${stationId}`, data)
    return response.data
  },

  // 保留：当前组件通过 updateStation({ is_active: false }) 停用电站，
  // 但 deleteStation 映射后端 DELETE 端点（软删除），供未来场景或脚本使用。
  async deleteStation(stationId: string): Promise<void> {
    await apiClient.delete(`/stations/${stationId}`)
  },

  // ── 绑定管理 ── (MEDIUM: 路由前缀改为 /bindings)

  async getUserStationBindings(userId: string): Promise<UserStationBindingsRead> {
    const response = await apiClient.get<UserStationBindingsRead>(
      `/bindings/${userId}/station_bindings`,
    )
    return response.data
  },

  async updateUserStationBindings(
    userId: string,
    stationIds: string[],
  ): Promise<UserStationBindingsRead> {
    const response = await apiClient.put<UserStationBindingsRead>(
      `/bindings/${userId}/station_bindings`,
      { station_ids: stationIds },
    )
    return response.data
  },

  async getUserDeviceBindings(userId: string): Promise<UserDeviceBindingsRead> {
    const response = await apiClient.get<UserDeviceBindingsRead>(
      `/bindings/${userId}/device_bindings`,
    )
    return response.data
  },

  async updateUserDeviceBindings(
    userId: string,
    deviceIds: string[],
  ): Promise<UserDeviceBindingsRead> {
    const response = await apiClient.put<UserDeviceBindingsRead>(
      `/bindings/${userId}/device_bindings`,
      { device_ids: deviceIds },
    )
    return response.data
  },

  // ── 活跃资源列表（用于穿梭框） ──

  // HIGH-7: 使用后端 active-only 端点获取全部活跃电站，避免分页截断
  async listAllActiveStations(): Promise<StationRead[]> {
    const response = await apiClient.get<StationRead[]>('/stations/active')
    return response.data
  },

  async listAllActiveDevices(): Promise<StorageDeviceRead[]> {
    const response = await apiClient.get<StorageDeviceRead[]>('/stations/devices/active')
    return response.data
  },

  async getStationDevices(stationId: string): Promise<StorageDeviceRead[]> {
    const response = await apiClient.get<StorageDeviceRead[]>(`/stations/${stationId}/devices`)
    return response.data
  },
}
