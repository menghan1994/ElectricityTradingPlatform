import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { defineComponent } from 'vue'

vi.mock('../../../src/api/dataImport', () => ({
  dataImportApi: {
    uploadImportData: vi.fn(),
    listImportJobs: vi.fn(),
    getImportJob: vi.fn(),
    getImportResult: vi.fn(),
    getImportAnomalies: vi.fn(),
    resumeImport: vi.fn(),
    cancelImport: vi.fn(),
    getOutputRecords: vi.fn(),
    getStorageRecords: vi.fn(),
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

import { useDataImport } from '../../../src/composables/useDataImport'
import { dataImportApi } from '../../../src/api/dataImport'
import { message } from 'ant-design-vue'
import type { ImportJob, ImportJobListResponse, ImportResult } from '../../../src/types/dataImport'

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

const mockJob: ImportJob = {
  id: 'job-1',
  file_name: 'uploads/test.csv',
  original_file_name: 'test.csv',
  file_size: 1024,
  station_id: 'station-1',
  import_type: 'trading_data',
  status: 'pending',
  total_records: 0,
  processed_records: 0,
  success_records: 0,
  failed_records: 0,
  data_completeness: 0,
  last_processed_row: 0,
  celery_task_id: null,
  error_message: null,
  started_at: null,
  completed_at: null,
  imported_by: 'user-1',
  created_at: '2026-03-01T10:00:00+08:00',
  updated_at: '2026-03-01T10:00:00+08:00',
}

const mockResult: ImportResult = {
  total_records: 100,
  success_records: 95,
  failed_records: 5,
  data_completeness: 95.0,
  anomaly_summary: [{ anomaly_type: 'format_error', count: 5 }],
}

const mockHistory: ImportJobListResponse = {
  items: [mockJob],
  total: 1,
  page: 1,
  page_size: 20,
}

describe('useDataImport', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  describe('initial state', () => {
    it('should have null currentJob', () => {
      const { result, unmount } = withSetup(() => useDataImport())
      expect(result.currentJob.value).toBeNull()
      unmount()
    })

    it('should have null importResult', () => {
      const { result, unmount } = withSetup(() => useDataImport())
      expect(result.importResult.value).toBeNull()
      unmount()
    })

    it('should not be uploading', () => {
      const { result, unmount } = withSetup(() => useDataImport())
      expect(result.isUploading.value).toBe(false)
      unmount()
    })

    it('should not be polling', () => {
      const { result, unmount } = withSetup(() => useDataImport())
      expect(result.isPolling.value).toBe(false)
      unmount()
    })
  })

  describe('uploadFile', () => {
    it('should upload file and set currentJob on success', async () => {
      vi.mocked(dataImportApi.uploadImportData).mockResolvedValue(mockJob)
      vi.mocked(dataImportApi.getImportJob).mockResolvedValue(mockJob)

      const { result, unmount } = withSetup(() => useDataImport())
      const file = new File(['data'], 'test.csv', { type: 'text/csv' })

      await result.uploadFile(file, 'station-1')

      expect(dataImportApi.uploadImportData).toHaveBeenCalledWith(file, 'station-1', 'trading_data', undefined)
      expect(result.currentJob.value).toEqual(mockJob)
      expect(vi.mocked(message.success)).toHaveBeenCalledWith('文件上传成功，开始导入...')
      result.stopPolling()
      unmount()
    })

    it('should show error message on upload failure', async () => {
      vi.mocked(dataImportApi.uploadImportData).mockRejectedValue(new Error('网络错误'))

      const { result, unmount } = withSetup(() => useDataImport())
      const file = new File(['data'], 'test.csv', { type: 'text/csv' })

      await result.uploadFile(file, 'station-1')

      expect(vi.mocked(message.error)).toHaveBeenCalled()
      expect(result.isUploading.value).toBe(false)
      unmount()
    })

    it('should manage uploading state', async () => {
      let resolvePromise!: (value: ImportJob) => void
      vi.mocked(dataImportApi.uploadImportData).mockReturnValue(
        new Promise((resolve) => { resolvePromise = resolve }),
      )

      const { result, unmount } = withSetup(() => useDataImport())
      const file = new File(['data'], 'test.csv', { type: 'text/csv' })
      const uploadPromise = result.uploadFile(file, 'station-1')

      expect(result.isUploading.value).toBe(true)
      resolvePromise(mockJob)
      await uploadPromise

      expect(result.isUploading.value).toBe(false)
      result.stopPolling()
      unmount()
    })
  })

  describe('cancelImport', () => {
    it('should call cancel API and update currentJob', async () => {
      const cancelledJob = { ...mockJob, status: 'cancelled' as const }
      vi.mocked(dataImportApi.cancelImport).mockResolvedValue(cancelledJob)

      const { result, unmount } = withSetup(() => useDataImport())
      await result.cancelImport('job-1')

      expect(dataImportApi.cancelImport).toHaveBeenCalledWith('job-1')
      expect(result.currentJob.value?.status).toBe('cancelled')
      expect(vi.mocked(message.success)).toHaveBeenCalledWith('导入已取消')
      unmount()
    })

    it('should show error message on cancel failure', async () => {
      vi.mocked(dataImportApi.cancelImport).mockRejectedValue(new Error('取消失败'))

      const { result, unmount } = withSetup(() => useDataImport())
      await result.cancelImport('job-1')

      expect(vi.mocked(message.error)).toHaveBeenCalled()
      unmount()
    })
  })

  describe('resumeImport', () => {
    it('should call resume API and start polling', async () => {
      const resumedJob = { ...mockJob, status: 'processing' as const }
      vi.mocked(dataImportApi.resumeImport).mockResolvedValue(resumedJob)
      vi.mocked(dataImportApi.getImportJob).mockResolvedValue(resumedJob)

      const { result, unmount } = withSetup(() => useDataImport())
      await result.resumeImport('job-1')

      expect(dataImportApi.resumeImport).toHaveBeenCalledWith('job-1')
      expect(result.currentJob.value?.status).toBe('processing')
      expect(vi.mocked(message.success)).toHaveBeenCalledWith('正在恢复导入...')
      expect(result.isPolling.value).toBe(true)
      result.stopPolling()
      unmount()
    })

    it('should show error message on resume failure', async () => {
      vi.mocked(dataImportApi.resumeImport).mockRejectedValue(new Error('恢复失败'))

      const { result, unmount } = withSetup(() => useDataImport())
      await result.resumeImport('job-1')

      expect(vi.mocked(message.error)).toHaveBeenCalled()
      unmount()
    })
  })

  describe('loadImportHistory', () => {
    it('should load history from API with default import_type', async () => {
      vi.mocked(dataImportApi.listImportJobs).mockResolvedValue(mockHistory)

      const { result, unmount } = withSetup(() => useDataImport())
      await result.loadImportHistory()

      expect(dataImportApi.listImportJobs).toHaveBeenCalledWith({
        page: 1,
        page_size: 20,
        import_type: 'trading_data',
      })
      expect(result.importHistory.value).toEqual(mockHistory)
      unmount()
    })

    it('should pass stationId and import_type when provided', async () => {
      vi.mocked(dataImportApi.listImportJobs).mockResolvedValue(mockHistory)

      const { result, unmount } = withSetup(() => useDataImport())
      result.activeImportType.value = 'station_output'
      await result.loadImportHistory('station-1', 2, 10)

      expect(dataImportApi.listImportJobs).toHaveBeenCalledWith({
        page: 2,
        page_size: 10,
        station_id: 'station-1',
        import_type: 'station_output',
      })
      unmount()
    })

    it('should manage loading state', async () => {
      let resolvePromise!: (value: ImportJobListResponse) => void
      vi.mocked(dataImportApi.listImportJobs).mockReturnValue(
        new Promise((resolve) => { resolvePromise = resolve }),
      )

      const { result, unmount } = withSetup(() => useDataImport())
      const loadPromise = result.loadImportHistory()

      expect(result.isLoadingHistory.value).toBe(true)
      resolvePromise(mockHistory)
      await loadPromise

      expect(result.isLoadingHistory.value).toBe(false)
      unmount()
    })

    it('should show error on load failure', async () => {
      vi.mocked(dataImportApi.listImportJobs).mockRejectedValue(new Error('加载失败'))

      const { result, unmount } = withSetup(() => useDataImport())
      await result.loadImportHistory()

      expect(vi.mocked(message.error)).toHaveBeenCalled()
      unmount()
    })
  })

  describe('resetCurrentJob', () => {
    it('should reset currentJob and importResult', async () => {
      vi.mocked(dataImportApi.uploadImportData).mockResolvedValue(mockJob)
      vi.mocked(dataImportApi.getImportJob).mockResolvedValue(mockJob)

      const { result, unmount } = withSetup(() => useDataImport())
      await result.uploadFile(new File(['data'], 'test.csv'), 'station-1')

      result.resetCurrentJob()

      expect(result.currentJob.value).toBeNull()
      expect(result.importResult.value).toBeNull()
      expect(result.isPolling.value).toBe(false)
      unmount()
    })
  })

  describe('polling', () => {
    it('should stop polling when job completes', async () => {
      const completedJob = { ...mockJob, status: 'completed' as const, total_records: 100, processed_records: 100 }
      vi.mocked(dataImportApi.getImportJob).mockResolvedValue(completedJob)
      vi.mocked(dataImportApi.getImportResult).mockResolvedValue(mockResult)

      const { result, unmount } = withSetup(() => useDataImport())
      result.startPolling('job-1')

      expect(result.isPolling.value).toBe(true)

      await vi.advanceTimersByTimeAsync(3000)

      expect(result.isPolling.value).toBe(false)
      expect(result.currentJob.value?.status).toBe('completed')
      expect(vi.mocked(message.success)).toHaveBeenCalledWith('数据导入完成')
      unmount()
    })

    it('should show error when job fails', async () => {
      const failedJob = { ...mockJob, status: 'failed' as const, error_message: '文件格式错误' }
      vi.mocked(dataImportApi.getImportJob).mockResolvedValue(failedJob)

      const { result, unmount } = withSetup(() => useDataImport())
      result.startPolling('job-1')

      await vi.advanceTimersByTimeAsync(3000)

      expect(result.isPolling.value).toBe(false)
      expect(vi.mocked(message.error)).toHaveBeenCalledWith('文件格式错误')
      unmount()
    })

    it('should show warning when job is cancelled', async () => {
      const cancelledJob = { ...mockJob, status: 'cancelled' as const }
      vi.mocked(dataImportApi.getImportJob).mockResolvedValue(cancelledJob)

      const { result, unmount } = withSetup(() => useDataImport())
      result.startPolling('job-1')

      await vi.advanceTimersByTimeAsync(3000)

      expect(result.isPolling.value).toBe(false)
      expect(vi.mocked(message.warning)).toHaveBeenCalledWith('导入已取消')
      unmount()
    })

    it('should stop polling on stopPolling call', () => {
      const { result, unmount } = withSetup(() => useDataImport())
      result.startPolling('job-1')

      expect(result.isPolling.value).toBe(true)
      result.stopPolling()
      expect(result.isPolling.value).toBe(false)
      unmount()
    })

    it('should discard stale polling responses when startPolling is called again (pollingVersion)', async () => {
      const processingJob = { ...mockJob, status: 'processing' as const, total_records: 100, processed_records: 50 }
      const freshJob = { ...mockJob, status: 'processing' as const, total_records: 200, processed_records: 10 }

      // First call returns the stale job after a delay
      let resolveStale!: (value: ImportJob) => void
      vi.mocked(dataImportApi.getImportJob).mockReturnValueOnce(
        new Promise((resolve) => { resolveStale = resolve }),
      )

      const { result, unmount } = withSetup(() => useDataImport())
      result.startPolling('job-1')

      // Advance timer to trigger first poll
      vi.advanceTimersByTime(3000)

      // Before stale response resolves, start a new polling session (increments pollingVersion)
      vi.mocked(dataImportApi.getImportJob).mockResolvedValue(freshJob)
      result.startPolling('job-2')

      // Now resolve the stale response — it should be discarded
      resolveStale(processingJob)
      await vi.advanceTimersByTimeAsync(0)

      // The stale response should NOT have been applied
      // After the new polling starts and fires, the fresh job should be used
      await vi.advanceTimersByTimeAsync(3000)

      expect(result.currentJob.value).toEqual(freshJob)
      result.stopPolling()
      unmount()
    })

    it('should stop polling after MAX_POLL_ERRORS consecutive errors', async () => {
      vi.mocked(dataImportApi.getImportJob).mockRejectedValue(new Error('网络错误'))

      const { result, unmount } = withSetup(() => useDataImport())
      result.startPolling('job-1')

      // 5 consecutive errors (MAX_POLL_ERRORS = 5)
      for (let i = 0; i < 5; i++) {
        await vi.advanceTimersByTimeAsync(3000)
      }

      expect(result.isPolling.value).toBe(false)
      expect(vi.mocked(message.error)).toHaveBeenCalledWith('轮询服务器失败次数过多，已停止自动刷新')
      unmount()
    })

    it('should reset error count on successful poll', async () => {
      const processingJob = { ...mockJob, status: 'processing' as const, total_records: 100, processed_records: 50 }

      // First 3 calls fail, then succeed
      vi.mocked(dataImportApi.getImportJob)
        .mockRejectedValueOnce(new Error('错误1'))
        .mockRejectedValueOnce(new Error('错误2'))
        .mockRejectedValueOnce(new Error('错误3'))
        .mockResolvedValue(processingJob)

      const { result, unmount } = withSetup(() => useDataImport())
      result.startPolling('job-1')

      // 3 errors
      for (let i = 0; i < 3; i++) {
        await vi.advanceTimersByTimeAsync(3000)
      }

      // Still polling (< MAX_POLL_ERRORS)
      expect(result.isPolling.value).toBe(true)

      // Now succeeds — error count resets
      await vi.advanceTimersByTimeAsync(3000)
      expect(result.currentJob.value).toEqual(processingJob)
      expect(result.isPolling.value).toBe(true)

      result.stopPolling()
      unmount()
    })
  })

  describe('loadImportResult', () => {
    it('should show error message on failure', async () => {
      vi.mocked(dataImportApi.getImportResult).mockRejectedValue(new Error('获取失败'))

      const { result, unmount } = withSetup(() => useDataImport())
      await result.loadImportResult('job-1')

      expect(vi.mocked(message.error)).toHaveBeenCalled()
      unmount()
    })
  })

  describe('activeImportType and activeEmsFormat', () => {
    it('should default to trading_data', () => {
      const { result, unmount } = withSetup(() => useDataImport())
      expect(result.activeImportType.value).toBe('trading_data')
      unmount()
    })

    it('should default to standard ems format', () => {
      const { result, unmount } = withSetup(() => useDataImport())
      expect(result.activeEmsFormat.value).toBe('standard')
      unmount()
    })

    it('should pass ems format for storage_operation uploads', async () => {
      const storageJob = { ...mockJob, import_type: 'storage_operation' as const }
      vi.mocked(dataImportApi.uploadImportData).mockResolvedValue(storageJob)
      vi.mocked(dataImportApi.listImportJobs).mockResolvedValue(mockHistory)

      const { result, unmount } = withSetup(() => useDataImport())
      result.activeImportType.value = 'storage_operation'
      result.activeEmsFormat.value = 'sungrow'

      await result.uploadFile(new File(['data'], 'test.csv'), 'station-1')

      expect(dataImportApi.uploadImportData).toHaveBeenCalledWith(
        expect.any(File), 'station-1', 'storage_operation', 'sungrow',
      )
      result.stopPolling()
      unmount()
    })

    it('should not pass ems format for non-storage uploads', async () => {
      vi.mocked(dataImportApi.uploadImportData).mockResolvedValue(mockJob)
      vi.mocked(dataImportApi.listImportJobs).mockResolvedValue(mockHistory)

      const { result, unmount } = withSetup(() => useDataImport())
      result.activeImportType.value = 'station_output'

      await result.uploadFile(new File(['data'], 'test.csv'), 'station-1')

      expect(dataImportApi.uploadImportData).toHaveBeenCalledWith(
        expect.any(File), 'station-1', 'station_output', undefined,
      )
      result.stopPolling()
      unmount()
    })
  })
})
