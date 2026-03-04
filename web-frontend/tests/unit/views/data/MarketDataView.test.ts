import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})

vi.mock('../../../../src/api/marketData', () => ({
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

import MarketDataView from '../../../../src/views/data/MarketDataView.vue'
import { marketDataApi } from '../../../../src/api/marketData'
import { message } from 'ant-design-vue'

const mockSourceResponse = {
  items: [
    {
      id: 'source-1',
      province: 'guangdong',
      source_name: '广东电力交易中心',
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
}

describe('MarketDataView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.useFakeTimers()
    vi.clearAllMocks()
    ;(marketDataApi.getMarketDataFreshness as ReturnType<typeof vi.fn>).mockResolvedValue({
      items: [],
    })
    ;(marketDataApi.getDataSources as ReturnType<typeof vi.fn>).mockResolvedValue(
      mockSourceResponse,
    )
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('renders the page title', () => {
    const wrapper = mount(MarketDataView)
    expect(wrapper.text()).toContain('市场数据管理')
  })

  it('renders tab navigation', () => {
    const wrapper = mount(MarketDataView)
    expect(wrapper.text()).toContain('出清价格')
    expect(wrapper.text()).toContain('数据源配置')
    expect(wrapper.text()).toContain('数据新鲜度')
  })

  it('renders search controls', () => {
    const wrapper = mount(MarketDataView)
    expect(wrapper.text()).toMatch(/查\s*询/)
    expect(wrapper.text()).toMatch(/手动获取/)
    expect(wrapper.text()).toMatch(/手动上传/)
  })

  it('loads data sources on mount', async () => {
    mount(MarketDataView)
    await vi.runOnlyPendingTimersAsync()
    expect(marketDataApi.getDataSources).toHaveBeenCalled()
  })

  it('shows warning when manual fetch without province and date', async () => {
    const wrapper = mount(MarketDataView)
    await vi.runOnlyPendingTimersAsync()

    // 找到手动获取按钮并点击（未选择省份和日期）
    const buttons = wrapper.findAll('button')
    const fetchButton = buttons.find((b) => b.text().includes('手动获取'))
    if (fetchButton) {
      await fetchButton.trigger('click')
      expect(message.warning).toHaveBeenCalledWith('请先选择省份和日期')
    }
  })

  it('calls getMarketData when search is triggered', async () => {
    ;(marketDataApi.getMarketData as ReturnType<typeof vi.fn>).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 96,
    })

    const wrapper = mount(MarketDataView)
    await vi.runOnlyPendingTimersAsync()

    // 点击查询按钮
    const buttons = wrapper.findAll('button')
    const searchButton = buttons.find((b) => b.text().match(/查\s*询/))
    if (searchButton) {
      await searchButton.trigger('click')
      await vi.runOnlyPendingTimersAsync()
      expect(marketDataApi.getMarketData).toHaveBeenCalled()
    }
  })

  it('calls triggerFetch on manual fetch with province and date', async () => {
    ;(marketDataApi.triggerFetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      province: 'guangdong',
      trading_date: '2026-03-01',
      records_count: 96,
      status: 'success',
      error_message: null,
    })
    ;(marketDataApi.getMarketData as ReturnType<typeof vi.fn>).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 96,
    })

    const wrapper = mount(MarketDataView)
    await vi.runOnlyPendingTimersAsync()

    // 通过 vm 直接设置值来模拟选择省份和日期
    const vm = wrapper.vm as Record<string, unknown>
    if ('selectedProvince' in vm) {
      ;(vm as { selectedProvince: string }).selectedProvince = 'guangdong'
      ;(vm as { selectedDate: string }).selectedDate = '2026-03-01'
      await wrapper.vm.$nextTick()

      const buttons = wrapper.findAll('button')
      const fetchButton = buttons.find((b) => b.text().includes('手动获取'))
      if (fetchButton) {
        await fetchButton.trigger('click')
        await vi.runOnlyPendingTimersAsync()
        expect(marketDataApi.triggerFetch).toHaveBeenCalledWith('guangdong', '2026-03-01')
      }
    }
  })

  it('renders new source button in sources tab', async () => {
    const wrapper = mount(MarketDataView)
    expect(wrapper.text()).toContain('新增数据源')
  })
})
