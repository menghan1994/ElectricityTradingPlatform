import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('../../../src/api/errors', () => ({
  getErrorMessage: vi.fn((err: unknown, fallback: string) => {
    if (err && typeof err === 'object' && 'response' in err) {
      const axiosErr = err as { response?: { data?: { message?: string } } }
      return axiosErr.response?.data?.message || fallback
    }
    return err instanceof Error ? err.message : fallback
  }),
  getErrorCode: vi.fn((err: unknown) => {
    if (err && typeof err === 'object' && 'response' in err) {
      const axiosErr = err as { response?: { data?: { code?: string } } }
      return axiosErr.response?.data?.code || null
    }
    return null
  }),
}))

vi.mock('../../../src/api/station', () => ({
  stationApi: {
    listStations: vi.fn().mockResolvedValue({
      items: [
        { id: '1', name: '广东风电一号', province: '广东', capacity_mw: '100.00', station_type: 'wind', has_storage: true, is_active: true, created_at: '2026-01-01', updated_at: '2026-01-01' },
        { id: '2', name: '山东光伏一号', province: '山东', capacity_mw: '50.00', station_type: 'solar', has_storage: false, is_active: false, created_at: '2026-01-01', updated_at: '2026-01-01' },
      ],
      total: 2,
      page: 1,
      page_size: 20,
    }),
    createStation: vi.fn(),
    updateStation: vi.fn(),
    deleteStation: vi.fn(),
    listAllActiveStations: vi.fn(),
    getUserStationBindings: vi.fn(),
    updateUserStationBindings: vi.fn(),
    getUserDeviceBindings: vi.fn(),
    updateUserDeviceBindings: vi.fn(),
    listAllActiveDevices: vi.fn().mockResolvedValue([]),
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
      warning: vi.fn(),
    },
  }
})

import StationManagementView from '../../../src/views/admin/StationManagementView.vue'
import { useStationStore } from '../../../src/stores/station'
import { useAuthStore } from '../../../src/stores/auth'
import { stationApi } from '../../../src/api/station'
import { message } from 'ant-design-vue'

// Stubs that render slot content and forward events for interaction testing
const defaultStubs = {
  'a-table': {
    template: `<div class="a-table-stub">
      <slot />
      <template v-for="record in dataSource" :key="record.id">
        <slot name="bodyCell" :column="{ key: 'station_type', dataIndex: 'station_type' }" :record="record" />
        <slot name="bodyCell" :column="{ key: 'has_storage', dataIndex: 'has_storage' }" :record="record" />
        <slot name="bodyCell" :column="{ key: 'is_active', dataIndex: 'is_active' }" :record="record" />
        <slot name="bodyCell" :column="{ key: 'actions', dataIndex: 'actions' }" :record="record" />
      </template>
    </div>`,
    props: ['columns', 'dataSource', 'loading', 'pagination', 'rowKey'],
    emits: ['change'],
  },
  'a-button': {
    template: '<button :class="{ danger }" @click="$emit(\'click\')"><slot /></button>',
    props: ['type', 'size', 'danger', 'loading'],
  },
  'a-input-search': {
    template: '<input class="search-input" @keyup.enter="$emit(\'search\', modelValue)" />',
    props: ['modelValue', 'placeholder'],
    emits: ['search', 'update:modelValue', 'pressEnter'],
  },
  'a-modal': {
    template: '<div v-if="open" class="a-modal-stub"><slot /><slot name="footer" /></div>',
    props: ['open', 'title', 'confirmLoading'],
    emits: ['ok', 'update:open'],
  },
  'a-form': { template: '<form><slot /></form>', props: ['model', 'rules', 'labelCol', 'wrapperCol'] },
  'a-form-item': { template: '<div class="form-item"><slot /></div>', props: ['label', 'name'] },
  'a-input': { template: '<input />', props: ['value'] },
  'a-input-number': { template: '<input type="number" />', props: ['value', 'min', 'step'] },
  'a-select': { template: '<select><slot /></select>', props: ['value', 'placeholder', 'options'] },
  'a-select-option': { template: '<option><slot /></option>', props: ['value'] },
  'a-switch': { template: '<input type="checkbox" />', props: ['checked'] },
  'a-tag': { template: '<span class="a-tag"><slot /></span>', props: ['color'] },
  'a-alert': { template: '<div class="a-alert"><slot /></div>', props: ['type', 'message', 'showIcon', 'closable'] },
  'a-space': { template: '<span class="a-space"><slot /></span>' },
  'a-popconfirm': {
    template: '<span class="a-popconfirm" @click="$emit(\'confirm\')"><slot /></span>',
    props: ['title', 'okText', 'cancelText'],
    emits: ['confirm'],
  },
  'a-divider': { template: '<hr />' },
}

function setAuthUser(role: string) {
  const authStore = useAuthStore()
  authStore.$patch({
    accessToken: 'fake-token',
    user: { id: '1', username: 'testuser', display_name: 'Test', role, is_active: true, is_locked: false, created_at: '2026-01-01', updated_at: '2026-01-01' } as any,
  })
}

function mountView() {
  return mount(StationManagementView, {
    global: { stubs: defaultStubs },
  })
}

describe('StationManagementView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    // 默认以 admin 角色挂载
    setAuthUser('admin')
  })

  describe('rendering', () => {
    it('should render the page title', () => {
      const wrapper = mountView()
      expect(wrapper.text()).toContain('电站管理')
    })

    it('should render create station button for admin', () => {
      const wrapper = mountView()
      const buttons = wrapper.findAll('button')
      const createBtn = buttons.find((b) => b.text().includes('创建电站'))
      expect(createBtn).toBeTruthy()
    })

    it('should not render create station button for non-admin', () => {
      setAuthUser('trader')
      const wrapper = mountView()
      const buttons = wrapper.findAll('button')
      const createBtn = buttons.find((b) => b.text().includes('创建电站'))
      expect(createBtn).toBeUndefined()
    })

    it('should render table with station data after fetch', async () => {
      const wrapper = mountView()
      await flushPromises()

      // Table should receive data via dataSource prop
      const table = wrapper.find('.a-table-stub')
      expect(table.exists()).toBe(true)

      // Station names rendered in table body slots
      expect(wrapper.text()).toContain('风电')
      expect(wrapper.text()).toContain('光伏')
    })

    it('should render status tags with correct labels', async () => {
      const wrapper = mountView()
      await flushPromises()

      expect(wrapper.text()).toContain('启用')
      expect(wrapper.text()).toContain('已停用')
    })

    it('should render has_storage tags', async () => {
      const wrapper = mountView()
      await flushPromises()

      expect(wrapper.text()).toContain('是')
      expect(wrapper.text()).toContain('否')
    })
  })

  describe('data fetching on mount', () => {
    it('should call listStations API on mount', () => {
      mountView()
      expect(stationApi.listStations).toHaveBeenCalled()
    })

    it('should populate store with fetched stations', async () => {
      mountView()
      await flushPromises()

      const store = useStationStore()
      expect(store.stationList).toHaveLength(2)
      expect(store.total).toBe(2)
    })
  })

  describe('create station dialog', () => {
    it('should open create dialog when create button is clicked', async () => {
      const wrapper = mountView()
      await flushPromises()

      // Find and click the create button
      const buttons = wrapper.findAll('button')
      const createBtn = buttons.find((b) => b.text().includes('创建电站'))
      expect(createBtn).toBeTruthy()
      await createBtn!.trigger('click')

      // Dialog should appear
      const modal = wrapper.find('.a-modal-stub')
      expect(modal.exists()).toBe(true)
    })
  })

  describe('edit station dialog', () => {
    it('should render edit buttons in table action column', async () => {
      const wrapper = mountView()
      await flushPromises()

      const buttons = wrapper.findAll('button')
      const editBtns = buttons.filter((b) => b.text() === '编辑')
      expect(editBtns.length).toBeGreaterThan(0)
    })

    it('should open edit dialog when edit button is clicked', async () => {
      const wrapper = mountView()
      await flushPromises()

      const buttons = wrapper.findAll('button')
      const editBtn = buttons.find((b) => b.text() === '编辑')
      expect(editBtn).toBeTruthy()
      await editBtn!.trigger('click')

      const modal = wrapper.find('.a-modal-stub')
      expect(modal.exists()).toBe(true)
    })
  })

  describe('toggle active (stop/enable)', () => {
    it('should render toggle buttons for each station', async () => {
      const wrapper = mountView()
      await flushPromises()

      const buttons = wrapper.findAll('button')
      // Active station shows '停用', inactive shows '启用'
      const toggleBtns = buttons.filter((b) => b.text() === '停用' || b.text() === '启用')
      expect(toggleBtns.length).toBeGreaterThan(0)
    })

    it('should call updateStation when deactivating an active station via popconfirm', async () => {
      vi.mocked(stationApi.updateStation).mockResolvedValue(
        { id: '1', name: '广东风电一号', province: '广东', capacity_mw: '100.00', station_type: 'wind', has_storage: true, is_active: false, created_at: '2026-01-01', updated_at: '2026-01-01' },
      )

      const wrapper = mountView()
      await flushPromises()

      // Click the popconfirm wrapping the '停用' button — triggers confirm
      const popconfirms = wrapper.findAll('.a-popconfirm')
      expect(popconfirms.length).toBeGreaterThan(0)
      await popconfirms[0].trigger('click')
      await flushPromises()

      expect(stationApi.updateStation).toHaveBeenCalled()
    })

    it('should show warning when deactivation fails with STATION_HAS_BINDINGS', async () => {
      const error = { response: { data: { code: 'STATION_HAS_BINDINGS', message: '电站有活跃绑定关系' } } }
      vi.mocked(stationApi.updateStation).mockRejectedValue(error)

      const wrapper = mountView()
      await flushPromises()

      const popconfirms = wrapper.findAll('.a-popconfirm')
      await popconfirms[0].trigger('click')
      await flushPromises()

      expect(vi.mocked(message.warning)).toHaveBeenCalledWith('该电站有交易员绑定关系，请先解除绑定后再停用')
    })
  })

  describe('error handling', () => {
    it('should show error message when fetch fails', async () => {
      vi.mocked(stationApi.listStations).mockRejectedValueOnce(new Error('Network error'))

      mountView()
      await flushPromises()

      expect(vi.mocked(message.error)).toHaveBeenCalledWith('加载电站列表失败')
    })
  })

  describe('storage_operator device view', () => {
    it('should show device section for storage_operator', async () => {
      vi.mocked(stationApi.listAllActiveDevices).mockResolvedValue([
        { id: 'd1', station_id: 's1', station_name: '测试电站', name: '储能设备A', capacity_mwh: '50.00', max_charge_rate_mw: '10.00', max_discharge_rate_mw: '10.00', soc_upper_limit: '0.9', soc_lower_limit: '0.1', is_active: true, created_at: '2026-01-01', updated_at: '2026-01-01' },
      ])

      setAuthUser('storage_operator')
      const wrapper = mountView()
      await flushPromises()

      expect(wrapper.text()).toContain('储能设备')
      expect(stationApi.listAllActiveDevices).toHaveBeenCalled()
    })

    it('should show both stations and devices for storage_operator', async () => {
      vi.mocked(stationApi.listAllActiveDevices).mockResolvedValue([])
      setAuthUser('storage_operator')
      const wrapper = mountView()
      await flushPromises()

      expect(wrapper.text()).toContain('电站管理')
      expect(wrapper.text()).toContain('储能设备')
      expect(stationApi.listStations).toHaveBeenCalled()
    })

    it('should not show admin actions for storage_operator', async () => {
      vi.mocked(stationApi.listAllActiveDevices).mockResolvedValue([])
      setAuthUser('storage_operator')
      const wrapper = mountView()
      await flushPromises()

      // 不应显示创建电站按钮
      const buttons = wrapper.findAll('button')
      const createBtn = buttons.find((b) => b.text().includes('创建电站'))
      expect(createBtn).toBeUndefined()

      // 电站表格的 columns 不应包含 'actions' 列
      const table = wrapper.find('.a-table-stub')
      const columnsProp = table.attributes('columns') || ''
      expect(columnsProp).not.toContain('actions')
    })

    it('should show both stations and devices for admin', async () => {
      vi.mocked(stationApi.listAllActiveDevices).mockResolvedValue([])
      const wrapper = mountView()
      await flushPromises()

      expect(wrapper.text()).toContain('电站管理')
      expect(wrapper.text()).toContain('储能设备')
    })

    it('should show device section for trader', async () => {
      vi.mocked(stationApi.listAllActiveDevices).mockResolvedValue([
        { id: 'd1', station_id: 's1', station_name: '测试电站', name: '储能设备A', capacity_mwh: '50.00', max_charge_rate_mw: '10.00', max_discharge_rate_mw: '10.00', soc_upper_limit: '0.9', soc_lower_limit: '0.1', is_active: true, created_at: '2026-01-01', updated_at: '2026-01-01' },
      ])

      setAuthUser('trader')
      const wrapper = mountView()
      await flushPromises()

      expect(wrapper.text()).toContain('电站管理')
      expect(wrapper.text()).toContain('储能设备')
    })
  })

  describe('executive_readonly view', () => {
    it('should show stations and devices for executive_readonly', async () => {
      vi.mocked(stationApi.listAllActiveDevices).mockResolvedValue([
        { id: 'd1', station_id: 's1', station_name: '测试电站', name: '储能设备A', capacity_mwh: '50.00', max_charge_rate_mw: '10.00', max_discharge_rate_mw: '10.00', soc_upper_limit: '0.9', soc_lower_limit: '0.1', is_active: true, created_at: '2026-01-01', updated_at: '2026-01-01' },
      ])

      setAuthUser('executive_readonly')
      const wrapper = mountView()
      await flushPromises()

      expect(wrapper.text()).toContain('电站管理')
      expect(wrapper.text()).toContain('储能设备')
      expect(stationApi.listStations).toHaveBeenCalled()
      expect(stationApi.listAllActiveDevices).toHaveBeenCalled()
    })

    it('should not show admin actions for executive_readonly', async () => {
      vi.mocked(stationApi.listAllActiveDevices).mockResolvedValue([])
      setAuthUser('executive_readonly')
      const wrapper = mountView()
      await flushPromises()

      // 不应显示创建电站按钮
      const buttons = wrapper.findAll('button')
      const createBtn = buttons.find((b) => b.text().includes('创建电站'))
      expect(createBtn).toBeUndefined()

      // 电站表格的 columns 不应包含 'actions' 列（非 admin 无操作列）
      const table = wrapper.find('.a-table-stub')
      const columnsProp = table.attributes('columns') || ''
      expect(columnsProp).not.toContain('actions')
    })
  })
})
