import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { mount, flushPromises } from '@vue/test-utils'
import { defineComponent } from 'vue'

vi.mock('../../../src/api/marketRule', () => ({
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

import { useMarketRuleConfig } from '../../../src/composables/useMarketRuleConfig'
import { marketRuleApi } from '../../../src/api/marketRule'
import { message } from 'ant-design-vue'
import type { MarketRuleRead } from '../../../src/types/marketRule'

function withSetup<T>(composable: () => T): { result: T; unmount: () => void } {
  let result!: T
  const TestComponent = defineComponent({
    setup() {
      result = composable()
      return {}
    },
    template: '<div></div>',
  })

  const pinia = createPinia()
  const wrapper = mount(TestComponent, {
    global: { plugins: [pinia] },
  })

  return { result, unmount: () => wrapper.unmount() }
}

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

describe('useMarketRuleConfig', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    vi.mocked(marketRuleApi.listMarketRules).mockResolvedValue([])
    vi.mocked(marketRuleApi.getProvinceDefaults).mockResolvedValue({})
  })

  describe('initial state', () => {
    it('should have empty rules', () => {
      const { result, unmount } = withSetup(() => useMarketRuleConfig())
      expect(result.rules.value).toEqual([])
      unmount()
    })

    it('should have no selected province', () => {
      const { result, unmount } = withSetup(() => useMarketRuleConfig())
      expect(result.selectedProvince.value).toBeNull()
      unmount()
    })

    it('should have default form data', () => {
      const { result, unmount } = withSetup(() => useMarketRuleConfig())
      expect(result.formData.settlement_method).toBe('spot')
      expect(result.formData.deviation_formula_type).toBe('stepped')
      expect(result.formData.price_cap_upper).toBeNull()
      expect(result.formData.price_cap_lower).toBeNull()
      unmount()
    })

    it('should have province list from constants', () => {
      const { result, unmount } = withSetup(() => useMarketRuleConfig())
      expect(result.provinceList.length).toBeGreaterThan(0)
      expect(result.provinceList[0]).toHaveProperty('label')
      expect(result.provinceList[0]).toHaveProperty('value')
      unmount()
    })
  })

  describe('loadRules', () => {
    it('should load rules from API', async () => {
      vi.mocked(marketRuleApi.listMarketRules).mockResolvedValue([mockRule])

      const { result, unmount } = withSetup(() => useMarketRuleConfig())
      await result.loadRules()

      expect(marketRuleApi.listMarketRules).toHaveBeenCalled()
      expect(result.rules.value).toHaveLength(1)
      expect(result.configuredProvinces.value.has('guangdong')).toBe(true)
      unmount()
    })

    it('should show error message on API failure', async () => {
      vi.mocked(marketRuleApi.listMarketRules).mockRejectedValue(new Error('Network error'))

      const { result, unmount } = withSetup(() => useMarketRuleConfig())
      await result.loadRules()

      expect(vi.mocked(message.error)).toHaveBeenCalledWith('Network error')
      unmount()
    })

    it('should manage loading state', async () => {
      let resolvePromise!: (value: MarketRuleRead[]) => void
      vi.mocked(marketRuleApi.listMarketRules).mockReturnValue(
        new Promise((resolve) => { resolvePromise = resolve })
      )

      const { result, unmount } = withSetup(() => useMarketRuleConfig())
      const loadPromise = result.loadRules()

      expect(result.isLoading.value).toBe(true)
      resolvePromise([])
      await loadPromise

      expect(result.isLoading.value).toBe(false)
      unmount()
    })
  })

  describe('selectProvince', () => {
    it('should prefill form with existing rule data', async () => {
      vi.mocked(marketRuleApi.listMarketRules).mockResolvedValue([mockRule])

      const { result, unmount } = withSetup(() => useMarketRuleConfig())
      await result.loadRules()
      await result.selectProvince('guangdong')

      expect(result.selectedProvince.value).toBe('guangdong')
      expect(result.formData.price_cap_upper).toBe(1500)
      expect(result.formData.price_cap_lower).toBe(0)
      expect(result.formData.settlement_method).toBe('spot')
      expect(result.formData.deviation_formula_type).toBe('stepped')
      expect(result.formData.exemption_ratio).toBe(0.03)
      expect(result.formData.steps).toHaveLength(1)
      unmount()
    })

    it('should load defaults for unconfigured province', async () => {
      vi.mocked(marketRuleApi.getProvinceDefaults).mockResolvedValue({
        price_cap_upper: 1000,
        price_cap_lower: 0,
        settlement_method: 'spot',
        deviation_formula_type: 'proportional',
        deviation_formula_params: {
          exemption_ratio: 0.05,
          base_rate: 1.0,
        },
      })

      const { result, unmount } = withSetup(() => useMarketRuleConfig())
      await result.selectProvince('gansu')

      expect(marketRuleApi.getProvinceDefaults).toHaveBeenCalledWith('gansu')
      expect(result.formData.price_cap_upper).toBe(1000)
      expect(result.formData.deviation_formula_type).toBe('proportional')
      expect(result.formData.exemption_ratio).toBe(0.05)
      expect(result.formData.base_rate).toBe(1.0)
      unmount()
    })

    it('should reset form when defaults API fails', async () => {
      vi.mocked(marketRuleApi.getProvinceDefaults).mockRejectedValue(new Error('404'))

      const { result, unmount } = withSetup(() => useMarketRuleConfig())
      await result.selectProvince('beijing')

      expect(result.formData.price_cap_upper).toBeNull()
      expect(result.formData.settlement_method).toBe('spot')
      unmount()
    })

    it('should reset form when defaults are empty', async () => {
      vi.mocked(marketRuleApi.getProvinceDefaults).mockResolvedValue({})

      const { result, unmount } = withSetup(() => useMarketRuleConfig())
      await result.selectProvince('beijing')

      expect(result.formData.price_cap_upper).toBeNull()
      unmount()
    })
  })

  describe('saveRule', () => {
    it('should warn if no province selected', async () => {
      const { result, unmount } = withSetup(() => useMarketRuleConfig())
      await result.saveRule()

      expect(vi.mocked(message.warning)).toHaveBeenCalledWith('请先选择省份')
      expect(marketRuleApi.upsertMarketRule).not.toHaveBeenCalled()
      unmount()
    })

    it('should warn if price caps are null', async () => {
      const { result, unmount } = withSetup(() => useMarketRuleConfig())
      result.selectedProvince.value = 'guangdong'
      await result.saveRule()

      expect(vi.mocked(message.warning)).toHaveBeenCalledWith('请填写限价范围')
      unmount()
    })

    it('should warn if upper <= lower', async () => {
      const { result, unmount } = withSetup(() => useMarketRuleConfig())
      result.selectedProvince.value = 'guangdong'
      result.formData.price_cap_upper = 100
      result.formData.price_cap_lower = 200
      await result.saveRule()

      expect(vi.mocked(message.warning)).toHaveBeenCalledWith('最高限价必须大于最低限价')
      unmount()
    })

    it('should call upsert API and reload on success', async () => {
      vi.mocked(marketRuleApi.upsertMarketRule).mockResolvedValue(mockRule)
      vi.mocked(marketRuleApi.listMarketRules).mockResolvedValue([mockRule])

      const { result, unmount } = withSetup(() => useMarketRuleConfig())
      result.selectedProvince.value = 'guangdong'
      result.formData.price_cap_upper = 1500
      result.formData.price_cap_lower = 0
      await result.saveRule()

      expect(marketRuleApi.upsertMarketRule).toHaveBeenCalledWith('guangdong', expect.objectContaining({
        price_cap_upper: 1500,
        price_cap_lower: 0,
        settlement_method: 'spot',
      }))
      expect(vi.mocked(message.success)).toHaveBeenCalledWith('市场规则保存成功')
      unmount()
    })

    it('should show error message on save failure', async () => {
      vi.mocked(marketRuleApi.upsertMarketRule).mockRejectedValue(new Error('保存失败'))

      const { result, unmount } = withSetup(() => useMarketRuleConfig())
      result.selectedProvince.value = 'guangdong'
      result.formData.price_cap_upper = 1500
      result.formData.price_cap_lower = 0
      await result.saveRule()

      expect(vi.mocked(message.error)).toHaveBeenCalledWith('保存失败')
      expect(result.isSaving.value).toBe(false)
      unmount()
    })

    it('should manage saving state', async () => {
      let resolvePromise!: (value: MarketRuleRead) => void
      vi.mocked(marketRuleApi.upsertMarketRule).mockReturnValue(
        new Promise((resolve) => { resolvePromise = resolve })
      )

      const { result, unmount } = withSetup(() => useMarketRuleConfig())
      result.selectedProvince.value = 'guangdong'
      result.formData.price_cap_upper = 1500
      result.formData.price_cap_lower = 0
      const savePromise = result.saveRule()

      expect(result.isSaving.value).toBe(true)
      resolvePromise(mockRule)
      await savePromise

      expect(result.isSaving.value).toBe(false)
      unmount()
    })
  })

  describe('step management', () => {
    it('should add a step based on last step upper', () => {
      const { result, unmount } = withSetup(() => useMarketRuleConfig())
      // Default has one step with upper=0.05
      result.addStep()

      expect(result.formData.steps).toHaveLength(2)
      expect(result.formData.steps[1].lower).toBe(0.05)
      expect(result.formData.steps[1].upper).toBe(1.0)
      expect(result.formData.steps[1].rate).toBe(1.0)
      unmount()
    })

    it('should remove a step when more than one', () => {
      const { result, unmount } = withSetup(() => useMarketRuleConfig())
      result.addStep()
      expect(result.formData.steps).toHaveLength(2)

      result.removeStep(0)
      expect(result.formData.steps).toHaveLength(1)
      unmount()
    })

    it('should not remove the last step', () => {
      const { result, unmount } = withSetup(() => useMarketRuleConfig())
      result.removeStep(0)
      expect(result.formData.steps).toHaveLength(1)
      unmount()
    })
  })

  describe('resetForm', () => {
    it('should re-select province to reload data', async () => {
      vi.mocked(marketRuleApi.listMarketRules).mockResolvedValue([mockRule])

      const { result, unmount } = withSetup(() => useMarketRuleConfig())
      await result.loadRules()
      await result.selectProvince('guangdong')

      // Modify form
      result.formData.price_cap_upper = 9999
      result.resetForm()
      await flushPromises()

      // Should reload from the existing rule
      expect(result.formData.price_cap_upper).toBe(1500)
      unmount()
    })

    it('should reset to empty when no province selected', () => {
      const { result, unmount } = withSetup(() => useMarketRuleConfig())
      result.formData.price_cap_upper = 9999
      result.resetForm()

      expect(result.formData.price_cap_upper).toBeNull()
      unmount()
    })
  })

  describe('formDataToCreatePayload', () => {
    it('should build stepped payload', async () => {
      vi.mocked(marketRuleApi.upsertMarketRule).mockResolvedValue(mockRule)
      vi.mocked(marketRuleApi.listMarketRules).mockResolvedValue([mockRule])

      const { result, unmount } = withSetup(() => useMarketRuleConfig())
      result.selectedProvince.value = 'guangdong'
      result.formData.price_cap_upper = 1500
      result.formData.price_cap_lower = 0
      result.formData.deviation_formula_type = 'stepped'
      result.formData.exemption_ratio = 0.03
      result.formData.steps = [{ lower: 0.03, upper: 0.05, rate: 0.5 }]
      await result.saveRule()

      const payload = vi.mocked(marketRuleApi.upsertMarketRule).mock.calls[0][1]
      expect(payload.deviation_formula_params).toEqual({
        exemption_ratio: 0.03,
        steps: [{ lower: 0.03, upper: 0.05, rate: 0.5 }],
      })
      unmount()
    })

    it('should build proportional payload', async () => {
      vi.mocked(marketRuleApi.upsertMarketRule).mockResolvedValue(mockRule)
      vi.mocked(marketRuleApi.listMarketRules).mockResolvedValue([mockRule])

      const { result, unmount } = withSetup(() => useMarketRuleConfig())
      result.selectedProvince.value = 'gansu'
      result.formData.price_cap_upper = 1000
      result.formData.price_cap_lower = 0
      result.formData.deviation_formula_type = 'proportional'
      result.formData.exemption_ratio = 0.05
      result.formData.base_rate = 1.0
      await result.saveRule()

      const payload = vi.mocked(marketRuleApi.upsertMarketRule).mock.calls[0][1]
      expect(payload.deviation_formula_params).toEqual({
        exemption_ratio: 0.05,
        base_rate: 1.0,
      })
      unmount()
    })

    it('should build bandwidth payload', async () => {
      vi.mocked(marketRuleApi.upsertMarketRule).mockResolvedValue(mockRule)
      vi.mocked(marketRuleApi.listMarketRules).mockResolvedValue([mockRule])

      const { result, unmount } = withSetup(() => useMarketRuleConfig())
      result.selectedProvince.value = 'shandong'
      result.formData.price_cap_upper = 2000
      result.formData.price_cap_lower = 0
      result.formData.deviation_formula_type = 'bandwidth'
      result.formData.bandwidth_percent = 0.02
      result.formData.penalty_rate = 0.8
      await result.saveRule()

      const payload = vi.mocked(marketRuleApi.upsertMarketRule).mock.calls[0][1]
      expect(payload.deviation_formula_params).toEqual({
        bandwidth_percent: 0.02,
        penalty_rate: 0.8,
      })
      unmount()
    })
  })
})
