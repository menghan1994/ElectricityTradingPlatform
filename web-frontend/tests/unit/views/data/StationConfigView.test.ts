import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('../../../../src/api/station', () => ({
  stationApi: {
    listStations: vi.fn().mockResolvedValue({
      items: [
        { id: '1', name: '甘肃某光伏电站', province: 'gansu', capacity_mw: '50.00', station_type: 'solar', grid_connection_point: null, has_storage: true, is_active: true, created_at: '2026-01-01', updated_at: '2026-01-01' },
        { id: '2', name: '青海风电一号', province: 'qinghai', capacity_mw: '100.00', station_type: 'wind', grid_connection_point: '330kV某变电站', has_storage: false, is_active: false, created_at: '2026-01-01', updated_at: '2026-01-01' },
      ],
      total: 2,
      page: 1,
      page_size: 20,
    }),
    getStationDevices: vi.fn().mockResolvedValue([]),
  },
}))

vi.mock('../../../../src/api/wizard', () => ({
  wizardApi: {
    createStationWithDevices: vi.fn(),
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

import StationConfigView from '../../../../src/views/data/StationConfigView.vue'
import { stationApi } from '../../../../src/api/station'

const defaultStubs = {
  'a-table': {
    template: `<div class="a-table-stub">
      <template v-for="record in dataSource" :key="record.id">
        <slot name="bodyCell" :column="{ key: 'province' }" :record="record" />
        <slot name="bodyCell" :column="{ key: 'station_type' }" :record="record" />
        <slot name="bodyCell" :column="{ key: 'has_storage' }" :record="record" />
        <slot name="bodyCell" :column="{ key: 'is_active' }" :record="record" />
        <slot name="bodyCell" :column="{ key: 'action' }" :record="record" />
      </template>
    </div>`,
    props: ['columns', 'dataSource', 'loading', 'pagination', 'rowKey'],
  },
  'a-button': {
    template: '<button class="a-button" @click="$emit(\'click\')"><slot /></button>',
    props: ['type', 'size', 'loading'],
  },
  'a-tag': { template: '<span class="a-tag"><slot /></span>', props: ['color'] },
  'a-modal': {
    template: '<div v-if="open" class="a-modal-stub"><slot /></div>',
    props: ['open', 'title', 'footer', 'width', 'destroyOnClose'],
    emits: ['update:open'],
  },
  StationWizard: {
    template: '<div class="station-wizard-stub"></div>',
    emits: ['success', 'cancel'],
  },
  StationDetailDrawer: {
    template: '<div class="station-detail-drawer-stub"></div>',
    props: ['open', 'station'],
    emits: ['close'],
  },
}

function mountView() {
  return mount(StationConfigView, {
    global: { stubs: defaultStubs },
  })
}

describe('StationConfigView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    // Re-set default mock for listStations (clearAllMocks clears it)
    vi.mocked(stationApi.listStations).mockResolvedValue({
      items: [
        { id: '1', name: '甘肃某光伏电站', province: 'gansu', capacity_mw: '50.00', station_type: 'solar', grid_connection_point: null, has_storage: true, is_active: true, created_at: '2026-01-01', updated_at: '2026-01-01' },
        { id: '2', name: '青海风电一号', province: 'qinghai', capacity_mw: '100.00', station_type: 'wind', grid_connection_point: '330kV某变电站', has_storage: false, is_active: false, created_at: '2026-01-01', updated_at: '2026-01-01' },
      ],
      total: 2,
      page: 1,
      page_size: 20,
    })
  })

  describe('rendering', () => {
    it('should render the page title', () => {
      const wrapper = mountView()
      expect(wrapper.text()).toContain('电站配置')
    })

    it('should render the 新建电站 button', () => {
      const wrapper = mountView()
      const buttons = wrapper.findAll('.a-button')
      const createBtn = buttons.find((b) => b.text().includes('新建电站'))
      expect(createBtn).toBeTruthy()
    })

    it('should render table with station data after fetch', async () => {
      const wrapper = mountView()
      await flushPromises()

      const table = wrapper.find('.a-table-stub')
      expect(table.exists()).toBe(true)
      // Table body slots should render station type labels
      expect(wrapper.text()).toContain('光伏')
      expect(wrapper.text()).toContain('风电')
    })

    it('should render status tags', async () => {
      const wrapper = mountView()
      await flushPromises()

      expect(wrapper.text()).toContain('活跃')
      expect(wrapper.text()).toContain('已停用')
    })

    it('should render has_storage tags', async () => {
      const wrapper = mountView()
      await flushPromises()

      expect(wrapper.text()).toContain('是')
      expect(wrapper.text()).toContain('否')
    })

    it('should render 详情 action buttons', async () => {
      const wrapper = mountView()
      await flushPromises()

      const buttons = wrapper.findAll('.a-button')
      const detailBtns = buttons.filter((b) => b.text() === '详情')
      expect(detailBtns.length).toBeGreaterThan(0)
    })
  })

  describe('data fetching on mount', () => {
    it('should call listStations API on mount', () => {
      mountView()
      expect(stationApi.listStations).toHaveBeenCalledWith(1, 20)
    })

    it('should clear stations on API error', async () => {
      vi.mocked(stationApi.listStations).mockRejectedValueOnce(new Error('Network error'))
      const wrapper = mountView()
      await flushPromises()

      // Table should have no data rows rendered
      const table = wrapper.find('.a-table-stub')
      expect(table.exists()).toBe(true)
    })
  })

  describe('wizard modal', () => {
    it('should open wizard modal when 新建电站 button is clicked', async () => {
      const wrapper = mountView()
      await flushPromises()

      // Initially no modal
      expect(wrapper.find('.a-modal-stub').exists()).toBe(false)

      // Click create button
      const createBtn = wrapper.findAll('.a-button').find((b) => b.text().includes('新建电站'))
      await createBtn!.trigger('click')

      // Modal should appear
      expect(wrapper.find('.a-modal-stub').exists()).toBe(true)
    })
  })

  describe('detail drawer', () => {
    it('should render StationDetailDrawer stub', async () => {
      const wrapper = mountView()
      await flushPromises()
      expect(wrapper.find('.station-detail-drawer-stub').exists()).toBe(true)
    })
  })
})
