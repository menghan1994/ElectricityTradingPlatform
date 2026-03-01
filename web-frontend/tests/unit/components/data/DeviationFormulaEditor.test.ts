import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

import DeviationFormulaEditor from '../../../../src/components/data/DeviationFormulaEditor.vue'

const defaultStubs = {
  'a-card': {
    template: '<div class="a-card-stub"><slot /></div>',
    props: ['size', 'title'],
  },
  'a-form-item': {
    template: '<div class="a-form-item-stub"><span>{{ label }}</span><slot /></div>',
    props: ['label', 'name'],
  },
  'a-input-number': {
    template: '<input class="a-input-number-stub" :value="value" @input="$emit(\'update:value\', parseFloat($event.target.value))" />',
    props: ['value', 'min', 'max', 'step', 'placeholder', 'addonAfter'],
  },
  'a-button': {
    template: '<button class="a-button-stub" @click="$emit(\'click\')"><slot /></button>',
    props: ['type', 'danger', 'size'],
  },
  'a-popconfirm': {
    template: '<div class="a-popconfirm-stub" @click="$emit(\'confirm\')"><slot /></div>',
    props: ['title'],
  },
}

function mountEditor(props: Record<string, unknown> = {}) {
  return mount(DeviationFormulaEditor, {
    props: {
      formulaType: 'stepped',
      exemptionRatio: 0.03,
      baseRate: null,
      bandwidthPercent: null,
      penaltyRate: null,
      steps: [{ lower: 0.03, upper: 0.05, rate: 0.5 }],
      ...props,
    },
    global: { stubs: defaultStubs },
  })
}

describe('DeviationFormulaEditor', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  describe('stepped formula', () => {
    it('should render stepped fields', () => {
      const wrapper = mountEditor()
      expect(wrapper.text()).toContain('免考核带')
      expect(wrapper.text()).toContain('阶梯 1')
    })

    it('should render exemption ratio hint text', () => {
      const wrapper = mountEditor()
      expect(wrapper.text()).toContain('取值 0~1，如 0.03 表示 3%')
    })

    it('should render add step button', () => {
      const wrapper = mountEditor()
      const addBtn = wrapper.findAll('.a-button-stub').find((b) => b.text().includes('添加阶梯'))
      expect(addBtn).toBeTruthy()
    })

    it('should emit update:exemptionRatio on input change', async () => {
      const wrapper = mountEditor()
      const inputs = wrapper.findAll('.a-input-number-stub')
      // First input is exemption ratio
      await inputs[0].setValue('0.05')
      expect(wrapper.emitted('update:exemptionRatio')).toBeTruthy()
    })

    it('should emit addStep when add button clicked', async () => {
      const wrapper = mountEditor()
      const addBtn = wrapper.findAll('.a-button-stub').find((b) => b.text().includes('添加阶梯'))
      await addBtn!.trigger('click')
      expect(wrapper.emitted('addStep')).toBeTruthy()
    })

    it('should emit removeStep when delete confirmed', async () => {
      const wrapper = mountEditor({
        steps: [
          { lower: 0.03, upper: 0.05, rate: 0.5 },
          { lower: 0.05, upper: 1.0, rate: 1.0 },
        ],
      })

      const popconfirm = wrapper.find('.a-popconfirm-stub')
      await popconfirm.trigger('click')
      expect(wrapper.emitted('removeStep')).toBeTruthy()
    })

    it('should not show delete button when only one step', () => {
      const wrapper = mountEditor()
      const popconfirms = wrapper.findAll('.a-popconfirm-stub')
      expect(popconfirms).toHaveLength(0)
    })

    it('should render multiple steps', () => {
      const wrapper = mountEditor({
        steps: [
          { lower: 0.03, upper: 0.05, rate: 0.5 },
          { lower: 0.05, upper: 1.0, rate: 1.0 },
        ],
      })
      expect(wrapper.text()).toContain('阶梯 1')
      expect(wrapper.text()).toContain('阶梯 2')
    })
  })

  describe('proportional formula', () => {
    it('should render proportional fields', () => {
      const wrapper = mountEditor({
        formulaType: 'proportional',
        exemptionRatio: 0.05,
        baseRate: 1.0,
      })
      expect(wrapper.text()).toContain('免考核带')
      expect(wrapper.text()).toContain('基础倍率')
    })

    it('should not render stepped fields', () => {
      const wrapper = mountEditor({
        formulaType: 'proportional',
      })
      expect(wrapper.text()).not.toContain('阶梯 1')
      expect(wrapper.text()).not.toContain('添加阶梯')
    })
  })

  describe('bandwidth formula', () => {
    it('should render bandwidth fields', () => {
      const wrapper = mountEditor({
        formulaType: 'bandwidth',
        bandwidthPercent: 0.02,
        penaltyRate: 0.8,
      })
      expect(wrapper.text()).toContain('带宽百分比')
      expect(wrapper.text()).toContain('罚金系数')
    })

    it('should not render stepped or proportional fields', () => {
      const wrapper = mountEditor({
        formulaType: 'bandwidth',
      })
      expect(wrapper.text()).not.toContain('阶梯 1')
      expect(wrapper.text()).not.toContain('基础倍率')
    })
  })

  describe('formula type switching', () => {
    it('should switch from stepped to proportional', async () => {
      const wrapper = mountEditor({ formulaType: 'stepped' })
      expect(wrapper.text()).toContain('阶梯 1')

      await wrapper.setProps({ formulaType: 'proportional' })
      expect(wrapper.text()).not.toContain('阶梯 1')
      expect(wrapper.text()).toContain('基础倍率')
    })

    it('should switch from proportional to bandwidth', async () => {
      const wrapper = mountEditor({ formulaType: 'proportional' })
      expect(wrapper.text()).toContain('基础倍率')

      await wrapper.setProps({ formulaType: 'bandwidth' })
      expect(wrapper.text()).not.toContain('基础倍率')
      expect(wrapper.text()).toContain('带宽百分比')
    })
  })
})
