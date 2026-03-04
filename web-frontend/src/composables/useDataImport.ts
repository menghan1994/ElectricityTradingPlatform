import { onScopeDispose, ref } from 'vue'
import { message } from 'ant-design-vue'
import { dataImportApi } from '@/api/dataImport'
import { getErrorMessage } from '@/api/errors'
import type { EmsFormat, ImportJob, ImportJobListResponse, ImportResult, ImportType } from '@/types/dataImport'

const MAX_POLL_ERRORS = 5

export function useDataImport() {
  const currentJob = ref<ImportJob | null>(null)
  const importResult = ref<ImportResult | null>(null)
  const isUploading = ref(false)
  const isPolling = ref(false)
  const importHistory = ref<ImportJobListResponse | null>(null)
  const isLoadingHistory = ref(false)
  const activeImportType = ref<ImportType>('trading_data')
  const activeEmsFormat = ref<EmsFormat>('standard')

  let pollingTimer: ReturnType<typeof setTimeout> | null = null
  let pollingVersion = 0
  let pollErrorCount = 0

  onScopeDispose(() => {
    stopPolling()
  })

  async function uploadFile(
    file: File,
    stationId: string,
    importType?: ImportType,
    emsFormat?: EmsFormat,
  ): Promise<void> {
    isUploading.value = true
    importResult.value = null
    const type = importType ?? activeImportType.value
    const format = emsFormat ?? (type === 'storage_operation' ? activeEmsFormat.value : undefined)
    try {
      const job = await dataImportApi.uploadImportData(file, stationId, type, format)
      currentJob.value = job
      message.success('文件上传成功，开始导入...')
      startPolling(job.id)
      // 静默刷新导入历史，失败不影响上传成功提示
      loadImportHistory().catch(() => {})
    } catch (e) {
      message.error(getErrorMessage(e, '文件上传失败，请稍后重试'))
    } finally {
      isUploading.value = false
    }
  }

  function startPolling(jobId: string): void {
    stopPolling()
    isPolling.value = true
    pollErrorCount = 0
    const version = ++pollingVersion

    async function pollOnce(): Promise<void> {
      if (version !== pollingVersion) return
      try {
        const job = await dataImportApi.getImportJob(jobId)
        if (version !== pollingVersion) return
        currentJob.value = job
        pollErrorCount = 0

        if (job.status === 'completed' || job.status === 'failed' || job.status === 'cancelled') {
          stopPolling()
          if (job.status === 'completed') {
            await loadImportResult(jobId)
            message.success('数据导入完成')
          } else if (job.status === 'failed') {
            message.error(job.error_message || '导入失败')
          } else {
            message.warning('导入已取消')
          }
          // 刷新导入历史列表
          await loadImportHistory()
          return
        }
      } catch {
        pollErrorCount++
        if (pollErrorCount >= MAX_POLL_ERRORS) {
          stopPolling()
          message.error('轮询服务器失败次数过多，已停止自动刷新')
          return
        }
      }
      // 递归 setTimeout：等当前请求完成后再调度下一次，避免请求堆积
      if (isPolling.value && version === pollingVersion) {
        pollingTimer = setTimeout(pollOnce, 3000)
      }
    }

    pollingTimer = setTimeout(pollOnce, 3000)
  }

  function stopPolling(): void {
    if (pollingTimer) {
      clearTimeout(pollingTimer)
      pollingTimer = null
    }
    isPolling.value = false
  }

  async function cancelImport(jobId: string): Promise<void> {
    try {
      const job = await dataImportApi.cancelImport(jobId)
      currentJob.value = job
      stopPolling()
      message.success('导入已取消')
      await loadImportHistory()
    } catch (e) {
      message.error(getErrorMessage(e, '取消失败，请稍后重试'))
    }
  }

  async function resumeImport(jobId: string): Promise<void> {
    try {
      const job = await dataImportApi.resumeImport(jobId)
      currentJob.value = job
      message.success('正在恢复导入...')
      startPolling(job.id)
    } catch (e) {
      message.error(getErrorMessage(e, '恢复失败，请稍后重试'))
    }
  }

  async function loadImportHistory(
    stationId?: string,
    page: number = 1,
    pageSize: number = 20,
    importType?: ImportType,
  ): Promise<void> {
    isLoadingHistory.value = true
    try {
      const params: Record<string, string | number> = { page, page_size: pageSize }
      if (stationId) params.station_id = stationId
      const type = importType ?? activeImportType.value
      if (type) params.import_type = type
      importHistory.value = await dataImportApi.listImportJobs(params)
    } catch (e) {
      message.error(getErrorMessage(e, '加载导入历史失败'))
    } finally {
      isLoadingHistory.value = false
    }
  }

  async function loadImportResult(jobId: string): Promise<void> {
    try {
      importResult.value = await dataImportApi.getImportResult(jobId)
    } catch (e) {
      message.error(getErrorMessage(e, '获取导入结果失败'))
    }
  }

  function resetCurrentJob(): void {
    stopPolling()
    currentJob.value = null
    importResult.value = null
  }

  return {
    currentJob,
    importResult,
    isUploading,
    isPolling,
    importHistory,
    isLoadingHistory,
    activeImportType,
    activeEmsFormat,
    uploadFile,
    startPolling,
    stopPolling,
    cancelImport,
    resumeImport,
    loadImportHistory,
    loadImportResult,
    resetCurrentJob,
  }
}
