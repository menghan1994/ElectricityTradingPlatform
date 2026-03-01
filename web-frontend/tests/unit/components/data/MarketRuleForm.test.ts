import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

import MarketRuleForm from '../../../../src/components/data/MarketRuleForm.vue'

const defaultStubs = {
  'a-form': {
    template: '<form class="a-form-stub"><slot /></form>',
    props: ['layout', 'model'],
    methods: { validateFields: () => Promise.resolve() },
  },
  'a-form-item': {
    template: '<div class="a-form-item-stub"><span>{{ label }}</span><slot /></div>',
    props: ['label', 'name', 'rules'],
  },
  'a-input-number': {
    template: '<input class="a-input-number-stub" :value="value" @input="$emit(\'update:value\', parseFloat($event.target.value))" />',
    props: ['value', 'min', 'step', 'placeholder'],
    emits: ['update:value'],
  },
  'a-select': {
    template: '<select class="a-select-stub" @change="$emit(\'update:value\', $event.target.value)"><option v-for="opt in options" :key="opt.value" :value="opt.value">{{ opt.label }}</option></select>',
    props: ['value', 'options', 'placeholder'],
    emits: ['update:value'],
  },
  'a-button': {
    template: '<button class="a-button-stub" @click="$emit(\'click\')"><slot /></button>',
    props: ['type', 'loading'],
  },
  DeviationFormulaEditor: {
    template: '<div class="deviation-editor-stub"></div>',
    props: ['formulaType', 'exemptionRatio', 'baseRate', 'bandwidthPercent', 'penaltyRate', 'steps'],
  },
}

function mountForm(props: Record<string, unknown> = {}) {
  return mount(MarketRuleForm, {
    props: {
      formData: {
        price_cap_upper: 1500,
        price_cap_lower: 0,
        settlement_method: 'spot',
        deviation_formula_type: 'stepped',
        exemption_ratio: 0.03,
        base_rate: null,
        bandwidth_percent: null,
        penalty_rate: null,
        steps: [{ lower: 0.03, upper: 0.05, rate: 0.5 }],
      },
      isSaving: false,
      province: 'guangdong',
      ...props,
    },
    global: { stubs: defaultStubs },
  })
}

describe('MarketRuleForm', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  describe('rendering', () => {
    it('should show placeholder when no province selected', () => {
      const wrapper = mountForm({ province: null })
      expect(wrapper.text()).toContain('请从左侧选择一个省份进行配置')
    })

    it('should show form when province is selected', () => {
      const wrapper = mountForm()
      expect(wrapper.find('.a-form-stub').exists()).toBe(true)
      expect(wrapper.text()).not.toContain('请从左侧选择一个省份进行配置')
    })

    it('should render price cap fields', () => {
      const wrapper = mountForm()
      expect(wrapper.text()).toContain('最高限价')
      expect(wrapper.text()).toContain('最低限价')
    })

    it('should render settlement method select', () => {
      const wrapper = mountForm()
      expect(wrapper.text()).toContain('结算方式')
      // Should render settlement options
      expect(wrapper.text()).toContain('现货结算')
    })

    it('should render formula type select', () => {
      const wrapper = mountForm()
      expect(wrapper.text()).toContain('偏差考核公式')
      // Should render formula type options
      expect(wrapper.text()).toContain('阶梯式')
    })

    it('should render DeviationFormulaEditor', () => {
      const wrapper = mountForm()
      expect(wrapper.find('.deviation-editor-stub').exists()).toBe(true)
    })

    it('should render save and reset buttons', () => {
      const wrapper = mountForm()
      const buttons = wrapper.findAll('.a-button-stub')
      expect(buttons.some((b) => b.text().includes('保存配置'))).toBe(true)
      expect(buttons.some((b) => b.text().includes('重置'))).toBe(true)
    })
  })

  describe('events', () => {
    it('should emit save after validation passes when save button clicked', async () => {
      const wrapper = mountForm()
      const saveBtn = wrapper.findAll('.a-button-stub').find((b) => b.text().includes('保存配置'))
      await saveBtn!.trigger('click')
      // Wait for async validateFields to resolve
      await wrapper.vm.$nextTick()
      expect(wrapper.emitted('save')).toBeTruthy()
    })

    it('should not emit save when validation fails', async () => {
      const failingStubs = {
        ...defaultStubs,
        'a-form': {
          template: '<form class="a-form-stub"><slot /></form>',
          props: ['layout', 'model'],
          methods: { validateFields: () => Promise.reject(new Error('validation failed')) },
        },
      }
      const wrapper = mount(MarketRuleForm, {
        props: {
          formData: {
            price_cap_upper: null,
            price_cap_lower: null,
            settlement_method: 'spot',
            deviation_formula_type: 'stepped',
            exemption_ratio: 0.03,
            base_rate: null,
            bandwidth_percent: null,
            penalty_rate: null,
            steps: [{ lower: 0.03, upper: 0.05, rate: 0.5 }],
          },
          isSaving: false,
          province: 'guangdong',
        },
        global: { stubs: failingStubs },
      })
      const saveBtn = wrapper.findAll('.a-button-stub').find((b) => b.text().includes('保存配置'))
      await saveBtn!.trigger('click')
      await wrapper.vm.$nextTick()
      expect(wrapper.emitted('save')).toBeFalsy()
    })

    it('should emit reset when reset button clicked', async () => {
      const wrapper = mountForm()
      const resetBtn = wrapper.findAll('.a-button-stub').find((b) => b.text().includes('重置'))
      await resetBtn!.trigger('click')
      expect(wrapper.emitted('reset')).toBeTruthy()
    })
  })

  describe('settlement method options', () => {
    it('should include all settlement methods', () => {
      const wrapper = mountForm()
      expect(wrapper.text()).toContain('现货结算')
      expect(wrapper.text()).toContain('合同结算')
      expect(wrapper.text()).toContain('混合结算')
    })
  })

  describe('formula type options', () => {
    it('should include all formula types', () => {
      const wrapper = mountForm()
      expect(wrapper.text()).toContain('阶梯式')
      expect(wrapper.text()).toContain('比例式')
      expect(wrapper.text()).toContain('带宽式')
    })
  })
})
