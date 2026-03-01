import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { mount } from '@vue/test-utils'
import { defineComponent } from 'vue'

vi.mock('../../../src/api/wizard', () => ({
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

import { useStationWizard } from '../../../src/composables/useStationWizard'
import { wizardApi } from '../../../src/api/wizard'
import { message } from 'ant-design-vue'
import { storageTemplates } from '../../../src/constants/storageTemplates'

function withSetup<T>(composable: () => T): { result: T; unmount: () => void } {
  let result!: T
  const TestComponent = defineComponent({
    setup() {
      result = composable()
      return {}
    },
    template: '<div></div>',
  })

  const pinia = createPinia()
  const wrapper = mount(TestComponent, {
    global: { plugins: [pinia] },
  })

  return { result, unmount: () => wrapper.unmount() }
}

describe('useStationWizard', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  describe('initial state', () => {
    it('should start at step 0', () => {
      const { result, unmount } = withSetup(() => useStationWizard())
      expect(result.currentStep.value).toBe(0)
      unmount()
    })

    it('should have totalSteps=2 when has_storage is false', () => {
      const { result, unmount } = withSetup(() => useStationWizard())
      expect(result.stationForm.has_storage).toBe(false)
      expect(result.totalSteps.value).toBe(2)
      unmount()
    })

    it('should have one default device', () => {
      const { result, unmount } = withSetup(() => useStationWizard())
      expect(result.devices.value).toHaveLength(1)
      expect(result.devices.value[0].soc_upper_limit).toBe(0.9)
      expect(result.devices.value[0].soc_lower_limit).toBe(0.1)
      unmount()
    })
  })

  describe('totalSteps computed', () => {
    it('should return 3 when has_storage is true', () => {
      const { result, unmount } = withSetup(() => useStationWizard())
      result.stationForm.has_storage = true
      expect(result.totalSteps.value).toBe(3)
      unmount()
    })
  })

  describe('step navigation', () => {
    it('should go to next step', () => {
      const { result, unmount } = withSetup(() => useStationWizard())
      result.nextStep()
      expect(result.currentStep.value).toBe(1)
      unmount()
    })

    it('should not exceed max step', () => {
      const { result, unmount } = withSetup(() => useStationWizard())
      // totalSteps=2 (no storage), max index=1
      result.nextStep()
      result.nextStep()
      expect(result.currentStep.value).toBe(1)
      unmount()
    })

    it('should go to previous step', () => {
      const { result, unmount } = withSetup(() => useStationWizard())
      result.nextStep()
      result.prevStep()
      expect(result.currentStep.value).toBe(0)
      unmount()
    })

    it('should not go below step 0', () => {
      const { result, unmount } = withSetup(() => useStationWizard())
      result.prevStep()
      expect(result.currentStep.value).toBe(0)
      unmount()
    })
  })

  describe('device management', () => {
    it('should add a device', () => {
      const { result, unmount } = withSetup(() => useStationWizard())
      result.addDevice()
      expect(result.devices.value).toHaveLength(2)
      unmount()
    })

    it('should remove a device when more than one', () => {
      const { result, unmount } = withSetup(() => useStationWizard())
      result.addDevice()
      expect(result.devices.value).toHaveLength(2)
      result.removeDevice(0)
      expect(result.devices.value).toHaveLength(1)
      unmount()
    })

    it('should not remove the last device', () => {
      const { result, unmount } = withSetup(() => useStationWizard())
      result.removeDevice(0)
      expect(result.devices.value).toHaveLength(1)
      unmount()
    })
  })

  describe('validateSocRange', () => {
    it('should return null for valid range', () => {
      const { result, unmount } = withSetup(() => useStationWizard())
      const err = result.validateSocRange(result.devices.value[0])
      expect(err).toBeNull()
      unmount()
    })

    it('should return error when lower >= upper', () => {
      const { result, unmount } = withSetup(() => useStationWizard())
      result.devices.value[0].soc_lower_limit = 0.9
      result.devices.value[0].soc_upper_limit = 0.1
      const err = result.validateSocRange(result.devices.value[0])
      expect(err).toContain('下限必须小于上限')
      unmount()
    })

    it('should return error for out-of-range lower', () => {
      const { result, unmount } = withSetup(() => useStationWizard())
      result.devices.value[0].soc_lower_limit = -0.1
      const err = result.validateSocRange(result.devices.value[0])
      expect(err).toContain('下限')
      unmount()
    })

    it('should return error for out-of-range upper', () => {
      const { result, unmount } = withSetup(() => useStationWizard())
      result.devices.value[0].soc_upper_limit = 1.5
      const err = result.validateSocRange(result.devices.value[0])
      expect(err).toContain('上限')
      unmount()
    })

    // M9: SOC 边界值测试
    it('should accept lower=0 and upper=1 as valid boundary', () => {
      const { result, unmount } = withSetup(() => useStationWizard())
      result.devices.value[0].soc_lower_limit = 0
      result.devices.value[0].soc_upper_limit = 1
      const err = result.validateSocRange(result.devices.value[0])
      expect(err).toBeNull()
      unmount()
    })

    it('should reject lower equal to upper', () => {
      const { result, unmount } = withSetup(() => useStationWizard())
      result.devices.value[0].soc_lower_limit = 0.5
      result.devices.value[0].soc_upper_limit = 0.5
      const err = result.validateSocRange(result.devices.value[0])
      expect(err).toContain('下限必须小于上限')
      unmount()
    })
  })

  describe('applyTemplate', () => {
    it('should apply template values to a device', () => {
      const { result, unmount } = withSetup(() => useStationWizard())
      const template = storageTemplates[0] // LFP-2h
      result.applyTemplate(template, 0)

      expect(result.devices.value[0].battery_type).toBe('lfp')
      expect(result.devices.value[0].soc_lower_limit).toBe(0.1)
      expect(result.devices.value[0].soc_upper_limit).toBe(0.9)
      unmount()
    })

    it('should apply NMC template with different SOC values', () => {
      const { result, unmount } = withSetup(() => useStationWizard())
      const template = storageTemplates[2] // NMC-1h
      result.applyTemplate(template, 0)

      expect(result.devices.value[0].battery_type).toBe('nmc')
      expect(result.devices.value[0].soc_lower_limit).toBe(0.15)
      expect(result.devices.value[0].soc_upper_limit).toBe(0.85)
      unmount()
    })

    it('H9: should calculate charge/discharge rates from c_rate when capacity is set', () => {
      const { result, unmount } = withSetup(() => useStationWizard())
      result.devices.value[0].capacity_mwh = 100
      const template = storageTemplates[0] // LFP-2h, c_rate=0.5
      result.applyTemplate(template, 0)

      expect(result.devices.value[0].max_charge_rate_mw).toBe(50) // 100 * 0.5
      expect(result.devices.value[0].max_discharge_rate_mw).toBe(50)
      unmount()
    })

    it('H9: should not calculate rates when capacity is null', () => {
      const { result, unmount } = withSetup(() => useStationWizard())
      // capacity_mwh is null by default
      const template = storageTemplates[0]
      result.applyTemplate(template, 0)

      expect(result.devices.value[0].max_charge_rate_mw).toBeNull()
      expect(result.devices.value[0].max_discharge_rate_mw).toBeNull()
      unmount()
    })
  })

  describe('validateAllDevices', () => {
    it('H10: should return null for valid device', () => {
      const { result, unmount } = withSetup(() => useStationWizard())
      result.devices.value[0].name = '1号储能'
      result.devices.value[0].capacity_mwh = 100
      result.devices.value[0].max_charge_rate_mw = 50
      result.devices.value[0].max_discharge_rate_mw = 50
      result.devices.value[0].soc_lower_limit = 0.1
      result.devices.value[0].soc_upper_limit = 0.9

      const err = result.validateAllDevices()
      expect(err).toBeNull()
      unmount()
    })

    it('H10: should return error for empty device name', () => {
      const { result, unmount } = withSetup(() => useStationWizard())
      result.devices.value[0].name = ''

      const err = result.validateAllDevices()
      expect(err).toContain('名称不能为空')
      unmount()
    })

    it('H10: should return error for missing capacity', () => {
      const { result, unmount } = withSetup(() => useStationWizard())
      result.devices.value[0].name = '1号储能'
      result.devices.value[0].capacity_mwh = null

      const err = result.validateAllDevices()
      expect(err).toContain('储能容量')
      unmount()
    })

    it('H10: should return error for missing charge rate', () => {
      const { result, unmount } = withSetup(() => useStationWizard())
      result.devices.value[0].name = '1号储能'
      result.devices.value[0].capacity_mwh = 100
      result.devices.value[0].max_charge_rate_mw = null

      const err = result.validateAllDevices()
      expect(err).toContain('最大充电功率')
      unmount()
    })

    it('H10: should return error for missing discharge rate', () => {
      const { result, unmount } = withSetup(() => useStationWizard())
      result.devices.value[0].name = '1号储能'
      result.devices.value[0].capacity_mwh = 100
      result.devices.value[0].max_charge_rate_mw = 50
      result.devices.value[0].max_discharge_rate_mw = null

      const err = result.validateAllDevices()
      expect(err).toContain('最大放电功率')
      unmount()
    })

    it('H10: should return SOC error for invalid SOC range', () => {
      const { result, unmount } = withSetup(() => useStationWizard())
      result.devices.value[0].name = '1号储能'
      result.devices.value[0].capacity_mwh = 100
      result.devices.value[0].max_charge_rate_mw = 50
      result.devices.value[0].max_discharge_rate_mw = 50
      result.devices.value[0].soc_lower_limit = 0.9
      result.devices.value[0].soc_upper_limit = 0.1

      const err = result.validateAllDevices()
      expect(err).toContain('SOC')
      unmount()
    })
  })

  describe('resetWizard', () => {
    it('should reset all state to defaults', () => {
      const { result, unmount } = withSetup(() => useStationWizard())
      // Modify state
      result.stationForm.name = '测试电站'
      result.stationForm.has_storage = true
      result.currentStep.value = 2
      result.addDevice()

      result.resetWizard()

      expect(result.currentStep.value).toBe(0)
      expect(result.stationForm.name).toBe('')
      expect(result.stationForm.has_storage).toBe(false)
      expect(result.devices.value).toHaveLength(1)
      expect(result.selectedTemplateIndices.value).toEqual({})
      unmount()
    })
  })

  describe('submitWizard', () => {
    it('should call API and return result on success', async () => {
      const mockResponse = {
        station: { id: '1', name: '测试电站' },
        devices: [],
      }
      vi.mocked(wizardApi.createStationWithDevices).mockResolvedValue(mockResponse as any)

      const { result, unmount } = withSetup(() => useStationWizard())
      result.stationForm.name = '测试电站'
      result.stationForm.province = 'gansu'
      result.stationForm.capacity_mw = 50
      result.stationForm.station_type = 'solar'

      const response = await result.submitWizard()

      expect(wizardApi.createStationWithDevices).toHaveBeenCalledOnce()
      expect(response).toEqual(mockResponse)
      expect(vi.mocked(message.success)).toHaveBeenCalledWith('电站创建成功')
      expect(result.isSubmitting.value).toBe(false)
      unmount()
    })

    it('should include storage devices when has_storage is true', async () => {
      vi.mocked(wizardApi.createStationWithDevices).mockResolvedValue({
        station: { id: '1', name: '测试电站' },
        devices: [{ id: 'd1', name: '1号储能' }],
      } as any)

      const { result, unmount } = withSetup(() => useStationWizard())
      result.stationForm.name = '测试电站'
      result.stationForm.province = 'gansu'
      result.stationForm.capacity_mw = 50
      result.stationForm.station_type = 'solar'
      result.stationForm.has_storage = true
      result.devices.value[0].name = '1号储能'
      result.devices.value[0].capacity_mwh = 100
      result.devices.value[0].max_charge_rate_mw = 50
      result.devices.value[0].max_discharge_rate_mw = 50

      await result.submitWizard()

      const callArgs = vi.mocked(wizardApi.createStationWithDevices).mock.calls[0][0]
      expect(callArgs.storage_devices).toHaveLength(1)
      expect(callArgs.storage_devices[0].name).toBe('1号储能')
      unmount()
    })

    it('should show error message on API failure', async () => {
      // H4: 使用 getErrorMessage 处理错误 — 非 AxiosError 走 Error.message 或 fallback
      vi.mocked(wizardApi.createStationWithDevices).mockRejectedValue(
        new Error('电站名称已存在'),
      )

      const { result, unmount } = withSetup(() => useStationWizard())
      result.stationForm.name = '已存在电站'
      result.stationForm.province = 'gansu'
      result.stationForm.capacity_mw = 50

      const response = await result.submitWizard()

      expect(response).toBeNull()
      // getErrorMessage: Error.message 被使用
      expect(vi.mocked(message.error)).toHaveBeenCalledWith('电站名称已存在')
      expect(result.isSubmitting.value).toBe(false)
      unmount()
    })

    it('should show fallback error message when no detail', async () => {
      vi.mocked(wizardApi.createStationWithDevices).mockRejectedValue('unknown')

      const { result, unmount } = withSetup(() => useStationWizard())
      // C3: 必须填写所有必填字段才能到达 API 调用
      result.stationForm.name = '测试电站'
      result.stationForm.province = 'gansu'
      result.stationForm.capacity_mw = 50
      const response = await result.submitWizard()

      expect(response).toBeNull()
      expect(vi.mocked(message.error)).toHaveBeenCalledWith('创建失败，请重试')
      unmount()
    })
  })
})
