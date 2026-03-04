import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { defineComponent } from 'vue'

vi.mock('../../../src/api/marketData', () => ({
  marketDataApi: {
    getMarketData: vi.fn(),
    getMarketDataFreshness: vi.fn(),
    triggerFetch: vi.fn(),
    uploadMarketData: vi.fn(),
    getDataSources: vi.fn(),
    createDataSource: vi.fn(),
    updateDataSource: vi.fn(),
    deleteDataSource: vi.fn(),
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

import { useMarketData } from '../../../src/composables/useMarketData'
import { marketDataApi } from '../../../src/api/marketData'
import { message } from 'ant-design-vue'
import type { MarketClearingPriceListResponse, MarketDataFreshnessListResponse } from '../../../src/types/marketData'

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

const mockPriceResponse: MarketClearingPriceListResponse = {
  items: [
    {
      id: 'price-1',
      trading_date: '2026-03-01',
      period: 1,
      province: 'guangdong',
      clearing_price: 350,
      source: 'api',
      fetched_at: '2026-03-01T07:00:00+08:00',
      import_job_id: null,
      created_at: '2026-03-01T07:00:00+08:00',
    },
  ],
  total: 1,
  page: 1,
  page_size: 96,
}

const mockFreshnessResponse: MarketDataFreshnessListResponse = {
  items: [
    {
      province: 'guangdong',
      last_updated: '2026-03-01T07:00:00+08:00',
      hours_ago: 1.0,
      status: 'fresh',
    },
  ],
}

describe('useMarketData', () => {
  let result: ReturnType<typeof useMarketData>
  let unmount: () => void

  beforeEach(() => {
    vi.useFakeTimers()
    vi.clearAllMocks()
    ;(marketDataApi.getMarketDataFreshness as ReturnType<typeof vi.fn>).mockResolvedValue(
      mockFreshnessResponse,
    )
    const setup = withSetup(useMarketData)
    result = setup.result
    unmount = setup.unmount
  })

  afterEach(() => {
    unmount()
    vi.useRealTimers()
  })

  describe('fetchMarketData', () => {
    it('should load market data successfully', async () => {
      ;(marketDataApi.getMarketData as ReturnType<typeof vi.fn>).mockResolvedValue(
        mockPriceResponse,
      )

      await result.fetchMarketData({ province: 'guangdong' })

      expect(result.marketDataList.value).toHaveLength(1)
      expect(result.marketDataTotal.value).toBe(1)
      expect(result.isLoading.value).toBe(false)
    })

    it('should show error on failure', async () => {
      ;(marketDataApi.getMarketData as ReturnType<typeof vi.fn>).mockRejectedValue(
        new Error('网络错误'),
      )

      await result.fetchMarketData({ province: 'guangdong' })

      expect(message.error).toHaveBeenCalled()
      expect(result.isLoading.value).toBe(false)
    })
  })

  describe('triggerManualFetch', () => {
    it('should trigger fetch and show success message', async () => {
      ;(marketDataApi.triggerFetch as ReturnType<typeof vi.fn>).mockResolvedValue({
        province: 'guangdong',
        trading_date: '2026-03-01',
        records_count: 96,
        status: 'success',
        error_message: null,
      })

      const fetchResult = await result.triggerManualFetch('guangdong', '2026-03-01')

      expect(fetchResult).not.toBeNull()
      expect(fetchResult!.status).toBe('success')
      expect(message.success).toHaveBeenCalledWith('成功获取 96 条数据')
    })

    it('should show warning on fetch failure', async () => {
      ;(marketDataApi.triggerFetch as ReturnType<typeof vi.fn>).mockResolvedValue({
        province: 'guangdong',
        trading_date: '2026-03-01',
        records_count: 0,
        status: 'failed',
        error_message: '连接超时',
      })

      const fetchResult = await result.triggerManualFetch('guangdong', '2026-03-01')

      expect(fetchResult!.status).toBe('failed')
      expect(message.warning).toHaveBeenCalled()
    })
  })

  describe('loadDataSources', () => {
    it('should load data sources', async () => {
      ;(marketDataApi.getDataSources as ReturnType<typeof vi.fn>).mockResolvedValue({
        items: [
          {
            id: 'source-1',
            province: 'guangdong',
            source_name: '广东',
            api_endpoint: 'https://example.com',
            api_auth_type: 'api_key',
            fetch_schedule: '0 7 * * *',
            is_active: true,
            last_fetch_at: null,
            last_fetch_status: 'pending',
            last_fetch_error: null,
            cache_ttl_seconds: 3600,
            created_at: '2026-03-01T00:00:00',
            updated_at: '2026-03-01T00:00:00',
          },
        ],
        total: 1,
        page: 1,
        page_size: 20,
      })

      await result.loadDataSources()

      expect(result.dataSourceList.value).toHaveLength(1)
      expect(result.dataSourceTotal.value).toBe(1)
    })
  })

  describe('freshness polling', () => {
    it('should poll freshness on mount', async () => {
      // onMounted triggers immediately
      await vi.runOnlyPendingTimersAsync()
      expect(marketDataApi.getMarketDataFreshness).toHaveBeenCalled()
    })
  })
})
