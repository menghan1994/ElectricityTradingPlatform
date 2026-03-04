import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

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

import ImportUploader from '../../../../src/components/data/ImportUploader.vue'
import { message } from 'ant-design-vue'
import type { StationRead } from '../../../../src/types/station'

const mockStations: StationRead[] = [
  {
    id: 'station-1',
    name: '测试电站A',
    province: 'guangdong',
    capacity_mw: 100,
    station_type: 'solar',
    grid_connection_point: '220kV',
    has_storage: false,
    is_active: true,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  } as StationRead,
  {
    id: 'station-2',
    name: '测试电站B',
    province: 'shandong',
    capacity_mw: 200,
    station_type: 'wind',
    grid_connection_point: '110kV',
    has_storage: true,
    is_active: true,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  } as StationRead,
]

describe('ImportUploader', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  function mountUploader(props: Partial<{
    stations: StationRead[]
    isUploading: boolean
    importType: string
    emsFormat: string
  }> = {}) {
    return mount(ImportUploader, {
      props: {
        stations: props.stations ?? mockStations,
        isUploading: props.isUploading ?? false,
        importType: (props.importType ?? 'trading_data') as any,
        emsFormat: (props.emsFormat ?? 'standard') as any,
      },
      global: {
        stubs: {
          'a-upload-dragger': {
            template: '<div class="upload-dragger"><slot /></div>',
            emits: ['remove'],
          },
          'a-select': {
            template: '<select class="station-select" @change="$emit(\'update:value\', $event.target.value)"><slot /></select>',
            props: ['value'],
            emits: ['update:value'],
          },
          'a-select-option': {
            template: '<option :value="value"><slot /></option>',
            props: ['value', 'label'],
          },
          'a-button': {
            template: '<button :disabled="disabled" :class="{ loading }" @click="$emit(\'click\')"><slot /></button>',
            props: ['type', 'loading', 'disabled'],
            emits: ['click'],
          },
          InboxOutlined: { template: '<span class="inbox-icon" />' },
          EmsFormatSelector: {
            template: '<div class="ems-selector" />',
            props: ['modelValue'],
            emits: ['update:modelValue'],
          },
        },
      },
    })
  }

  it('should render upload area', () => {
    const wrapper = mountUploader()
    expect(wrapper.find('.upload-dragger').exists()).toBe(true)
  })

  it('should render station options', () => {
    const wrapper = mountUploader()
    const options = wrapper.findAll('option')
    expect(options).toHaveLength(2)
  })

  it('should show upload hint text', () => {
    const wrapper = mountUploader()
    expect(wrapper.text()).toContain('支持 .xlsx / .csv 格式')
  })

  it('should disable button when no file or station selected', () => {
    const wrapper = mountUploader()
    const button = wrapper.find('button')
    expect(button.attributes('disabled')).toBeDefined()
  })

  it('should show loading state when uploading', () => {
    const wrapper = mountUploader({ isUploading: true })
    const button = wrapper.find('button')
    expect(button.classes()).toContain('loading')
  })

  it('should render all station names', () => {
    const wrapper = mountUploader()
    expect(wrapper.text()).toContain('测试电站A')
    expect(wrapper.text()).toContain('测试电站B')
  })

  it('should reject invalid file type via handleBeforeUpload', () => {
    const wrapper = mountUploader()
    const vm = wrapper.vm as any

    const pdfFile = new File(['content'], 'test.pdf', { type: 'application/pdf' })
    vm.handleBeforeUpload(pdfFile)

    expect(message.error).toHaveBeenCalledWith('仅支持 .xlsx 和 .csv 格式文件')
    expect(vm.selectedFile).toBeNull()
  })

  it('should accept valid csv file via handleBeforeUpload', () => {
    const wrapper = mountUploader()
    const vm = wrapper.vm as any

    const csvFile = new File(['a,b,c'], 'data.csv', { type: 'text/csv' })
    vm.handleBeforeUpload(csvFile)

    expect(message.error).not.toHaveBeenCalled()
    expect(vm.selectedFile).toBe(csvFile)
  })

  it('should accept valid xlsx file', () => {
    const wrapper = mountUploader()
    const vm = wrapper.vm as any

    const xlsxFile = new File(['binary'], 'data.xlsx')
    vm.handleBeforeUpload(xlsxFile)

    expect(vm.selectedFile).toBe(xlsxFile)
  })

  it('should reject file exceeding 100MB', () => {
    const wrapper = mountUploader()
    const vm = wrapper.vm as any

    const bigFile = new File(['x'], 'big.csv', { type: 'text/csv' })
    Object.defineProperty(bigFile, 'size', { value: 101 * 1024 * 1024 })
    vm.handleBeforeUpload(bigFile)

    expect(message.error).toHaveBeenCalledWith('文件大小不能超过 100MB')
    expect(vm.selectedFile).toBeNull()
  })

  it('should emit upload event when file and station selected', async () => {
    const wrapper = mountUploader()
    const vm = wrapper.vm as any

    const csvFile = new File(['a,b'], 'data.csv', { type: 'text/csv' })
    vm.handleBeforeUpload(csvFile)
    vm.selectedStationId = 'station-1'

    vm.handleStartImport()

    expect(wrapper.emitted('upload')).toBeTruthy()
    expect(wrapper.emitted('upload')![0]).toEqual([csvFile, 'station-1'])
  })

  it('should warn when starting import without station', () => {
    const wrapper = mountUploader()
    const vm = wrapper.vm as any

    const csvFile = new File(['a,b'], 'data.csv', { type: 'text/csv' })
    vm.handleBeforeUpload(csvFile)

    vm.handleStartImport()

    expect(message.warning).toHaveBeenCalledWith('请先选择目标电站')
    expect(wrapper.emitted('upload')).toBeFalsy()
  })

  it('should warn when starting import without file', () => {
    const wrapper = mountUploader()
    const vm = wrapper.vm as any

    vm.selectedStationId = 'station-1'
    vm.handleStartImport()

    expect(message.warning).toHaveBeenCalledWith('请先选择要导入的文件')
    expect(wrapper.emitted('upload')).toBeFalsy()
  })

  it('should show trading_data hint text', () => {
    const wrapper = mountUploader({ importType: 'trading_data' })
    expect(wrapper.text()).toContain('出清价格')
  })

  it('should show station_output hint text', () => {
    const wrapper = mountUploader({ importType: 'station_output' })
    expect(wrapper.text()).toContain('实际出力')
  })

  it('should show storage_operation hint text', () => {
    const wrapper = mountUploader({ importType: 'storage_operation' })
    expect(wrapper.text()).toContain('SOC')
    expect(wrapper.text()).toContain('充放电功率')
  })

  it('should show EmsFormatSelector for storage_operation', () => {
    const wrapper = mountUploader({ importType: 'storage_operation' })
    expect(wrapper.find('.ems-selector').exists()).toBe(true)
  })

  it('should hide EmsFormatSelector for trading_data', () => {
    const wrapper = mountUploader({ importType: 'trading_data' })
    expect(wrapper.find('.ems-selector').exists()).toBe(false)
  })

  it('should hide EmsFormatSelector for station_output', () => {
    const wrapper = mountUploader({ importType: 'station_output' })
    expect(wrapper.find('.ems-selector').exists()).toBe(false)
  })
})
