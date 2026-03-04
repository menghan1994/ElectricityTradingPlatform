import { onMounted, onUnmounted, ref } from 'vue'
import { message } from 'ant-design-vue'
import { marketDataApi } from '@/api/marketData'
import { getErrorMessage } from '@/api/errors'
import type {
  MarketClearingPrice,
  MarketDataFetchResult,
  MarketDataFreshness,
  MarketDataSource,
} from '@/types/marketData'

const FRESHNESS_POLL_INTERVAL = 5 * 60 * 1000 // 5分钟

export function useMarketData() {
  const marketDataList = ref<MarketClearingPrice[]>([])
  const marketDataTotal = ref(0)
  const freshnessMap = ref<MarketDataFreshness[]>([])
  const dataSourceList = ref<MarketDataSource[]>([])
  const dataSourceTotal = ref(0)
  const isLoading = ref(false)
  const isLoadingSources = ref(false)
  const isFetching = ref(false)
  const isUploading = ref(false)
  let freshnessTimer: ReturnType<typeof setInterval> | null = null

  async function fetchMarketData(params: {
    province?: string
    trading_date?: string
    page?: number
    page_size?: number
  }) {
    isLoading.value = true
    try {
      const response = await marketDataApi.getMarketData(params)
      marketDataList.value = response.items
      marketDataTotal.value = response.total
    } catch (err) {
      message.error(getErrorMessage(err, '加载市场数据失败'))
    } finally {
      isLoading.value = false
    }
  }

  async function loadFreshness() {
    try {
      const response = await marketDataApi.getMarketDataFreshness()
      freshnessMap.value = response.items
    } catch {
      // 静默失败
    }
  }

  async function triggerManualFetch(
    province: string,
    tradingDate: string,
  ): Promise<MarketDataFetchResult | null> {
    isFetching.value = true
    try {
      const result = await marketDataApi.triggerFetch(province, tradingDate)
      if (result.status === 'success') {
        message.success(`成功获取 ${result.records_count} 条数据`)
      } else {
        message.warning(`获取失败: ${result.error_message}`)
      }
      return result
    } catch (err) {
      message.error(getErrorMessage(err, '手动获取市场数据失败'))
      return null
    } finally {
      isFetching.value = false
    }
  }

  async function uploadMarketData(
    file: File,
    province: string,
  ): Promise<MarketDataFetchResult | null> {
    isUploading.value = true
    try {
      const result = await marketDataApi.uploadMarketData(file, province)
      if (result.status === 'success') {
        message.success(`成功导入 ${result.records_count} 条数据`)
      } else {
        message.warning(`导入失败: ${result.error_message}`)
      }
      return result
    } catch (err) {
      message.error(getErrorMessage(err, '上传市场数据失败'))
      return null
    } finally {
      isUploading.value = false
    }
  }

  // --- 数据源管理 ---

  async function loadDataSources(params?: {
    page?: number
    page_size?: number
    is_active?: boolean
  }) {
    isLoadingSources.value = true
    try {
      const response = await marketDataApi.getDataSources(params)
      dataSourceList.value = response.items
      dataSourceTotal.value = response.total
    } catch (err) {
      message.error(getErrorMessage(err, '加载数据源列表失败'))
    } finally {
      isLoadingSources.value = false
    }
  }

  async function createDataSource(data: Parameters<typeof marketDataApi.createDataSource>[0]) {
    try {
      await marketDataApi.createDataSource(data)
      message.success('数据源创建成功')
      await loadDataSources()
    } catch (err) {
      message.error(getErrorMessage(err, '创建数据源失败'))
    }
  }

  async function updateDataSource(
    sourceId: string,
    data: Parameters<typeof marketDataApi.updateDataSource>[1],
  ) {
    try {
      await marketDataApi.updateDataSource(sourceId, data)
      message.success('数据源更新成功')
      await loadDataSources()
    } catch (err) {
      message.error(getErrorMessage(err, '更新数据源失败'))
    }
  }

  async function deleteDataSource(sourceId: string) {
    try {
      await marketDataApi.deleteDataSource(sourceId)
      message.success('数据源删除成功')
      await loadDataSources()
    } catch (err) {
      message.error(getErrorMessage(err, '删除数据源失败'))
    }
  }

  function startFreshnessPolling() {
    loadFreshness()
    freshnessTimer = setInterval(loadFreshness, FRESHNESS_POLL_INTERVAL)
  }

  function stopFreshnessPolling() {
    if (freshnessTimer) {
      clearInterval(freshnessTimer)
      freshnessTimer = null
    }
  }

  onMounted(startFreshnessPolling)
  onUnmounted(stopFreshnessPolling)

  return {
    marketDataList,
    marketDataTotal,
    freshnessMap,
    dataSourceList,
    dataSourceTotal,
    isLoading,
    isLoadingSources,
    isFetching,
    isUploading,
    fetchMarketData,
    loadFreshness,
    triggerManualFetch,
    uploadMarketData,
    loadDataSources,
    createDataSource,
    updateDataSource,
    deleteDataSource,
  }
}
