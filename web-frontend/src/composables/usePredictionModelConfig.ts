import { onMounted, onUnmounted, ref } from 'vue'
import { message } from 'ant-design-vue'
import { predictionApi } from '@/api/prediction'
import { getErrorMessage } from '@/api/errors'
import type {
  ConnectionTestResult,
  PredictionModel,
  PredictionModelCreate,
  PredictionModelStatus,
  PredictionModelUpdate,
} from '@/types/prediction'

const STATUS_POLL_INTERVAL = 30 * 1000 // 30秒

export function usePredictionModelConfig() {
  const models = ref<PredictionModel[]>([])
  const modelsTotal = ref(0)
  const modelStatuses = ref<PredictionModelStatus[]>([])
  const isLoading = ref(false)
  const isTestingConnection = ref(false)
  let statusTimer: ReturnType<typeof setInterval> | null = null

  async function fetchModels(params?: {
    station_id?: string
    page?: number
    page_size?: number
  }) {
    isLoading.value = true
    try {
      const response = await predictionApi.getPredictionModels(params)
      models.value = response.items
      modelsTotal.value = response.total
    } catch (err) {
      message.error(getErrorMessage(err, '加载预测模型列表失败'))
    } finally {
      isLoading.value = false
    }
  }

  async function createModel(data: PredictionModelCreate): Promise<boolean> {
    try {
      await predictionApi.createPredictionModel(data)
      message.success('预测模型创建成功')
      return true
    } catch (err) {
      message.error(getErrorMessage(err, '创建预测模型失败'))
      return false
    }
  }

  async function updateModel(modelId: string, data: PredictionModelUpdate): Promise<boolean> {
    try {
      await predictionApi.updatePredictionModel(modelId, data)
      message.success('预测模型更新成功')
      return true
    } catch (err) {
      message.error(getErrorMessage(err, '更新预测模型失败'))
      return false
    }
  }

  async function deleteModel(modelId: string): Promise<boolean> {
    try {
      await predictionApi.deletePredictionModel(modelId)
      message.success('预测模型删除成功')
      return true
    } catch (err) {
      message.error(getErrorMessage(err, '删除预测模型失败'))
      return false
    }
  }

  async function testConnection(modelId: string): Promise<ConnectionTestResult | null> {
    isTestingConnection.value = true
    try {
      const result = await predictionApi.testConnection(modelId)
      if (result.success) {
        message.success(`连接成功，延迟 ${result.latency_ms}ms`)
      } else {
        message.warning(`连接失败: ${result.error_message}`)
      }
      await fetchModels()
      return result
    } catch (err) {
      message.error(getErrorMessage(err, '测试连接失败'))
      return null
    } finally {
      isTestingConnection.value = false
    }
  }

  const isFetching = ref(false)

  async function triggerFetch(modelId: string, predictionDate?: string): Promise<boolean> {
    isFetching.value = true
    try {
      const result = await predictionApi.triggerFetch(modelId, predictionDate)
      if (result.success) {
        message.success(`成功拉取 ${result.records_count} 条记录`)
      } else {
        message.error(`拉取失败: ${result.error_message}`)
      }
      await fetchModels()
      await fetchStatuses()
      return result.success
    } catch (err) {
      message.error(getErrorMessage(err, '拉取预测数据失败'))
      return false
    } finally {
      isFetching.value = false
    }
  }

  async function fetchStatuses() {
    try {
      const response = await predictionApi.getModelStatuses()
      modelStatuses.value = response.items
    } catch {
      // 静默失败
    }
  }

  function startStatusPolling() {
    fetchStatuses()
    statusTimer = setInterval(fetchStatuses, STATUS_POLL_INTERVAL)
  }

  function stopStatusPolling() {
    if (statusTimer) {
      clearInterval(statusTimer)
      statusTimer = null
    }
  }

  onMounted(startStatusPolling)
  onUnmounted(stopStatusPolling)

  return {
    models,
    modelsTotal,
    modelStatuses,
    isLoading,
    isTestingConnection,
    isFetching,
    fetchModels,
    createModel,
    updateModel,
    deleteModel,
    testConnection,
    triggerFetch,
    fetchStatuses,
  }
}
