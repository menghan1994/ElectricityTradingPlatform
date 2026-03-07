import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

// Mock window.matchMedia for ant-design-vue
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})

vi.mock('../../../../src/composables/usePredictionModelConfig', () => ({
  usePredictionModelConfig: vi.fn(() => ({
    models: { value: [] },
    modelsTotal: { value: 0 },
    modelStatuses: { value: [] },
    isLoading: { value: false },
    isTestingConnection: { value: false },
    isFetching: { value: false },
    fetchModels: vi.fn(),
    createModel: vi.fn(),
    updateModel: vi.fn(),
    deleteModel: vi.fn(),
    testConnection: vi.fn(),
    triggerFetch: vi.fn(),
    fetchStatuses: vi.fn(),
  })),
}))

vi.mock('../../../../src/api/station', () => ({
  stationApi: {
    listStations: vi.fn().mockResolvedValue({ items: [], total: 0 }),
  },
}))

vi.mock('vue-router', () => ({
  useRoute: vi.fn(() => ({ query: {} })),
  useRouter: vi.fn(() => ({ push: vi.fn() })),
}))

import PredictionModelConfigView from '../../../../src/views/data/PredictionModelConfigView.vue'
import { usePredictionModelConfig } from '../../../../src/composables/usePredictionModelConfig'

describe('PredictionModelConfigView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should render page title', () => {
    const wrapper = mount(PredictionModelConfigView, {
      global: {
        stubs: {
          'a-button': true,
          'a-table': true,
          'a-modal': true,
          'a-card': true,
          'a-row': true,
          'a-col': true,
          'a-statistic': true,
          'a-select': true,
          'a-select-option': true,
          'a-alert': true,
          'a-form': true,
          'a-form-item': true,
          'a-input': true,
          'a-input-password': true,
          'a-input-number': true,
          'a-space': true,
          'a-tag': true,
          'a-tooltip': true,
          'a-popconfirm': true,
          'a-date-picker': true,
        },
      },
    })
    expect(wrapper.text()).toContain('预测模型配置')
  })

  it('should render status cards', () => {
    const mockComposable = usePredictionModelConfig as ReturnType<typeof vi.fn>
    mockComposable.mockReturnValue({
      models: {
        value: [
          { id: '1', status: 'running', station_id: 's1', is_active: true },
          { id: '2', status: 'error', station_id: 's2', is_active: true },
          { id: '3', status: 'disabled', station_id: 's3', is_active: false },
        ],
      },
      modelsTotal: { value: 3 },
      modelStatuses: { value: [] },
      isLoading: { value: false },
      isTestingConnection: { value: false },
      isFetching: { value: false },
      fetchModels: vi.fn(),
      createModel: vi.fn(),
      updateModel: vi.fn(),
      deleteModel: vi.fn(),
      testConnection: vi.fn(),
      triggerFetch: vi.fn(),
      fetchStatuses: vi.fn(),
    })

    const wrapper = mount(PredictionModelConfigView, {
      global: {
        stubs: {
          'a-button': true,
          'a-table': true,
          'a-modal': true,
          'a-card': { template: '<div><slot /></div>' },
          'a-row': { template: '<div><slot /></div>' },
          'a-col': { template: '<div><slot /></div>' },
          'a-statistic': { template: '<div class="stat">{{ $attrs.title }}: {{ $attrs.value }}</div>' },
          'a-select': true,
          'a-select-option': true,
          'a-alert': true,
          'a-form': true,
          'a-form-item': true,
          'a-input': true,
          'a-input-password': true,
          'a-input-number': true,
          'a-space': true,
          'a-tag': true,
          'a-tooltip': true,
          'a-popconfirm': true,
        },
      },
    })

    const stats = wrapper.findAll('.stat')
    const statsText = stats.map(s => s.text())
    expect(statsText).toContain('运行中: 1')
    expect(statsText).toContain('异常: 1')
    expect(statsText).toContain('已停用: 1')
  })

  it('should call fetchModels on mount', async () => {
    const mockFetch = vi.fn()
    const mockComposable = usePredictionModelConfig as ReturnType<typeof vi.fn>
    mockComposable.mockReturnValue({
      models: { value: [] },
      modelsTotal: { value: 0 },
      modelStatuses: { value: [] },
      isLoading: { value: false },
      isTestingConnection: { value: false },
      fetchModels: mockFetch,
      createModel: vi.fn(),
      updateModel: vi.fn(),
      deleteModel: vi.fn(),
      testConnection: vi.fn(),
      fetchStatuses: vi.fn(),
    })

    mount(PredictionModelConfigView, {
      global: {
        stubs: {
          'a-button': true,
          'a-table': true,
          'a-modal': true,
          'a-card': true,
          'a-row': true,
          'a-col': true,
          'a-statistic': true,
          'a-select': true,
          'a-select-option': true,
          'a-alert': true,
          'a-form': true,
          'a-form-item': true,
          'a-input': true,
          'a-input-password': true,
          'a-input-number': true,
          'a-space': true,
          'a-tag': true,
          'a-tooltip': true,
          'a-popconfirm': true,
        },
      },
    })

    await flushPromises()
    expect(mockFetch).toHaveBeenCalled()
  })
})
