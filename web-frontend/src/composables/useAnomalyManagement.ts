import { ref } from 'vue'
import { message } from 'ant-design-vue'
import { anomalyApi } from '@/api/anomaly'
import { getErrorMessage } from '@/api/errors'
import type { AnomalyStatsSummaryItem, ImportAnomaly, ImportAnomalyListResponse } from '@/types/dataImport'

export function useAnomalyManagement() {
  const anomalies = ref<ImportAnomaly[]>([])
  const total = ref(0)
  const isLoading = ref(false)
  const selectedIds = ref<Set<string>>(new Set())
  const summary = ref<AnomalyStatsSummaryItem[]>([])

  // 当前筛选条件（用于刷新时保持）
  let currentFilters: {
    page?: number
    page_size?: number
    anomaly_type?: string
    status?: string
    import_job_id?: string
  } = { status: 'pending' }

  async function loadAnomalies(filters?: {
    page?: number
    page_size?: number
    anomaly_type?: string
    status?: string
    import_job_id?: string
  }): Promise<void> {
    if (filters) {
      currentFilters = { ...filters }
    }
    isLoading.value = true
    try {
      const response: ImportAnomalyListResponse = await anomalyApi.listAnomalies(currentFilters)
      anomalies.value = response.items
      total.value = response.total
    } catch (e) {
      message.error(getErrorMessage(e, '加载异常数据失败'))
    } finally {
      isLoading.value = false
    }
  }

  async function loadSummary(params?: {
    import_job_id?: string
    status?: string
  }): Promise<void> {
    try {
      summary.value = await anomalyApi.getSummary(params ?? { status: 'pending' })
    } catch {
      // 统计加载失败不阻塞主功能
    }
  }

  async function correctAnomaly(anomalyId: string, correctedValue: string): Promise<boolean> {
    try {
      await anomalyApi.correctAnomaly(anomalyId, { corrected_value: correctedValue })
      message.success('修正成功')
      await loadAnomalies()
      return true
    } catch (e) {
      message.error(getErrorMessage(e, '修正失败'))
      return false
    }
  }

  async function confirmNormal(anomalyId: string): Promise<boolean> {
    try {
      await anomalyApi.confirmAnomalyNormal(anomalyId)
      message.success('已确认为正常数据')
      await loadAnomalies()
      return true
    } catch (e) {
      message.error(getErrorMessage(e, '确认失败'))
      return false
    }
  }

  async function bulkDelete(): Promise<boolean> {
    const ids = Array.from(selectedIds.value)
    if (ids.length === 0) return false
    try {
      const result = await anomalyApi.bulkAction({
        anomaly_ids: ids,
        action: 'delete',
      })
      message.success(`已删除 ${result.affected_count} 条异常数据`)
      selectedIds.value = new Set()
      await loadAnomalies()
      return true
    } catch (e) {
      message.error(getErrorMessage(e, '批量删除失败'))
      return false
    }
  }

  async function bulkConfirmNormal(): Promise<boolean> {
    const ids = Array.from(selectedIds.value)
    if (ids.length === 0) return false
    try {
      const result = await anomalyApi.bulkAction({
        anomaly_ids: ids,
        action: 'confirm_normal',
      })
      message.success(`已确认 ${result.affected_count} 条数据为正常`)
      selectedIds.value = new Set()
      await loadAnomalies()
      return true
    } catch (e) {
      message.error(getErrorMessage(e, '批量确认失败'))
      return false
    }
  }

  async function deleteAnomaly(anomalyId: string): Promise<boolean> {
    try {
      await anomalyApi.bulkAction({
        anomaly_ids: [anomalyId],
        action: 'delete',
      })
      message.success('已删除')
      await loadAnomalies()
      return true
    } catch (e) {
      message.error(getErrorMessage(e, '删除失败'))
      return false
    }
  }

  function toggleSelection(id: string): void {
    const newSet = new Set(selectedIds.value)
    if (newSet.has(id)) {
      newSet.delete(id)
    } else {
      newSet.add(id)
    }
    selectedIds.value = newSet
  }

  function clearSelection(): void {
    selectedIds.value = new Set()
  }

  return {
    anomalies,
    total,
    isLoading,
    selectedIds,
    summary,
    loadAnomalies,
    loadSummary,
    correctAnomaly,
    confirmNormal,
    deleteAnomaly,
    bulkDelete,
    bulkConfirmNormal,
    toggleSelection,
    clearSelection,
  }
}
