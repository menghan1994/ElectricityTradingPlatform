import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import EmsFormatSelector from '../../../../src/components/data/EmsFormatSelector.vue'

function mountSelector(modelValue = 'standard' as string) {
  return mount(EmsFormatSelector, {
    props: { modelValue },
    global: {
      stubs: {
        'a-select': {
          template: '<div class="select"><slot /></div>',
          props: ['value'],
          emits: ['update:value'],
        },
        'a-select-option': {
          template: '<div class="option">{{ label || "" }}<slot /></div>',
          props: ['value', 'label'],
        },
      },
    },
  })
}

describe('EmsFormatSelector', () => {
  it('should render the component', () => {
    const wrapper = mountSelector()
    expect(wrapper.find('.select').exists()).toBe(true)
  })

  it('should display EMS 格式 label', () => {
    const wrapper = mountSelector()
    expect(wrapper.text()).toContain('EMS 格式')
  })

  it('should render 4 format options', () => {
    const wrapper = mountSelector()
    const options = wrapper.findAll('.option')
    expect(options).toHaveLength(4)
  })

  it('should display vendor names', () => {
    const wrapper = mountSelector()
    const text = wrapper.text()
    expect(text).toContain('标准格式')
    expect(text).toContain('阳光电源')
    expect(text).toContain('华为')
    expect(text).toContain('宁德时代')
  })
})
