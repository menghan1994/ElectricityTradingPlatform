import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'

const mockLoadAnomalies = vi.fn()
const mockLoadSummary = vi.fn()
const mockCorrectAnomaly = vi.fn()
const mockConfirmNormal = vi.fn()
const mockDeleteAnomaly = vi.fn()
const mockBulkDelete = vi.fn()
const mockBulkConfirmNormal = vi.fn()
const mockClearSelection = vi.fn()
const mockAnomalies = ref<any[]>([])
const mockTotal = ref(0)
const mockIsLoading = ref(false)
const mockSelectedIds = ref(new Set<string>())
const mockSummary = ref<any[]>([])

vi.mock('../../../../src/composables/useAnomalyManagement', () => ({
  useAnomalyManagement: () => ({
    anomalies: mockAnomalies,
    total: mockTotal,
    isLoading: mockIsLoading,
    selectedIds: mockSelectedIds,
    summary: mockSummary,
    loadAnomalies: mockLoadAnomalies,
    loadSummary: mockLoadSummary,
    correctAnomaly: mockCorrectAnomaly,
    confirmNormal: mockConfirmNormal,
    deleteAnomaly: mockDeleteAnomaly,
    bulkDelete: mockBulkDelete,
    bulkConfirmNormal: mockBulkConfirmNormal,
    clearSelection: mockClearSelection,
  }),
}))

vi.mock('vue-router', () => ({
  useRoute: () => ({
    query: {},
  }),
}))

import AnomalyManagementView from '../../../../src/views/data/AnomalyManagementView.vue'

describe('AnomalyManagementView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockAnomalies.value = []
    mockTotal.value = 0
    mockIsLoading.value = false
    mockSelectedIds.value = new Set()
    mockSummary.value = []
  })

  function mountView() {
    return mount(AnomalyManagementView, {
      global: {
        stubs: {
          'a-table': {
            template: '<div class="table"><slot name="bodyCell" v-for="row in dataSource" :column="{ key: \'actions\' }" :record="row" /></div>',
            props: ['columns', 'dataSource', 'loading', 'rowSelection', 'pagination', 'rowKey', 'size', 'scroll'],
          },
          'a-tag': { template: '<span class="tag"><slot /></span>', props: ['color'] },
          'a-button': {
            template: '<button :disabled="disabled" :class="{ danger }" @click="$emit(\'click\')"><slot /></button>',
            props: ['type', 'size', 'danger', 'disabled', 'loading'],
            emits: ['click'],
          },
          'a-space': { template: '<div class="space"><slot /></div>' },
          'a-popconfirm': {
            template: '<div class="popconfirm"><slot /></div>',
            props: ['title'],
            emits: ['confirm'],
          },
          'a-row': { template: '<div class="row"><slot /></div>', props: ['gutter'] },
          'a-col': { template: '<div class="col"><slot /></div>', props: ['span'] },
          'a-card': { template: '<div class="card"><slot /></div>', props: ['size'] },
          'a-statistic': { template: '<div class="statistic" />', props: ['title', 'value'] },
          AnomalyFilterBar: {
            template: '<div class="filter-bar" />',
            props: ['initialFilters'],
            emits: ['search', 'reset'],
          },
          AnomalyCorrectModal: {
            template: '<div class="correct-modal" />',
            props: ['visible', 'anomaly'],
            emits: ['confirm', 'cancel'],
          },
        },
      },
    })
  }

  it('should render page title', () => {
    const wrapper = mountView()
    expect(wrapper.text()).toContain('异常数据管理')
  })

  it('should render filter bar', () => {
    const wrapper = mountView()
    expect(wrapper.find('.filter-bar').exists()).toBe(true)
  })

  it('should render table', () => {
    const wrapper = mountView()
    expect(wrapper.find('.table').exists()).toBe(true)
  })

  it('should render correct modal', () => {
    const wrapper = mountView()
    expect(wrapper.find('.correct-modal').exists()).toBe(true)
  })

  it('should load anomalies on mount', async () => {
    mountView()
    await flushPromises()
    expect(mockLoadAnomalies).toHaveBeenCalled()
  })

  it('should load with default pending filter', async () => {
    mountView()
    await flushPromises()
    expect(mockLoadAnomalies).toHaveBeenCalledWith(
      expect.objectContaining({ status: 'pending' }),
    )
  })

  it('should not show batch toolbar when nothing selected', () => {
    const wrapper = mountView()
    expect(wrapper.text()).not.toContain('已选中')
  })

  it('should show batch toolbar when items selected', async () => {
    mockSelectedIds.value = new Set(['id-1', 'id-2'])
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.text()).toContain('已选中 2 项')
  })

  it('should show batch confirm and delete buttons', async () => {
    mockSelectedIds.value = new Set(['id-1'])
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.text()).toContain('批量确认正常')
    expect(wrapper.text()).toContain('批量删除')
  })

  it('should handle search from filter bar', async () => {
    const wrapper = mountView()
    const vm = wrapper.vm as any

    vm.handleSearch({ anomaly_type: 'missing' })
    await flushPromises()

    expect(mockClearSelection).toHaveBeenCalled()
    expect(mockLoadAnomalies).toHaveBeenCalledWith(
      expect.objectContaining({ anomaly_type: 'missing' }),
    )
  })

  it('should handle reset from filter bar', async () => {
    const wrapper = mountView()
    const vm = wrapper.vm as any

    vm.handleReset()
    await flushPromises()

    expect(mockClearSelection).toHaveBeenCalled()
    expect(mockLoadAnomalies).toHaveBeenCalledWith(
      expect.objectContaining({ status: 'pending' }),
    )
  })

  it('should handle correct modal confirm', async () => {
    mockCorrectAnomaly.mockResolvedValue(true)
    const wrapper = mountView()
    const vm = wrapper.vm as any

    vm.currentAnomaly = {
      id: 'anomaly-1',
      status: 'pending',
      anomaly_type: 'format_error',
    }
    vm.correctModalVisible = true

    await vm.handleCorrect('350.00')
    await flushPromises()

    expect(mockCorrectAnomaly).toHaveBeenCalledWith('anomaly-1', '350.00')
  })

  it('should close modal after successful correction', async () => {
    mockCorrectAnomaly.mockResolvedValue(true)
    const wrapper = mountView()
    const vm = wrapper.vm as any

    vm.currentAnomaly = { id: 'anomaly-1' }
    vm.correctModalVisible = true

    await vm.handleCorrect('350.00')
    await flushPromises()

    expect(vm.correctModalVisible).toBe(false)
    expect(vm.currentAnomaly).toBeNull()
  })

  it('should keep modal open on correction failure', async () => {
    mockCorrectAnomaly.mockResolvedValue(false)
    const wrapper = mountView()
    const vm = wrapper.vm as any

    vm.currentAnomaly = { id: 'anomaly-1' }
    vm.correctModalVisible = true

    await vm.handleCorrect('350.00')
    await flushPromises()

    expect(vm.correctModalVisible).toBe(true)
  })

  it('should determine canCorrect based on status and type', () => {
    const wrapper = mountView()
    const vm = wrapper.vm as any

    expect(vm.canCorrect({ status: 'pending', anomaly_type: 'format_error' })).toBe(true)
    expect(vm.canCorrect({ status: 'pending', anomaly_type: 'duplicate' })).toBe(false)
    expect(vm.canCorrect({ status: 'corrected', anomaly_type: 'format_error' })).toBe(false)
  })
})
