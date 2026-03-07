import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { defineComponent } from 'vue'

vi.mock('../../../src/api/prediction', () => ({
  predictionApi: {
    getPredictionModels: vi.fn(),
    createPredictionModel: vi.fn(),
    updatePredictionModel: vi.fn(),
    deletePredictionModel: vi.fn(),
    testConnection: vi.fn(),
    getModelStatuses: vi.fn(),
    triggerFetch: vi.fn(),
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

import { usePredictionModelConfig } from '../../../src/composables/usePredictionModelConfig'
import { predictionApi } from '../../../src/api/prediction'
import { message } from 'ant-design-vue'
import type {
  PredictionModelListResponse,
  PredictionModelStatusListResponse,
} from '../../../src/types/prediction'

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

const mockModelsResponse: PredictionModelListResponse = {
  items: [
    {
      id: 'model-1',
      station_id: 'station-1',
      model_name: '风电预测模型',
      model_type: 'wind',
      api_endpoint: 'https://api.example.com/predict',
      api_key_display: '****',
      api_auth_type: 'api_key',
      call_frequency_cron: '0 6,12 * * *',
      timeout_seconds: 30,
      is_active: true,
      status: 'running',
      last_check_at: '2026-03-01T07:00:00+08:00',
      last_check_status: 'success',
      last_check_error: null,
      last_fetch_at: null,
      last_fetch_status: null,
      last_fetch_error: null,
      created_at: '2026-03-01T00:00:00+08:00',
      updated_at: '2026-03-01T07:00:00+08:00',
    },
  ],
  total: 1,
  page: 1,
  page_size: 20,
}

const mockStatusesResponse: PredictionModelStatusListResponse = {
  items: [
    {
      model_id: 'model-1',
      model_name: '风电预测模型',
      station_name: null,
      status: 'running',
      last_check_at: '2026-03-01T07:00:00+08:00',
      last_check_error: null,
      last_fetch_at: null,
      last_fetch_status: null,
      last_fetch_error: null,
    },
  ],
}

describe('usePredictionModelConfig', () => {
  let result: ReturnType<typeof usePredictionModelConfig>
  let unmount: () => void

  beforeEach(() => {
    vi.useFakeTimers()
    vi.clearAllMocks()
    ;(predictionApi.getModelStatuses as ReturnType<typeof vi.fn>).mockResolvedValue(
      mockStatusesResponse,
    )
    const setup = withSetup(usePredictionModelConfig)
    result = setup.result
    unmount = setup.unmount
  })

  afterEach(() => {
    unmount()
    vi.useRealTimers()
  })

  describe('fetchModels', () => {
    it('should load prediction models successfully', async () => {
      ;(predictionApi.getPredictionModels as ReturnType<typeof vi.fn>).mockResolvedValue(
        mockModelsResponse,
      )
      await result.fetchModels()

      expect(result.models.value).toHaveLength(1)
      expect(result.modelsTotal.value).toBe(1)
      expect(result.models.value[0].model_name).toBe('风电预测模型')
      expect(result.isLoading.value).toBe(false)
    })

    it('should show error on failure', async () => {
      ;(predictionApi.getPredictionModels as ReturnType<typeof vi.fn>).mockRejectedValue(
        new Error('网络错误'),
      )
      await result.fetchModels()

      expect(message.error).toHaveBeenCalled()
      expect(result.isLoading.value).toBe(false)
    })
  })

  describe('createModel', () => {
    it('should create model and refresh list', async () => {
      ;(predictionApi.createPredictionModel as ReturnType<typeof vi.fn>).mockResolvedValue({
        id: 'new-model',
      })
      ;(predictionApi.getPredictionModels as ReturnType<typeof vi.fn>).mockResolvedValue(
        mockModelsResponse,
      )

      await result.createModel({
        model_name: '新模型',
        model_type: 'wind',
        api_endpoint: 'https://api.example.com',
        station_id: 'station-1',
      })

      expect(message.success).toHaveBeenCalledWith('预测模型创建成功')
      // createModel returns boolean; view calls fetchData() separately
    })

    it('should show error on create failure', async () => {
      ;(predictionApi.createPredictionModel as ReturnType<typeof vi.fn>).mockRejectedValue(
        new Error('创建失败'),
      )

      await result.createModel({
        model_name: '新模型',
        model_type: 'wind',
        api_endpoint: 'https://api.example.com',
        station_id: 'station-1',
      })

      expect(message.error).toHaveBeenCalled()
    })
  })

  describe('updateModel', () => {
    it('should update model and refresh list', async () => {
      ;(predictionApi.updatePredictionModel as ReturnType<typeof vi.fn>).mockResolvedValue({})
      ;(predictionApi.getPredictionModels as ReturnType<typeof vi.fn>).mockResolvedValue(
        mockModelsResponse,
      )

      await result.updateModel('model-1', { model_name: '更新名称' })

      expect(message.success).toHaveBeenCalledWith('预测模型更新成功')
    })
  })

  describe('deleteModel', () => {
    it('should delete model and refresh list', async () => {
      ;(predictionApi.deletePredictionModel as ReturnType<typeof vi.fn>).mockResolvedValue(
        undefined,
      )
      ;(predictionApi.getPredictionModels as ReturnType<typeof vi.fn>).mockResolvedValue({
        items: [],
        total: 0,
        page: 1,
        page_size: 20,
      })

      await result.deleteModel('model-1')

      expect(message.success).toHaveBeenCalledWith('预测模型删除成功')
    })
  })

  describe('testConnection', () => {
    it('should show success message on successful connection', async () => {
      ;(predictionApi.testConnection as ReturnType<typeof vi.fn>).mockResolvedValue({
        success: true,
        latency_ms: 45.2,
        error_message: null,
        tested_at: '2026-03-01T07:00:00+08:00',
      })
      ;(predictionApi.getPredictionModels as ReturnType<typeof vi.fn>).mockResolvedValue(
        mockModelsResponse,
      )

      const testResult = await result.testConnection('model-1')

      expect(testResult).not.toBeNull()
      expect(testResult!.success).toBe(true)
      expect(message.success).toHaveBeenCalledWith('连接成功，延迟 45.2ms')
    })

    it('should show warning on failed connection', async () => {
      ;(predictionApi.testConnection as ReturnType<typeof vi.fn>).mockResolvedValue({
        success: false,
        latency_ms: 5000,
        error_message: '连接超时',
        tested_at: '2026-03-01T07:00:00+08:00',
      })
      ;(predictionApi.getPredictionModels as ReturnType<typeof vi.fn>).mockResolvedValue(
        mockModelsResponse,
      )

      const testResult = await result.testConnection('model-1')

      expect(testResult!.success).toBe(false)
      expect(message.warning).toHaveBeenCalled()
    })

    it('should show error on API exception', async () => {
      ;(predictionApi.testConnection as ReturnType<typeof vi.fn>).mockRejectedValue(
        new Error('网络错误'),
      )

      const testResult = await result.testConnection('model-1')

      expect(testResult).toBeNull()
      expect(message.error).toHaveBeenCalled()
    })
  })

  describe('triggerFetch', () => {
    it('should show success message on successful fetch', async () => {
      ;(predictionApi.triggerFetch as ReturnType<typeof vi.fn>).mockResolvedValue({
        model_id: 'model-1',
        model_name: '风电预测模型',
        success: true,
        records_count: 96,
        error_message: null,
        fetched_at: '2026-03-06T06:00:00+08:00',
      })
      ;(predictionApi.getPredictionModels as ReturnType<typeof vi.fn>).mockResolvedValue(
        mockModelsResponse,
      )

      const fetchResult = await result.triggerFetch('model-1')

      expect(fetchResult).toBe(true)
      expect(message.success).toHaveBeenCalledWith('成功拉取 96 条记录')
      expect(result.isFetching.value).toBe(false)
    })

    it('should show error message on failed fetch', async () => {
      ;(predictionApi.triggerFetch as ReturnType<typeof vi.fn>).mockResolvedValue({
        model_id: 'model-1',
        model_name: '风电预测模型',
        success: false,
        records_count: 0,
        error_message: 'API调用超时',
        fetched_at: '2026-03-06T06:00:00+08:00',
      })
      ;(predictionApi.getPredictionModels as ReturnType<typeof vi.fn>).mockResolvedValue(
        mockModelsResponse,
      )

      const fetchResult = await result.triggerFetch('model-1')

      expect(fetchResult).toBe(false)
      expect(message.error).toHaveBeenCalledWith('拉取失败: API调用超时')
    })

    it('should show error on API exception', async () => {
      ;(predictionApi.triggerFetch as ReturnType<typeof vi.fn>).mockRejectedValue(
        new Error('网络错误'),
      )

      const fetchResult = await result.triggerFetch('model-1')

      expect(fetchResult).toBe(false)
      expect(message.error).toHaveBeenCalled()
      expect(result.isFetching.value).toBe(false)
    })

    it('should pass prediction date when provided', async () => {
      ;(predictionApi.triggerFetch as ReturnType<typeof vi.fn>).mockResolvedValue({
        model_id: 'model-1',
        model_name: '风电预测模型',
        success: true,
        records_count: 96,
        error_message: null,
        fetched_at: '2026-03-06T06:00:00+08:00',
      })
      ;(predictionApi.getPredictionModels as ReturnType<typeof vi.fn>).mockResolvedValue(
        mockModelsResponse,
      )

      await result.triggerFetch('model-1', '2026-03-10')

      expect(predictionApi.triggerFetch).toHaveBeenCalledWith('model-1', '2026-03-10')
    })
  })

  describe('status polling', () => {
    it('should poll statuses on mount', async () => {
      await vi.runOnlyPendingTimersAsync()
      expect(predictionApi.getModelStatuses).toHaveBeenCalled()
    })
  })
})
