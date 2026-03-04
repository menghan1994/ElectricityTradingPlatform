import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'
import { createPinia, setActivePinia } from 'pinia'

const mockUploadFile = vi.fn()
const mockStopPolling = vi.fn()
const mockCancelImport = vi.fn()
const mockResumeImport = vi.fn()
const mockLoadImportHistory = vi.fn()
const mockResetCurrentJob = vi.fn()
const mockCurrentJob = ref(null)
const mockImportResult = ref(null)
const mockIsUploading = ref(false)
const mockIsPolling = ref(false)
const mockImportHistory = ref(null)
const mockIsLoadingHistory = ref(false)
const mockActiveImportType = ref('trading_data')
const mockActiveEmsFormat = ref('standard')

vi.mock('../../../../src/composables/useDataImport', () => ({
  useDataImport: () => ({
    currentJob: mockCurrentJob,
    importResult: mockImportResult,
    isUploading: mockIsUploading,
    isPolling: mockIsPolling,
    importHistory: mockImportHistory,
    isLoadingHistory: mockIsLoadingHistory,
    activeImportType: mockActiveImportType,
    activeEmsFormat: mockActiveEmsFormat,
    uploadFile: mockUploadFile,
    stopPolling: mockStopPolling,
    cancelImport: mockCancelImport,
    resumeImport: mockResumeImport,
    loadImportHistory: mockLoadImportHistory,
    resetCurrentJob: mockResetCurrentJob,
  }),
}))

vi.mock('../../../../src/stores/station', () => ({
  useStationStore: () => ({
    fetchAllActiveStations: vi.fn().mockResolvedValue([
      { id: 'station-1', name: '测试电站', province: 'guangdong' },
    ]),
  }),
}))

vi.mock('../../../../src/api/errors', () => ({
  getErrorMessage: vi.fn((_e: unknown, fallback: string) => fallback),
}))

import DataImportView from '../../../../src/views/data/DataImportView.vue'

describe('DataImportView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    mockCurrentJob.value = null
    mockImportResult.value = null
    mockIsUploading.value = false
    mockIsPolling.value = false
    mockImportHistory.value = null
    mockIsLoadingHistory.value = false
    mockActiveImportType.value = 'trading_data'
    mockActiveEmsFormat.value = 'standard'
  })

  function mountView() {
    return mount(DataImportView, {
      global: {
        stubs: {
          'a-tabs': {
            template: '<div class="tabs"><slot /></div>',
            props: ['activeKey'],
            emits: ['change'],
          },
          'a-tab-pane': {
            template: '<div class="tab-pane" />',
            props: ['tab'],
          },
          'a-spin': { template: '<div class="spin"><slot /></div>', props: ['spinning'] },
          'a-divider': { template: '<div class="divider"><slot /></div>' },
          'a-table': { template: '<div class="table" />', props: ['columns', 'dataSource', 'loading', 'pagination', 'rowKey', 'size'] },
          'a-tag': { template: '<span class="tag"><slot /></span>', props: ['color'] },
          'a-button': { template: '<button @click="$emit(\'click\')"><slot /></button>', emits: ['click'] },
          ImportUploader: {
            template: '<div class="uploader" />',
            props: ['stations', 'isUploading', 'importType', 'emsFormat'],
            emits: ['upload', 'update:emsFormat'],
          },
          ImportProgressPanel: {
            template: '<div class="progress-panel" />',
            props: ['job'],
            emits: ['cancel'],
          },
          ImportResultSummary: {
            template: '<div class="result-summary" />',
            props: ['job', 'result'],
            emits: ['resume'],
          },
        },
      },
    })
  }

  it('should render page title', () => {
    const wrapper = mountView()
    expect(wrapper.text()).toContain('数据导入')
  })

  it('should show uploader when no current job', () => {
    const wrapper = mountView()
    expect(wrapper.find('.uploader').exists()).toBe(true)
  })

  it('should hide uploader when job is completed and show result instead', async () => {
    mockCurrentJob.value = { id: 'job-1', status: 'completed' } as any
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.find('.uploader').exists()).toBe(false)
    expect(wrapper.find('.result-summary').exists()).toBe(true)
  })

  it('should show progress panel when job is processing', async () => {
    mockCurrentJob.value = { id: 'job-1', status: 'processing' } as any
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.find('.progress-panel').exists()).toBe(true)
    expect(wrapper.find('.uploader').exists()).toBe(false)
  })

  it('should show progress panel when job is pending', async () => {
    mockCurrentJob.value = { id: 'job-1', status: 'pending' } as any
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.find('.progress-panel').exists()).toBe(true)
  })

  it('should show result summary when job is completed', async () => {
    mockCurrentJob.value = { id: 'job-1', status: 'completed' } as any
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.find('.result-summary').exists()).toBe(true)
  })

  it('should show result summary when job is failed', async () => {
    mockCurrentJob.value = { id: 'job-1', status: 'failed' } as any
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.find('.result-summary').exists()).toBe(true)
  })

  it('should show result summary when job is cancelled', async () => {
    mockCurrentJob.value = { id: 'job-1', status: 'cancelled' } as any
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.find('.result-summary').exists()).toBe(true)
  })

  it('should load stations and history on mount', async () => {
    mountView()
    await flushPromises()
    expect(mockLoadImportHistory).toHaveBeenCalled()
  })

  it('should stop polling on unmount', () => {
    const wrapper = mountView()
    wrapper.unmount()
    expect(mockStopPolling).toHaveBeenCalled()
  })

  it('should render history divider', () => {
    const wrapper = mountView()
    expect(wrapper.text()).toContain('导入历史')
  })

  it('should render tabs for import types', () => {
    const wrapper = mountView()
    const tabPanes = wrapper.findAll('.tab-pane')
    expect(tabPanes).toHaveLength(3)
  })

  it('should handle tab change and reset job', async () => {
    const wrapper = mountView()
    const vm = wrapper.vm as any

    vm.handleTabChange('station_output')

    expect(mockActiveImportType.value).toBe('station_output')
    expect(mockResetCurrentJob).toHaveBeenCalled()
  })
})
