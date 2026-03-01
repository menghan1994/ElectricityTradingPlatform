import type { BatteryType } from '@/types/station'

export interface StorageTemplate {
  label: string
  battery_type: BatteryType
  soc_lower_limit: number
  soc_upper_limit: number
  c_rate: number
  description: string
}

export const storageTemplates: StorageTemplate[] = [
  {
    label: '磷酸铁锂-2小时储能',
    battery_type: 'lfp',
    soc_lower_limit: 0.1,
    soc_upper_limit: 0.9,
    c_rate: 0.5,
    description: 'LFP 电池，充放电倍率 0.5C，适合 2 小时调峰场景',
  },
  {
    label: '磷酸铁锂-4小时储能',
    battery_type: 'lfp',
    soc_lower_limit: 0.1,
    soc_upper_limit: 0.9,
    c_rate: 0.25,
    description: 'LFP 电池，充放电倍率 0.25C，适合 4 小时长时储能场景',
  },
  {
    label: '三元锂-1小时储能',
    battery_type: 'nmc',
    soc_lower_limit: 0.15,
    soc_upper_limit: 0.85,
    c_rate: 1,
    description: 'NMC 电池，充放电倍率 1C，适合 1 小时快速调频场景',
  },
  {
    label: '钛酸锂-快充储能',
    battery_type: 'lto',
    soc_lower_limit: 0.05,
    soc_upper_limit: 0.95,
    c_rate: 2,
    description: 'LTO 电池，充放电倍率 2C，超长循环寿命，适合高频充放场景',
  },
]

export const batteryTypeLabels: Record<BatteryType, string> = {
  lfp: '磷酸铁锂 (LFP)',
  nmc: '三元锂 (NMC)',
  lto: '钛酸锂 (LTO)',
  other: '其他',
}
