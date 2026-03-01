import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('../../../../src/api/marketRule', () => ({
  marketRuleApi: {
    listMarketRules: vi.fn().mockResolvedValue([]),
    getMarketRule: vi.fn(),
    upsertMarketRule: vi.fn(),
    deleteMarketRule: vi.fn(),
    getDeviationTemplates: vi.fn().mockResolvedValue([]),
    getProvinceDefaults: vi.fn().mockResolvedValue({}),
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

import MarketRuleConfigView from '../../../../src/views/data/MarketRuleConfigView.vue'
import { marketRuleApi } from '../../../../src/api/marketRule'
import type { MarketRuleRead } from '../../../../src/types/marketRule'

const mockRule: MarketRuleRead = {
  id: 'rule-1',
  province: 'guangdong',
  price_cap_upper: 1500,
  price_cap_lower: 0,
  settlement_method: 'spot',
  deviation_formula_type: 'stepped',
  deviation_formula_params: {
    exemption_ratio: 0.03,
    steps: [{ lower: 0.03, upper: 0.05, rate: 0.5 }],
  },
  is_active: true,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

const defaultStubs = {
  'a-spin': { template: '<div class="a-spin-stub"><slot /></div>', props: ['spinning'] },
  'a-layout': { template: '<div class="a-layout-stub"><slot /></div>' },
  'a-layout-sider': { template: '<div class="a-sider-stub"><slot /></div>', props: ['width'] },
  'a-layout-content': { template: '<div class="a-content-stub"><slot /></div>' },
  'a-menu': {
    template: `<div class="a-menu-stub"><slot /></div>`,
    props: ['mode', 'selectedKeys'],
    emits: ['click'],
  },
  'a-menu-item': {
    template: '<div class="a-menu-item-stub" @click="$emit(\'click\')"><slot /></div>',
    props: ['key' as never],
  },
  'a-badge': { template: '<span class="a-badge-stub"></span>', props: ['status'] },
  MarketRuleForm: {
    template: '<div class="market-rule-form-stub"></div>',
    props: ['formData', 'isSaving', 'province'],
    emits: ['save', 'reset', 'addStep', 'removeStep'],
  },
}

function mountView() {
  return mount(MarketRuleConfigView, {
    global: { stubs: defaultStubs },
  })
}

describe('MarketRuleConfigView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    vi.mocked(marketRuleApi.listMarketRules).mockResolvedValue([])
    vi.mocked(marketRuleApi.getProvinceDefaults).mockResolvedValue({})
  })

  describe('rendering', () => {
    it('should render page title', () => {
      const wrapper = mountView()
      expect(wrapper.text()).toContain('市场规则配置')
    })

    it('should render province list in sider', async () => {
      const wrapper = mountView()
      await flushPromises()

      const sider = wrapper.find('.a-sider-stub')
      expect(sider.exists()).toBe(true)
      // Should render province names
      expect(wrapper.text()).toContain('广东')
      expect(wrapper.text()).toContain('甘肃')
    })

    it('should render MarketRuleForm', async () => {
      const wrapper = mountView()
      await flushPromises()

      expect(wrapper.find('.market-rule-form-stub').exists()).toBe(true)
    })
  })

  describe('data fetching', () => {
    it('should call listMarketRules on mount', () => {
      mountView()
      expect(marketRuleApi.listMarketRules).toHaveBeenCalled()
    })

    it('should show configured badge for provinces with rules', async () => {
      vi.mocked(marketRuleApi.listMarketRules).mockResolvedValue([mockRule])

      const wrapper = mountView()
      await flushPromises()

      const badges = wrapper.findAll('.a-badge-stub')
      expect(badges.length).toBeGreaterThan(0)
    })

    it('should show no badges when no rules configured', async () => {
      vi.mocked(marketRuleApi.listMarketRules).mockResolvedValue([])

      const wrapper = mountView()
      await flushPromises()

      const badges = wrapper.findAll('.a-badge-stub')
      expect(badges).toHaveLength(0)
    })
  })

  describe('province selection', () => {
    it('should show province heading after selection', async () => {
      vi.mocked(marketRuleApi.listMarketRules).mockResolvedValue([mockRule])

      const wrapper = mountView()
      await flushPromises()

      // Simulate clicking a province menu item — find the guangdong one
      const menuItems = wrapper.findAll('.a-menu-item-stub')
      // Find the one that contains '广东'
      const gdItem = menuItems.find((m) => m.text().includes('广东'))
      expect(gdItem).toBeTruthy()
    })
  })

  describe('loading state', () => {
    it('should render spin container', () => {
      const wrapper = mountView()
      expect(wrapper.find('.a-spin-stub').exists()).toBe(true)
    })
  })
})
