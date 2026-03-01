import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { defineComponent, h, nextTick } from 'vue'
import StationDetailDrawer from '../../../../src/components/data/StationDetailDrawer.vue'

vi.mock('../../../../src/api/station', () => ({
  stationApi: {
    getStationDevices: vi.fn(),
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

import { stationApi } from '../../../../src/api/station'
import { message } from 'ant-design-vue'

const stubs = {
  'a-drawer': defineComponent({
    props: ['open', 'title', 'width'],
    emits: ['close'],
    setup(_, { slots }) {
      return () => h('div', { class: 'drawer-stub' }, slots.default?.())
    },
  }),
  'a-descriptions': defineComponent({
    props: ['bordered', 'column', 'size', 'title'],
    setup(_, { slots }) {
      return () => h('div', { class: 'descriptions-stub' }, slots.default?.())
    },
  }),
  'a-descriptions-item': defineComponent({
    props: ['label'],
    setup(props, { slots }) {
      return () => h('span', { class: 'desc-item', 'data-label': props.label }, slots.default?.())
    },
  }),
  'a-tag': defineComponent({
    props: ['color'],
    setup(_, { slots }) {
      return () => h('span', { class: 'tag-stub' }, slots.default?.())
    },
  }),
  'a-spin': defineComponent({
    props: ['spinning'],
    setup(_, { slots }) {
      return () => h('div', { class: 'spin-stub' }, slots.default?.())
    },
  }),
  'a-empty': defineComponent({
    props: ['description'],
    setup(props) {
      return () => h('div', { class: 'empty-stub' }, props.description)
    },
  }),
}

function mountDrawer(props = {}) {
  return mount(StationDetailDrawer, {
    props: {
      open: false,
      station: null,
      ...props,
    },
    global: {
      stubs,
    },
  })
}

const mockStation = {
  id: 'station-1',
  name: '测试电站',
  province: 'gansu',
  capacity_mw: '50.00',
  grid_connection_point: '330kV 某变电站',
  station_type: 'solar',
  has_storage: true,
  is_active: true,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

const mockDevices = [
  {
    id: 'device-1',
    station_id: 'station-1',
    name: '1号储能',
    capacity_mwh: '100.00',
    max_charge_rate_mw: '50.00',
    max_discharge_rate_mw: '50.00',
    soc_upper_limit: '0.9',
    soc_lower_limit: '0.1',
    battery_type: 'lfp',
    is_active: true,
  },
]

describe('StationDetailDrawer', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should render station details when open with station', async () => {
    vi.mocked(stationApi.getStationDevices).mockResolvedValue(mockDevices as any)

    const wrapper = mountDrawer({ open: true, station: mockStation })
    await flushPromises()

    expect(wrapper.text()).toContain('测试电站')
    expect(wrapper.text()).toContain('50.00')
    wrapper.unmount()
  })

  it('should fetch devices when open with storage station', async () => {
    vi.mocked(stationApi.getStationDevices).mockResolvedValue(mockDevices as any)

    const wrapper = mountDrawer({ open: false, station: mockStation })
    await wrapper.setProps({ open: true })
    await flushPromises()

    expect(stationApi.getStationDevices).toHaveBeenCalledWith('station-1')
    wrapper.unmount()
  })

  it('should not fetch devices for non-storage station', async () => {
    const noStorageStation = { ...mockStation, has_storage: false }
    const wrapper = mountDrawer({ open: true, station: noStorageStation })
    await flushPromises()

    expect(stationApi.getStationDevices).not.toHaveBeenCalled()
    wrapper.unmount()
  })

  it('M5: should show error message on device load failure', async () => {
    vi.mocked(stationApi.getStationDevices).mockRejectedValue(new Error('fail'))

    const wrapper = mountDrawer({ open: false, station: mockStation })
    await wrapper.setProps({ open: true })
    await flushPromises()

    expect(vi.mocked(message.error)).toHaveBeenCalledWith('加载储能设备失败')
    wrapper.unmount()
  })

  it('should clear devices when drawer is closed', async () => {
    vi.mocked(stationApi.getStationDevices).mockResolvedValue(mockDevices as any)

    const wrapper = mountDrawer({ open: true, station: mockStation })
    await flushPromises()

    await wrapper.setProps({ open: false })
    await nextTick()

    // After closing, devices should be cleared
    expect(wrapper.text()).not.toContain('1号储能')
    wrapper.unmount()
  })

  it('should emit close event', async () => {
    const wrapper = mountDrawer({ open: true, station: mockStation })

    const drawer = wrapper.findComponent({ name: 'a-drawer' })
    if (drawer.exists()) {
      drawer.vm.$emit('close')
      expect(wrapper.emitted('close')).toBeTruthy()
    }
    wrapper.unmount()
  })
})
