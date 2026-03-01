<script setup lang="ts">
import { ref, watch } from 'vue'
import { message } from 'ant-design-vue'
import { stationApi } from '@/api/station'
import { batteryTypeLabels } from '@/constants/storageTemplates'
import { provinceLabels } from '@/constants/provinces'
import { stationTypeLabels } from '@/types/station'
import type { StationRead, StorageDeviceRead } from '@/types/station'

const props = defineProps<{
  open: boolean
  station: StationRead | null
}>()

const emit = defineEmits<{
  (e: 'close'): void
}>()

const devices = ref<StorageDeviceRead[]>([])
const isLoadingDevices = ref(false)

// M4+M10: 仅在 open=true 时 fetch 设备，immediate 确保首次打开也触发
watch(
  [() => props.open, () => props.station],
  async ([isOpen, station]) => {
    if (isOpen && station && station.has_storage) {
      isLoadingDevices.value = true
      try {
        devices.value = await stationApi.getStationDevices(station.id)
      } catch {
        devices.value = []
        message.error('加载储能设备失败')
      } finally {
        isLoadingDevices.value = false
      }
    } else if (!isOpen) {
      devices.value = []
    }
  },
  { immediate: true },
)
</script>

<template>
  <a-drawer :open="open" title="电站详情" width="600" @close="emit('close')">
    <template v-if="station">
      <a-descriptions bordered :column="1" size="small" style="margin-bottom: 24px;">
        <a-descriptions-item label="电站名称">{{ station.name }}</a-descriptions-item>
        <a-descriptions-item label="省份">{{ provinceLabels[station.province] || station.province }}</a-descriptions-item>
        <a-descriptions-item label="装机容量">{{ station.capacity_mw }} MW</a-descriptions-item>
        <a-descriptions-item label="并网点">{{ station.grid_connection_point || '未填写' }}</a-descriptions-item>
        <a-descriptions-item label="电站类型">{{ stationTypeLabels[station.station_type] }}</a-descriptions-item>
        <a-descriptions-item label="配有储能">{{ station.has_storage ? '是' : '否' }}</a-descriptions-item>
        <a-descriptions-item label="状态">
          <a-tag :color="station.is_active ? 'green' : 'red'">
            {{ station.is_active ? '活跃' : '已停用' }}
          </a-tag>
        </a-descriptions-item>
      </a-descriptions>

      <template v-if="station.has_storage">
        <h4 style="margin-bottom: 12px;">储能设备</h4>
        <a-spin :spinning="isLoadingDevices">
          <a-empty v-if="!isLoadingDevices && devices.length === 0" description="暂无储能设备" />
          <a-descriptions v-for="device in devices" :key="device.id" :title="device.name" bordered :column="2" size="small" style="margin-bottom: 16px;">
            <a-descriptions-item label="储能容量">{{ device.capacity_mwh }} MWh</a-descriptions-item>
            <a-descriptions-item label="电池类型">{{ device.battery_type ? batteryTypeLabels[device.battery_type] : '未知' }}</a-descriptions-item>
            <a-descriptions-item label="最大充电功率">{{ device.max_charge_rate_mw }} MW</a-descriptions-item>
            <a-descriptions-item label="最大放电功率">{{ device.max_discharge_rate_mw }} MW</a-descriptions-item>
            <a-descriptions-item label="SOC 下限">{{ device.soc_lower_limit }}</a-descriptions-item>
            <a-descriptions-item label="SOC 上限">{{ device.soc_upper_limit }}</a-descriptions-item>
          </a-descriptions>
        </a-spin>
      </template>
    </template>
  </a-drawer>
</template>
