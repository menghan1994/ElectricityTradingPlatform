import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

import AnomalyCorrectModal from '../../../../src/components/data/AnomalyCorrectModal.vue'
import type { ImportAnomaly } from '../../../../src/types/dataImport'

const mockAnomaly: ImportAnomaly = {
  id: 'anomaly-1',
  import_job_id: 'job-1',
  row_number: 15,
  anomaly_type: 'format_error',
  field_name: 'clearing_price',
  raw_value: 'abc',
  description: '价格格式错误',
  status: 'pending',
  created_at: '2026-03-01T10:00:00+08:00',
  updated_at: '2026-03-01T10:00:00+08:00',
}

describe('AnomalyCorrectModal', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  function mountModal(props: Partial<{ visible: boolean; anomaly: ImportAnomaly | null }> = {}) {
    return mount(AnomalyCorrectModal, {
      props: {
        visible: props.visible ?? true,
        anomaly: props.anomaly ?? mockAnomaly,
      },
      global: {
        stubs: {
          'a-modal': {
            template: '<div class="modal" v-if="open"><slot /><slot name="footer" /></div>',
            props: ['open', 'title', 'okText', 'cancelText'],
            emits: ['ok', 'cancel'],
          },
          'a-descriptions': {
            template: '<div class="descriptions"><slot /></div>',
            props: ['column', 'bordered', 'size'],
          },
          'a-descriptions-item': {
            template: '<div class="desc-item" :data-label="label"><slot /></div>',
            props: ['label'],
          },
          'a-form-item': {
            template: '<div class="form-item"><slot /></div>',
            props: ['label', 'validateStatus', 'help'],
          },
          'a-input': {
            template: '<input class="input" :value="value" @input="$emit(\'update:value\', $event.target.value)" @keydown.enter="$emit(\'pressEnter\')" />',
            props: ['value', 'placeholder'],
            emits: ['update:value', 'pressEnter'],
          },
        },
      },
    })
  }

  it('should render modal when visible', () => {
    const wrapper = mountModal()
    expect(wrapper.find('.modal').exists()).toBe(true)
  })

  it('should not render content when not visible', () => {
    const wrapper = mountModal({ visible: false })
    expect(wrapper.find('.modal').exists()).toBe(false)
  })

  it('should display anomaly details', () => {
    const wrapper = mountModal()
    expect(wrapper.text()).toContain('15')
    expect(wrapper.text()).toContain('格式错误')
    expect(wrapper.text()).toContain('clearing_price')
    expect(wrapper.text()).toContain('abc')
    expect(wrapper.text()).toContain('价格格式错误')
  })

  it('should show field hint for clearing_price', () => {
    const wrapper = mountModal()
    const formItem = wrapper.find('.form-item')
    expect(formItem.exists()).toBe(true)
  })

  it('should emit confirm with trimmed value', async () => {
    const wrapper = mountModal()
    const vm = wrapper.vm as any

    vm.correctedValue = '  350.00  '
    vm.handleConfirm()

    expect(wrapper.emitted('confirm')).toBeTruthy()
    expect(wrapper.emitted('confirm')![0]).toEqual(['350.00'])
  })

  it('should not emit confirm when value is empty', () => {
    const wrapper = mountModal()
    const vm = wrapper.vm as any

    vm.correctedValue = ''
    vm.handleConfirm()

    expect(wrapper.emitted('confirm')).toBeFalsy()
    expect(vm.validationError).toBe('修正值不能为空')
  })

  it('should not emit confirm when value is whitespace only', () => {
    const wrapper = mountModal()
    const vm = wrapper.vm as any

    vm.correctedValue = '   '
    vm.handleConfirm()

    expect(wrapper.emitted('confirm')).toBeFalsy()
    expect(vm.validationError).toBe('修正值不能为空')
  })

  it('should emit cancel', () => {
    const wrapper = mountModal()
    const vm = wrapper.vm as any

    vm.handleCancel()

    expect(wrapper.emitted('cancel')).toBeTruthy()
  })

  it('should reset state when visibility changes to true', async () => {
    const wrapper = mountModal({ visible: false })
    const vm = wrapper.vm as any

    vm.correctedValue = 'old value'
    vm.validationError = 'some error'

    await wrapper.setProps({ visible: true })
    await flushPromises()

    expect(vm.correctedValue).toBe('')
    expect(vm.validationError).toBe('')
  })

  it('should display dash for null raw_value', () => {
    const anomalyNoRaw = { ...mockAnomaly, raw_value: null }
    const wrapper = mountModal({ anomaly: anomalyNoRaw })
    expect(wrapper.text()).toContain('-')
  })

  it('should show type label for missing type', () => {
    const missingAnomaly = { ...mockAnomaly, anomaly_type: 'missing' as const }
    const wrapper = mountModal({ anomaly: missingAnomaly })
    expect(wrapper.text()).toContain('缺失')
  })
})
