import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'

vi.mock('../../../../src/api/marketData', () => ({
  marketDataApi: {
    getMarketDataFreshness: vi.fn(),
  },
}))

import DataFreshnessBadge from '../../../../src/components/common/DataFreshnessBadge.vue'
import { marketDataApi } from '../../../../src/api/marketData'

describe('DataFreshnessBadge', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.clearAllMocks()
    ;(marketDataApi.getMarketDataFreshness as ReturnType<typeof vi.fn>).mockResolvedValue({
      items: [],
    })
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('renders nothing when status is fresh', () => {
    const now = new Date().toISOString()
    const wrapper = mount(DataFreshnessBadge, {
      props: { province: 'guangdong', lastUpdated: now },
    })
    // fresh status renders nothing visible
    expect(wrapper.find('.ant-alert').exists()).toBe(false)
  })

  it('renders stale text when 2-12 hours old', () => {
    const sixHoursAgo = new Date(Date.now() - 6 * 3600 * 1000).toISOString()
    const wrapper = mount(DataFreshnessBadge, {
      props: { province: 'guangdong', lastUpdated: sixHoursAgo },
    })
    expect(wrapper.text()).toContain('数据更新于')
    expect(wrapper.text()).toContain('小时前')
  })

  it('renders critical alert when no data', () => {
    const wrapper = mount(DataFreshnessBadge, {
      props: { province: 'guangdong', lastUpdated: null },
    })
    expect(wrapper.text()).toContain('报价功能受限')
  })

  it('starts polling on mount when no freshnessData provided', async () => {
    mount(DataFreshnessBadge, {
      props: { province: 'guangdong' },
    })
    await vi.runOnlyPendingTimersAsync()
    expect(marketDataApi.getMarketDataFreshness).toHaveBeenCalled()
  })

  it('does NOT poll when freshnessData prop is provided', async () => {
    mount(DataFreshnessBadge, {
      props: {
        province: 'guangdong',
        freshnessData: {
          province: 'guangdong',
          last_updated: new Date().toISOString(),
          hours_ago: 0.5,
          status: 'fresh',
        },
      },
    })
    await vi.runOnlyPendingTimersAsync()
    expect(marketDataApi.getMarketDataFreshness).not.toHaveBeenCalled()
  })

  it('uses freshnessData prop status when provided', () => {
    const wrapper = mount(DataFreshnessBadge, {
      props: {
        province: 'guangdong',
        freshnessData: {
          province: 'guangdong',
          last_updated: null,
          hours_ago: null,
          status: 'critical',
        },
      },
    })
    expect(wrapper.text()).toContain('报价功能受限')
  })
})
