import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { defineComponent } from 'vue'

vi.mock('../../../src/api/anomaly', () => ({
  anomalyApi: {
    listAnomalies: vi.fn(),
    getAnomaly: vi.fn(),
    correctAnomaly: vi.fn(),
    confirmAnomalyNormal: vi.fn(),
    bulkAction: vi.fn(),
  },
}))

vi.mock('ant-design-vue', async () => {
  const actual = await vi.importActual('ant-design-vue')
  return {
    ...actual,
    message: {
      success: vi.fn(),
      error: vi.fn(),
      warning: vi.fn(),
    },
  }
})

import { useAnomalyManagement } from '../../../src/composables/useAnomalyManagement'
import { anomalyApi } from '../../../src/api/anomaly'
import { message } from 'ant-design-vue'
import type { ImportAnomaly, ImportAnomalyListResponse } from '../../../src/types/dataImport'

function withSetup<T>(composable: () => T): { result: T; unmount: () => void } {
  let result!: T
  const TestComponent = defineComponent({
    setup() {
      result = composable()
      return {}
    },
    template: '<div></div>',
  })
  const wrapper = mount(TestComponent)
  return { result, unmount: () => wrapper.unmount() }
}

const mockAnomaly: ImportAnomaly = {
  id: 'anomaly-1',
  import_job_id: 'job-1',
  row_number: 15,
  anomaly_type: 'format_error',
  field_name: 'clearing_price',
  raw_value: 'abc',
  description: '价格格式错误',
  status: 'pending',
  created_at: '2026-03-01T10:00:00+08:00',
  updated_at: '2026-03-01T10:00:00+08:00',
}

const mockListResponse: ImportAnomalyListResponse = {
  items: [mockAnomaly],
  total: 1,
  page: 1,
  page_size: 20,
}

describe('useAnomalyManagement', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('initial state', () => {
    it('should have empty anomalies', () => {
      const { result, unmount } = withSetup(() => useAnomalyManagement())
      expect(result.anomalies.value).toEqual([])
      unmount()
    })

    it('should have zero total', () => {
      const { result, unmount } = withSetup(() => useAnomalyManagement())
      expect(result.total.value).toBe(0)
      unmount()
    })

    it('should not be loading', () => {
      const { result, unmount } = withSetup(() => useAnomalyManagement())
      expect(result.isLoading.value).toBe(false)
      unmount()
    })

    it('should have empty selected ids', () => {
      const { result, unmount } = withSetup(() => useAnomalyManagement())
      expect(result.selectedIds.value.size).toBe(0)
      unmount()
    })
  })

  describe('loadAnomalies', () => {
    it('should load anomalies from API', async () => {
      vi.mocked(anomalyApi.listAnomalies).mockResolvedValue(mockListResponse)

      const { result, unmount } = withSetup(() => useAnomalyManagement())
      await result.loadAnomalies({ page: 1, page_size: 20, status: 'pending' })

      expect(anomalyApi.listAnomalies).toHaveBeenCalledWith({
        page: 1,
        page_size: 20,
        status: 'pending',
      })
      expect(result.anomalies.value).toEqual([mockAnomaly])
      expect(result.total.value).toBe(1)
      unmount()
    })

    it('should show error on failure', async () => {
      vi.mocked(anomalyApi.listAnomalies).mockRejectedValue(new Error('网络错误'))

      const { result, unmount } = withSetup(() => useAnomalyManagement())
      await result.loadAnomalies()

      expect(vi.mocked(message.error)).toHaveBeenCalled()
      unmount()
    })

    it('should manage loading state', async () => {
      let resolvePromise!: (value: ImportAnomalyListResponse) => void
      vi.mocked(anomalyApi.listAnomalies).mockReturnValue(
        new Promise((resolve) => { resolvePromise = resolve }),
      )

      const { result, unmount } = withSetup(() => useAnomalyManagement())
      const loadPromise = result.loadAnomalies()

      expect(result.isLoading.value).toBe(true)
      resolvePromise(mockListResponse)
      await loadPromise

      expect(result.isLoading.value).toBe(false)
      unmount()
    })

    it('should refresh with current filters when called without args', async () => {
      vi.mocked(anomalyApi.listAnomalies).mockResolvedValue(mockListResponse)

      const { result, unmount } = withSetup(() => useAnomalyManagement())
      await result.loadAnomalies({ anomaly_type: 'missing', status: 'pending' })
      await result.loadAnomalies()

      expect(anomalyApi.listAnomalies).toHaveBeenCalledTimes(2)
      expect(vi.mocked(anomalyApi.listAnomalies).mock.calls[1][0]).toEqual({
        anomaly_type: 'missing',
        status: 'pending',
      })
      unmount()
    })
  })

  describe('correctAnomaly', () => {
    it('should correct anomaly and reload', async () => {
      vi.mocked(anomalyApi.correctAnomaly).mockResolvedValue({
        ...mockAnomaly,
        status: 'corrected',
      })
      vi.mocked(anomalyApi.listAnomalies).mockResolvedValue(mockListResponse)

      const { result, unmount } = withSetup(() => useAnomalyManagement())
      const success = await result.correctAnomaly('anomaly-1', '350.00')

      expect(success).toBe(true)
      expect(anomalyApi.correctAnomaly).toHaveBeenCalledWith('anomaly-1', {
        corrected_value: '350.00',
      })
      expect(vi.mocked(message.success)).toHaveBeenCalledWith('修正成功')
      expect(anomalyApi.listAnomalies).toHaveBeenCalled()
      unmount()
    })

    it('should return false and show error on failure', async () => {
      vi.mocked(anomalyApi.correctAnomaly).mockRejectedValue(new Error('修正失败'))

      const { result, unmount } = withSetup(() => useAnomalyManagement())
      const success = await result.correctAnomaly('anomaly-1', '350.00')

      expect(success).toBe(false)
      expect(vi.mocked(message.error)).toHaveBeenCalled()
      unmount()
    })
  })

  describe('confirmNormal', () => {
    it('should confirm normal and reload', async () => {
      vi.mocked(anomalyApi.confirmAnomalyNormal).mockResolvedValue({
        ...mockAnomaly,
        status: 'confirmed_normal',
      })
      vi.mocked(anomalyApi.listAnomalies).mockResolvedValue(mockListResponse)

      const { result, unmount } = withSetup(() => useAnomalyManagement())
      const success = await result.confirmNormal('anomaly-1')

      expect(success).toBe(true)
      expect(anomalyApi.confirmAnomalyNormal).toHaveBeenCalledWith('anomaly-1')
      expect(vi.mocked(message.success)).toHaveBeenCalledWith('已确认为正常数据')
      unmount()
    })

    it('should return false on failure', async () => {
      vi.mocked(anomalyApi.confirmAnomalyNormal).mockRejectedValue(new Error('失败'))

      const { result, unmount } = withSetup(() => useAnomalyManagement())
      const success = await result.confirmNormal('anomaly-1')

      expect(success).toBe(false)
      expect(vi.mocked(message.error)).toHaveBeenCalled()
      unmount()
    })
  })

  describe('bulkDelete', () => {
    it('should delete selected and clear selection', async () => {
      vi.mocked(anomalyApi.bulkAction).mockResolvedValue({
        affected_count: 2,
        action: 'delete',
      })
      vi.mocked(anomalyApi.listAnomalies).mockResolvedValue(mockListResponse)

      const { result, unmount } = withSetup(() => useAnomalyManagement())
      result.selectedIds.value = new Set(['id-1', 'id-2'])
      const success = await result.bulkDelete()

      expect(success).toBe(true)
      expect(anomalyApi.bulkAction).toHaveBeenCalledWith({
        anomaly_ids: expect.arrayContaining(['id-1', 'id-2']),
        action: 'delete',
      })
      expect(vi.mocked(message.success)).toHaveBeenCalledWith('已删除 2 条异常数据')
      expect(result.selectedIds.value.size).toBe(0)
      unmount()
    })

    it('should return false when no ids selected', async () => {
      const { result, unmount } = withSetup(() => useAnomalyManagement())
      const success = await result.bulkDelete()

      expect(success).toBe(false)
      expect(anomalyApi.bulkAction).not.toHaveBeenCalled()
      unmount()
    })

    it('should return false on failure', async () => {
      vi.mocked(anomalyApi.bulkAction).mockRejectedValue(new Error('删除失败'))

      const { result, unmount } = withSetup(() => useAnomalyManagement())
      result.selectedIds.value = new Set(['id-1'])
      const success = await result.bulkDelete()

      expect(success).toBe(false)
      expect(vi.mocked(message.error)).toHaveBeenCalled()
      unmount()
    })
  })

  describe('bulkConfirmNormal', () => {
    it('should confirm selected and clear selection', async () => {
      vi.mocked(anomalyApi.bulkAction).mockResolvedValue({
        affected_count: 3,
        action: 'confirm_normal',
      })
      vi.mocked(anomalyApi.listAnomalies).mockResolvedValue(mockListResponse)

      const { result, unmount } = withSetup(() => useAnomalyManagement())
      result.selectedIds.value = new Set(['id-1', 'id-2', 'id-3'])
      const success = await result.bulkConfirmNormal()

      expect(success).toBe(true)
      expect(anomalyApi.bulkAction).toHaveBeenCalledWith({
        anomaly_ids: expect.arrayContaining(['id-1', 'id-2', 'id-3']),
        action: 'confirm_normal',
      })
      expect(vi.mocked(message.success)).toHaveBeenCalledWith('已确认 3 条数据为正常')
      expect(result.selectedIds.value.size).toBe(0)
      unmount()
    })

    it('should return false when no ids selected', async () => {
      const { result, unmount } = withSetup(() => useAnomalyManagement())
      const success = await result.bulkConfirmNormal()

      expect(success).toBe(false)
      unmount()
    })
  })

  describe('deleteAnomaly', () => {
    it('should delete single anomaly via bulk action', async () => {
      vi.mocked(anomalyApi.bulkAction).mockResolvedValue({
        affected_count: 1,
        action: 'delete',
      })
      vi.mocked(anomalyApi.listAnomalies).mockResolvedValue(mockListResponse)

      const { result, unmount } = withSetup(() => useAnomalyManagement())
      const success = await result.deleteAnomaly('anomaly-1')

      expect(success).toBe(true)
      expect(anomalyApi.bulkAction).toHaveBeenCalledWith({
        anomaly_ids: ['anomaly-1'],
        action: 'delete',
      })
      expect(vi.mocked(message.success)).toHaveBeenCalledWith('已删除')
      unmount()
    })

    it('should return false on failure', async () => {
      vi.mocked(anomalyApi.bulkAction).mockRejectedValue(new Error('失败'))

      const { result, unmount } = withSetup(() => useAnomalyManagement())
      const success = await result.deleteAnomaly('anomaly-1')

      expect(success).toBe(false)
      expect(vi.mocked(message.error)).toHaveBeenCalled()
      unmount()
    })
  })

  describe('toggleSelection', () => {
    it('should add id to selection', () => {
      const { result, unmount } = withSetup(() => useAnomalyManagement())
      result.toggleSelection('id-1')
      expect(result.selectedIds.value.has('id-1')).toBe(true)
      unmount()
    })

    it('should remove id from selection', () => {
      const { result, unmount } = withSetup(() => useAnomalyManagement())
      result.toggleSelection('id-1')
      result.toggleSelection('id-1')
      expect(result.selectedIds.value.has('id-1')).toBe(false)
      unmount()
    })
  })

  describe('clearSelection', () => {
    it('should clear all selections', () => {
      const { result, unmount } = withSetup(() => useAnomalyManagement())
      result.selectedIds.value = new Set(['id-1', 'id-2'])
      result.clearSelection()
      expect(result.selectedIds.value.size).toBe(0)
      unmount()
    })
  })
})
