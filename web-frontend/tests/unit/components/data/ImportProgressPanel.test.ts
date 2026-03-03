import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

import ImportProgressPanel from '../../../../src/components/data/ImportProgressPanel.vue'
import type { ImportJob } from '../../../../src/types/dataImport'

const baseJob: ImportJob = {
  id: 'job-1',
  file_name: 'uploads/test.csv',
  original_file_name: 'test.csv',
  file_size: 1024,
  station_id: 'station-1',
  status: 'processing',
  total_records: 1000,
  processed_records: 500,
  success_records: 480,
  failed_records: 20,
  data_completeness: 0,
  last_processed_row: 500,
  celery_task_id: 'task-1',
  error_message: null,
  started_at: '2026-03-01T10:00:00+08:00',
  completed_at: null,
  imported_by: 'user-1',
  created_at: '2026-03-01T10:00:00+08:00',
  updated_at: '2026-03-01T10:00:30+08:00',
}

describe('ImportProgressPanel', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  function mountPanel(job: Partial<ImportJob> = {}) {
    return mount(ImportProgressPanel, {
      props: {
        job: { ...baseJob, ...job },
      },
      global: {
        stubs: {
          'a-card': {
            template: '<div class="card"><slot /></div>',
            props: ['title', 'size'],
          },
          'a-progress': {
            template: '<div class="progress" :data-percent="percent" :data-status="status" />',
            props: ['percent', 'status', 'strokeColor'],
          },
          'a-popconfirm': {
            template: '<div class="popconfirm" @click="$emit(\'confirm\')"><slot /></div>',
            props: ['title', 'okText', 'cancelText'],
            emits: ['confirm'],
          },
          'a-button': {
            template: '<button :class="{ danger }" @click="$emit(\'click\')"><slot /></button>',
            props: ['danger', 'size'],
            emits: ['click'],
          },
        },
      },
    })
  }

  it('should calculate progress percentage correctly', () => {
    const wrapper = mountPanel({ total_records: 1000, processed_records: 500 })
    const progress = wrapper.find('.progress')
    expect(progress.attributes('data-percent')).toBe('50')
  })

  it('should show 0% when total_records is 0', () => {
    const wrapper = mountPanel({ total_records: 0, processed_records: 0 })
    const progress = wrapper.find('.progress')
    expect(progress.attributes('data-percent')).toBe('0')
  })

  it('should show active status when processing', () => {
    const wrapper = mountPanel({ status: 'processing' })
    const progress = wrapper.find('.progress')
    expect(progress.attributes('data-status')).toBe('active')
  })

  it('should show success status when completed', () => {
    const wrapper = mountPanel({ status: 'completed' })
    const progress = wrapper.find('.progress')
    expect(progress.attributes('data-status')).toBe('success')
  })

  it('should show exception status when failed', () => {
    const wrapper = mountPanel({ status: 'failed' })
    const progress = wrapper.find('.progress')
    expect(progress.attributes('data-status')).toBe('exception')
  })

  it('should display record count text', () => {
    const wrapper = mountPanel({ total_records: 1000, processed_records: 500 })
    expect(wrapper.text()).toContain('500')
    expect(wrapper.text()).toContain('1,000')
  })

  it('should show cancel button when processing', () => {
    const wrapper = mountPanel({ status: 'processing' })
    const cancelBtn = wrapper.find('.popconfirm')
    expect(cancelBtn.exists()).toBe(true)
  })

  it('should not show cancel button when not processing', () => {
    const wrapper = mountPanel({ status: 'completed' })
    const cancelBtn = wrapper.find('.popconfirm')
    expect(cancelBtn.exists()).toBe(false)
  })

  it('should emit cancel event on confirm', async () => {
    const wrapper = mountPanel({ status: 'processing' })
    await wrapper.find('.popconfirm').trigger('click')
    expect(wrapper.emitted('cancel')).toBeTruthy()
    expect(wrapper.emitted('cancel')![0]).toEqual(['job-1'])
  })

  it('should display error message when present', () => {
    const wrapper = mountPanel({ error_message: '文件解析失败' })
    expect(wrapper.text()).toContain('文件解析失败')
  })

  it('should not show error section when no error', () => {
    const wrapper = mountPanel({ error_message: null })
    expect(wrapper.text()).not.toContain('错误信息')
  })
})
