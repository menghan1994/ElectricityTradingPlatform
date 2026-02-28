import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('../../../src/api/station', () => ({
  stationApi: {
    listStations: vi.fn(),
    listAllActiveStations: vi.fn().mockResolvedValue([
      { id: '1', name: '广东风电一号', province: '广东', capacity_mw: '100.00', station_type: 'wind', has_storage: true, is_active: true, created_at: '2026-01-01', updated_at: '2026-01-01' },
    ]),
    listAllActiveDevices: vi.fn().mockResolvedValue([
      { id: 'd1', station_id: '1', station_name: null, name: '储能设备A', capacity_mwh: '50.00', max_charge_rate_mw: '10.00', max_discharge_rate_mw: '10.00', soc_upper_limit: '0.9', soc_lower_limit: '0.1', is_active: true, created_at: '2026-01-01', updated_at: '2026-01-01' },
    ]),
    getUserStationBindings: vi.fn().mockResolvedValue({ station_ids: ['1'], stations: [] }),
    updateUserStationBindings: vi.fn().mockResolvedValue({ station_ids: ['1'], stations: [] }),
    getUserDeviceBindings: vi.fn().mockResolvedValue({ device_ids: [], devices: [] }),
    updateUserDeviceBindings: vi.fn().mockResolvedValue({ device_ids: [], devices: [] }),
    createStation: vi.fn(),
    updateStation: vi.fn(),
    deleteStation: vi.fn(),
    getStation: vi.fn(),
  },
}))

vi.mock('../../../src/api/auth', () => ({
  authApi: {
    getMe: vi.fn(),
  },
}))

vi.mock('../../../src/router', () => ({
  default: {
    push: vi.fn(),
  },
}))

vi.mock('ant-design-vue', async () => {
  const actual = await vi.importActual('ant-design-vue')
  return {
    ...actual,
    message: {
      success: vi.fn(),
      error: vi.fn(),
    },
  }
})

import BindingConfigDrawer from '../../../src/components/admin/BindingConfigDrawer.vue'
import { stationApi } from '../../../src/api/station'

const defaultStubs = {
  'a-drawer': { template: '<div>{{ title }}<slot /><slot name="footer" /></div>', props: ['open', 'title'] },
  'a-transfer': true,
  'a-spin': { template: '<div><slot /></div>' },
  'a-result': { template: '<div>{{ title }}{{ subTitle }}</div>', props: ['status', 'title', 'subTitle'] },
  'a-button': { template: '<button @click="$emit(\'click\')"><slot /></button>' },
}

describe('BindingConfigDrawer', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('should render drawer with user info', () => {
    const wrapper = mount(BindingConfigDrawer, {
      props: {
        open: true,
        user: {
          id: '1', username: 'trader1', display_name: '交易员1', phone: null, email: null,
          role: 'trader' as const, is_active: true, is_locked: false, last_login_at: null,
          created_at: '2026-01-01', updated_at: '2026-01-01',
        },
      },
      global: { stubs: defaultStubs },
    })

    expect(wrapper.exists()).toBe(true)
    expect(wrapper.text()).toContain('保存绑定')
    expect(wrapper.text()).toContain('交易员1')
  })

  it('should show info message for non-bindable roles', () => {
    const wrapper = mount(BindingConfigDrawer, {
      props: {
        open: true,
        user: {
          id: '1', username: 'admin', display_name: '管理员', phone: null, email: null,
          role: 'admin' as const, is_active: true, is_locked: false, last_login_at: null,
          created_at: '2026-01-01', updated_at: '2026-01-01',
        },
      },
      global: { stubs: defaultStubs },
    })

    // Should not show the save button for admin role
    expect(wrapper.text()).not.toContain('保存绑定')
    expect(wrapper.text()).toContain('该角色无需绑定资源')
  })

  it('should show save button for trader role', () => {
    const wrapper = mount(BindingConfigDrawer, {
      props: {
        open: true,
        user: {
          id: '1', username: 'trader1', display_name: '交易员1', phone: null, email: null,
          role: 'trader' as const, is_active: true, is_locked: false, last_login_at: null,
          created_at: '2026-01-01', updated_at: '2026-01-01',
        },
      },
      global: { stubs: defaultStubs },
    })

    expect(wrapper.text()).toContain('保存绑定')
  })

  it('should load station bindings when opened for trader', async () => {
    const user = {
      id: 'user-1', username: 'trader1', display_name: '交易员1', phone: null, email: null,
      role: 'trader' as const, is_active: true, is_locked: false, last_login_at: null,
      created_at: '2026-01-01', updated_at: '2026-01-01',
    }

    // Mount with open=false, then change to true to trigger the watcher
    const wrapper = mount(BindingConfigDrawer, {
      props: { open: false, user },
      global: { stubs: defaultStubs },
    })

    await wrapper.setProps({ open: true })

    // Wait for async operations
    await flushPromises()

    expect(stationApi.listAllActiveStations).toHaveBeenCalled()
    expect(stationApi.getUserStationBindings).toHaveBeenCalledWith('user-1')
  })

  it('should load device bindings when opened for storage_operator', async () => {
    const user = {
      id: 'user-2', username: 'operator1', display_name: '运维员1', phone: null, email: null,
      role: 'storage_operator' as const, is_active: true, is_locked: false, last_login_at: null,
      created_at: '2026-01-01', updated_at: '2026-01-01',
    }

    const wrapper = mount(BindingConfigDrawer, {
      props: { open: false, user },
      global: { stubs: defaultStubs },
    })

    await wrapper.setProps({ open: true })
    await flushPromises()

    expect(stationApi.listAllActiveDevices).toHaveBeenCalled()
    expect(stationApi.getUserDeviceBindings).toHaveBeenCalledWith('user-2')
  })

  it('should call updateUserStationBindings on save for trader', async () => {
    const user = {
      id: 'user-1', username: 'trader1', display_name: '交易员1', phone: null, email: null,
      role: 'trader' as const, is_active: true, is_locked: false, last_login_at: null,
      created_at: '2026-01-01', updated_at: '2026-01-01',
    }

    const wrapper = mount(BindingConfigDrawer, {
      props: { open: false, user },
      global: { stubs: defaultStubs },
    })

    await wrapper.setProps({ open: true })
    await flushPromises()

    // Click save button
    const buttons = wrapper.findAll('button')
    const saveButton = buttons.find(b => b.text() === '保存绑定')
    expect(saveButton).toBeTruthy()
    await saveButton!.trigger('click')
    await flushPromises()

    expect(stationApi.updateUserStationBindings).toHaveBeenCalledWith('user-1', expect.any(Array))
  })

  it('should emit update:open on close', async () => {
    const wrapper = mount(BindingConfigDrawer, {
      props: {
        open: true,
        user: {
          id: '1', username: 'trader1', display_name: '交易员1', phone: null, email: null,
          role: 'trader' as const, is_active: true, is_locked: false, last_login_at: null,
          created_at: '2026-01-01', updated_at: '2026-01-01',
        },
      },
      global: { stubs: defaultStubs },
    })

    // Find and click cancel button
    const buttons = wrapper.findAll('button')
    const cancelButton = buttons.find(b => b.text() === '取消')
    expect(cancelButton).toBeTruthy()
    await cancelButton!.trigger('click')
    expect(wrapper.emitted('update:open')).toBeTruthy()
    expect(wrapper.emitted('update:open')![0]).toEqual([false])
  })
})
