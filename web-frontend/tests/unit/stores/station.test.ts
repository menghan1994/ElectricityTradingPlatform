import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useStationStore } from '../../../src/stores/station'

vi.mock('../../../src/api/station', () => ({
  stationApi: {
    listStations: vi.fn(),
    getStation: vi.fn(),
    createStation: vi.fn(),
    updateStation: vi.fn(),
    deleteStation: vi.fn(),
    getUserStationBindings: vi.fn(),
    updateUserStationBindings: vi.fn(),
    getUserDeviceBindings: vi.fn(),
    updateUserDeviceBindings: vi.fn(),
    listAllActiveStations: vi.fn(),
    listAllActiveDevices: vi.fn(),
  },
}))

import { stationApi } from '../../../src/api/station'

const mockStationList = {
  items: [
    { id: '1', name: '广东风电一号', province: '广东', capacity_mw: '100.00', station_type: 'wind', has_storage: true, is_active: true, created_at: '2026-01-01', updated_at: '2026-01-01' },
    { id: '2', name: '山东光伏一号', province: '山东', capacity_mw: '50.00', station_type: 'solar', has_storage: false, is_active: true, created_at: '2026-01-01', updated_at: '2026-01-01' },
  ],
  total: 2,
  page: 1,
  page_size: 20,
}

describe('useStationStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  describe('initial state', () => {
    it('should have empty station list initially', () => {
      const store = useStationStore()
      expect(store.stationList).toEqual([])
      expect(store.total).toBe(0)
      expect(store.page).toBe(1)
      expect(store.pageSize).toBe(20)
      expect(store.isLoading).toBe(false)
    })
  })

  describe('fetchStations', () => {
    it('should fetch and update station list', async () => {
      vi.mocked(stationApi.listStations).mockResolvedValue(mockStationList)

      const store = useStationStore()
      await store.fetchStations()

      expect(store.stationList).toEqual(mockStationList.items)
      expect(store.total).toBe(2)
      expect(store.isLoading).toBe(false)
    })

    it('should pass filter parameters', async () => {
      vi.mocked(stationApi.listStations).mockResolvedValue(mockStationList)

      const store = useStationStore()
      await store.fetchStations(1, 10, '风电', '广东', 'wind')

      expect(stationApi.listStations).toHaveBeenCalledWith(1, 10, '风电', '广东', 'wind')
    })

    it('should set isLoading during fetch', async () => {
      let resolvePromise: (value: unknown) => void
      const promise = new Promise((resolve) => { resolvePromise = resolve })
      vi.mocked(stationApi.listStations).mockReturnValue(promise as never)

      const store = useStationStore()
      const fetchPromise = store.fetchStations()

      expect(store.isLoading).toBe(true)

      resolvePromise!(mockStationList)
      await fetchPromise

      expect(store.isLoading).toBe(false)
    })

    it('should reset isLoading and set error on failure', async () => {
      vi.mocked(stationApi.listStations).mockRejectedValue(new Error('Network error'))

      const store = useStationStore()
      await expect(store.fetchStations()).rejects.toThrow()
      expect(store.isLoading).toBe(false)
      expect(store.error).toBe('Network error')
    })

    it('should clear error on successful fetch', async () => {
      vi.mocked(stationApi.listStations).mockRejectedValueOnce(new Error('fail'))

      const store = useStationStore()
      await expect(store.fetchStations()).rejects.toThrow()
      expect(store.error).toBe('fail')

      vi.mocked(stationApi.listStations).mockResolvedValue(mockStationList)
      await store.fetchStations()
      expect(store.error).toBeNull()
    })
  })

  describe('createStation', () => {
    it('should create station and refresh list', async () => {
      vi.mocked(stationApi.createStation).mockResolvedValue(mockStationList.items[0])
      vi.mocked(stationApi.listStations).mockResolvedValue(mockStationList)

      const store = useStationStore()
      const result = await store.createStation({
        name: '新电站',
        province: '山东',
        capacity_mw: 50,
        station_type: 'solar',
        has_storage: false,
      })

      expect(result.name).toBe('广东风电一号')
      expect(stationApi.createStation).toHaveBeenCalled()
      expect(stationApi.listStations).toHaveBeenCalled()
    })
  })

  describe('updateStation', () => {
    it('should update station and refresh list', async () => {
      vi.mocked(stationApi.updateStation).mockResolvedValue(mockStationList.items[0])
      vi.mocked(stationApi.listStations).mockResolvedValue(mockStationList)

      const store = useStationStore()
      await store.updateStation('1', { province: '山东' })

      expect(stationApi.updateStation).toHaveBeenCalledWith('1', { province: '山东' })
      expect(stationApi.listStations).toHaveBeenCalled()
    })
  })

  describe('deleteStation', () => {
    it('should delete station and refresh list', async () => {
      vi.mocked(stationApi.deleteStation).mockResolvedValue(undefined)
      vi.mocked(stationApi.listStations).mockResolvedValue(mockStationList)

      const store = useStationStore()
      await store.deleteStation('1')

      expect(stationApi.deleteStation).toHaveBeenCalledWith('1')
      expect(stationApi.listStations).toHaveBeenCalled()
    })
  })

  describe('binding operations', () => {
    it('should fetch user station bindings', async () => {
      const mockBindings = { station_ids: ['1', '2'], stations: mockStationList.items }
      vi.mocked(stationApi.getUserStationBindings).mockResolvedValue(mockBindings)

      const store = useStationStore()
      const result = await store.fetchUserStationBindings('user-1')

      expect(result.station_ids).toEqual(['1', '2'])
      expect(stationApi.getUserStationBindings).toHaveBeenCalledWith('user-1')
    })

    it('should update user station bindings', async () => {
      const mockResult = { station_ids: ['1'], stations: [mockStationList.items[0]] }
      vi.mocked(stationApi.updateUserStationBindings).mockResolvedValue(mockResult)

      const store = useStationStore()
      const result = await store.updateUserStationBindings('user-1', ['1'])

      expect(result.station_ids).toEqual(['1'])
      expect(stationApi.updateUserStationBindings).toHaveBeenCalledWith('user-1', ['1'])
    })

    it('should fetch user device bindings', async () => {
      const mockBindings = { device_ids: [], devices: [] }
      vi.mocked(stationApi.getUserDeviceBindings).mockResolvedValue(mockBindings)

      const store = useStationStore()
      const result = await store.fetchUserDeviceBindings('user-1')

      expect(result.device_ids).toEqual([])
    })

    it('should update user device bindings', async () => {
      const mockResult = { device_ids: ['d1'], devices: [] }
      vi.mocked(stationApi.updateUserDeviceBindings).mockResolvedValue(mockResult)

      const store = useStationStore()
      const result = await store.updateUserDeviceBindings('user-1', ['d1'])

      expect(result.device_ids).toEqual(['d1'])
    })
  })

  describe('fetchAllActiveStations', () => {
    it('should return active stations', async () => {
      vi.mocked(stationApi.listAllActiveStations).mockResolvedValue(mockStationList.items)

      const store = useStationStore()
      const result = await store.fetchAllActiveStations()

      expect(result).toEqual(mockStationList.items)
    })
  })

  describe('fetchAllActiveDevices', () => {
    it('should return active devices', async () => {
      const mockDevices = [
        { id: 'd1', station_id: '1', station_name: null, name: '储能设备A', capacity_mwh: '50.00', max_charge_rate_mw: '10.00', max_discharge_rate_mw: '10.00', soc_upper_limit: '0.9', soc_lower_limit: '0.1', is_active: true, created_at: '2026-01-01', updated_at: '2026-01-01' },
      ]
      vi.mocked(stationApi.listAllActiveDevices).mockResolvedValue(mockDevices)

      const store = useStationStore()
      const result = await store.fetchAllActiveDevices()

      expect(result).toEqual(mockDevices)
      expect(stationApi.listAllActiveDevices).toHaveBeenCalled()
    })
  })
})
