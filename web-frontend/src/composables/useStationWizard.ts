import { ref, computed, reactive, watch } from 'vue'
import { message } from 'ant-design-vue'
import { wizardApi } from '@/api/wizard'
import { getErrorMessage } from '@/api/errors'
import { storageTemplates, type StorageTemplate } from '@/constants/storageTemplates'
import type { StationType, BatteryType } from '@/types/station'
import type { WizardStorageDeviceInput, StationWizardResponse } from '@/types/wizard'

export interface StationFormData {
  name: string
  province: string
  capacity_mw: number | null
  station_type: StationType
  grid_connection_point: string
  has_storage: boolean
}

export interface DeviceFormData {
  _uid: number
  name: string
  capacity_mwh: number | null
  max_charge_rate_mw: number | null
  max_discharge_rate_mw: number | null
  soc_upper_limit: number
  soc_lower_limit: number
  battery_type: BatteryType | null
}

function createDefaultStationForm(): StationFormData {
  return {
    name: '',
    province: '',
    capacity_mw: null,
    station_type: 'solar',
    grid_connection_point: '',
    has_storage: false,
  }
}

// M5: 模块级 UID 计数器 — 跨 useStationWizard 实例单调递增，确保设备 _uid 全局唯一
let _nextUid = 0

function createDefaultDevice(): DeviceFormData {
  return {
    _uid: _nextUid++,
    name: '',
    capacity_mwh: null,
    max_charge_rate_mw: null,
    max_discharge_rate_mw: null,
    soc_upper_limit: 0.9,
    soc_lower_limit: 0.1,
    battery_type: null,
  }
}

export function useStationWizard() {
  const currentStep = ref(0)
  const isSubmitting = ref(false)

  const stationForm = reactive<StationFormData>(createDefaultStationForm())

  const devices = ref<DeviceFormData[]>([createDefaultDevice()])
  // H8: 每个设备独立的模板选择状态
  const selectedTemplateIndices = ref<Record<number, number | null>>({})

  const totalSteps = computed(() => stationForm.has_storage ? 3 : 2)

  // H11: has_storage 切换时重置 currentStep 防止步骤索引错乱
  watch(() => stationForm.has_storage, () => {
    if (currentStep.value >= totalSteps.value) {
      currentStep.value = 0
    }
  })

  function validateSocRange(device: DeviceFormData): string | null {
    if (device.soc_lower_limit < 0 || device.soc_lower_limit > 1) {
      return 'SOC 下限必须在 0-1 之间'
    }
    if (device.soc_upper_limit < 0 || device.soc_upper_limit > 1) {
      return 'SOC 上限必须在 0-1 之间'
    }
    if (device.soc_lower_limit >= device.soc_upper_limit) {
      return 'SOC 下限必须小于上限'
    }
    return null
  }

  // C6: 验证所有设备的完整性和 SOC 范围
  function validateAllDevices(): string | null {
    for (let i = 0; i < devices.value.length; i++) {
      const d = devices.value[i]
      if (!d.name.trim()) {
        return `储能设备 ${i + 1} 的名称不能为空`
      }
      if (!d.capacity_mwh || d.capacity_mwh <= 0) {
        return `储能设备 ${i + 1} 的储能容量必须大于 0`
      }
      if (!d.max_charge_rate_mw || d.max_charge_rate_mw <= 0) {
        return `储能设备 ${i + 1} 的最大充电功率必须大于 0`
      }
      if (!d.max_discharge_rate_mw || d.max_discharge_rate_mw <= 0) {
        return `储能设备 ${i + 1} 的最大放电功率必须大于 0`
      }
      const socError = validateSocRange(d)
      if (socError) {
        return `储能设备 ${i + 1}: ${socError}`
      }
    }
    return null
  }

  function applyTemplate(template: StorageTemplate, deviceIndex: number) {
    const device = devices.value[deviceIndex]
    if (!device) return
    device.battery_type = template.battery_type
    device.soc_lower_limit = template.soc_lower_limit
    device.soc_upper_limit = template.soc_upper_limit
    // H9: 利用 c_rate 计算充放电功率（当容量已填写时）
    if (device.capacity_mwh && device.capacity_mwh > 0) {
      const rate = Math.round(device.capacity_mwh * template.c_rate * 100) / 100
      device.max_charge_rate_mw = rate
      device.max_discharge_rate_mw = rate
    }
  }

  function addDevice() {
    // M6: 设备数量上限（与后端 max_length=50 一致）
    if (devices.value.length >= 50) {
      message.warning('单个电站最多 50 个储能设备')
      return
    }
    devices.value.push(createDefaultDevice())
  }

  function removeDevice(index: number) {
    if (devices.value.length > 1) {
      const removed = devices.value[index]
      devices.value.splice(index, 1)
      // 清理已删除设备的模板选择状态
      if (removed) {
        delete selectedTemplateIndices.value[removed._uid]
      }
    }
  }

  function nextStep() {
    if (currentStep.value < totalSteps.value - 1) {
      currentStep.value++
    }
  }

  function prevStep() {
    if (currentStep.value > 0) {
      currentStep.value--
    }
  }

  // M6: 使用 Object.assign 模式重置表单
  function resetWizard() {
    currentStep.value = 0
    Object.assign(stationForm, createDefaultStationForm())
    devices.value = [createDefaultDevice()]
    selectedTemplateIndices.value = {}
  }

  async function submitWizard(): Promise<StationWizardResponse | null> {
    // C3+C7: 提交前校验所有必填字段
    if (!stationForm.name.trim()) {
      message.error('请填写电站名称')
      return null
    }
    if (!stationForm.province) {
      message.error('请选择省份')
      return null
    }
    if (!stationForm.station_type) {
      message.error('请选择电站类型')
      return null
    }
    if (!stationForm.capacity_mw || stationForm.capacity_mw <= 0) {
      message.error('请填写有效的装机容量')
      return null
    }

    // C6: 提交前验证所有设备
    if (stationForm.has_storage) {
      const deviceError = validateAllDevices()
      if (deviceError) {
        message.error(deviceError)
        return null
      }
    }

    isSubmitting.value = true
    try {
      const storageDevices: WizardStorageDeviceInput[] = stationForm.has_storage
        ? devices.value.map((d) => ({
            name: d.name,
            capacity_mwh: d.capacity_mwh ?? 0,
            max_charge_rate_mw: d.max_charge_rate_mw ?? 0,
            max_discharge_rate_mw: d.max_discharge_rate_mw ?? 0,
            soc_upper_limit: d.soc_upper_limit,
            soc_lower_limit: d.soc_lower_limit,
            battery_type: d.battery_type,
          }))
        : []

      const result = await wizardApi.createStationWithDevices({
        name: stationForm.name,
        province: stationForm.province,
        capacity_mw: stationForm.capacity_mw,
        station_type: stationForm.station_type,
        grid_connection_point: stationForm.grid_connection_point || null,
        has_storage: stationForm.has_storage,
        storage_devices: storageDevices,
      })

      message.success('电站创建成功')
      return result
    } catch (error: unknown) {
      // H4: 使用类型安全的错误处理工具函数替代 unsafe `as` 断言
      message.error(getErrorMessage(error, '创建失败，请重试'))
      return null
    } finally {
      isSubmitting.value = false
    }
  }

  return {
    currentStep,
    isSubmitting,
    stationForm,
    devices,
    selectedTemplateIndices,
    totalSteps,
    storageTemplates,
    validateSocRange,
    validateAllDevices,
    applyTemplate,
    addDevice,
    removeDevice,
    nextStep,
    prevStep,
    resetWizard,
    submitWizard,
  }
}
