import { ref } from 'vue'
import { defineStore } from 'pinia'
import { stationApi } from '@/api/station'
import type {
  StationCreate,
  StationRead,
  StationType,
  StationUpdate,
  StorageDeviceRead,
  UserDeviceBindingsRead,
  UserStationBindingsRead,
} from '@/types/station'

export const useStationStore = defineStore('station', () => {
  const stationList = ref<StationRead[]>([])
  const total = ref(0)
  const page = ref(1)
  const pageSize = ref(20)
  const isLoading = ref(false)
  const searchQuery = ref('')
  const provinceFilter = ref('')
  const typeFilter = ref('')
  const error = ref<string | null>(null)

  async function fetchStations(
    p?: number,
    ps?: number,
    search?: string,
    province?: string,
    stationType?: StationType,
  ): Promise<void> {
    isLoading.value = true
    error.value = null
    try {
      if (p !== undefined) page.value = p
      if (ps !== undefined) pageSize.value = ps
      if (search !== undefined) searchQuery.value = search
      if (province !== undefined) provinceFilter.value = province
      if (stationType !== undefined) typeFilter.value = stationType

      const data = await stationApi.listStations(
        page.value,
        pageSize.value,
        searchQuery.value || undefined,
        provinceFilter.value || undefined,
        typeFilter.value || undefined,
      )
      stationList.value = data.items
      total.value = data.total
      page.value = data.page
      pageSize.value = data.page_size
    } catch (e) {
      error.value = e instanceof Error ? e.message : '加载电站列表失败'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  async function createStation(data: StationCreate): Promise<StationRead> {
    const result = await stationApi.createStation(data)
    // 操作已成功，刷新列表失败不应影响结果（静默吞掉刷新异常）
    await fetchStations().catch(() => {})
    return result
  }

  async function updateStation(stationId: string, data: StationUpdate): Promise<StationRead> {
    const result = await stationApi.updateStation(stationId, data)
    await fetchStations().catch(() => {})
    return result
  }

  async function deleteStation(stationId: string): Promise<void> {
    await stationApi.deleteStation(stationId)
    await fetchStations().catch(() => {})
  }

  // ── 绑定管理 ──

  async function fetchUserStationBindings(userId: string): Promise<UserStationBindingsRead> {
    return await stationApi.getUserStationBindings(userId)
  }

  async function updateUserStationBindings(
    userId: string,
    stationIds: string[],
  ): Promise<UserStationBindingsRead> {
    return await stationApi.updateUserStationBindings(userId, stationIds)
  }

  async function fetchUserDeviceBindings(userId: string): Promise<UserDeviceBindingsRead> {
    return await stationApi.getUserDeviceBindings(userId)
  }

  async function updateUserDeviceBindings(
    userId: string,
    deviceIds: string[],
  ): Promise<UserDeviceBindingsRead> {
    return await stationApi.updateUserDeviceBindings(userId, deviceIds)
  }

  async function fetchAllActiveStations(): Promise<StationRead[]> {
    return await stationApi.listAllActiveStations()
  }

  async function fetchAllActiveDevices(): Promise<StorageDeviceRead[]> {
    return await stationApi.listAllActiveDevices()
  }

  return {
    stationList,
    total,
    page,
    pageSize,
    isLoading,
    searchQuery,
    provinceFilter,
    typeFilter,
    error,
    fetchStations,
    createStation,
    updateStation,
    deleteStation,
    fetchUserStationBindings,
    updateUserStationBindings,
    fetchUserDeviceBindings,
    updateUserDeviceBindings,
    fetchAllActiveStations,
    fetchAllActiveDevices,
  }
})
