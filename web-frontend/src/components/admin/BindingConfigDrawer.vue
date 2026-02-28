<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { message } from 'ant-design-vue'
import { getErrorMessage } from '@/api/errors'
import type { UserRead } from '@/api/auth'
import { useStationStore } from '@/stores/station'
import type { StationRead, StorageDeviceRead } from '@/types/station'
import { stationTypeLabels } from '@/types/station'
import { roleLabels } from '@/constants/roles'

const props = defineProps<{
  open: boolean
  user: UserRead | null
}>()

const emit = defineEmits<{
  (e: 'update:open', value: boolean): void
}>()

const stationStore = useStationStore()

const isLoading = ref(false)
const isSaving = ref(false)

// Transfer data
const allStations = ref<StationRead[]>([])
const allDevices = ref<StorageDeviceRead[]>([])
const selectedStationIds = ref<string[]>([])
const selectedDeviceIds = ref<string[]>([])

const isBindableRole = computed(() => {
  return props.user?.role === 'trader' || props.user?.role === 'storage_operator'
})

const isTrader = computed(() => props.user?.role === 'trader')
const isOperator = computed(() => props.user?.role === 'storage_operator')

// Transfer data source for stations
const stationTransferData = computed(() =>
  allStations.value.map((s) => ({
    key: s.id,
    title: s.name,
    description: `${s.province} | ${stationTypeLabels[s.station_type] || s.station_type} | ${s.capacity_mw}MW`,
  })),
)

// Transfer data source for devices
const deviceTransferData = computed(() =>
  allDevices.value.map((d) => ({
    key: d.id,
    title: d.name,
    description: `${d.station_name ? d.station_name + ' | ' : ''}${d.capacity_mwh}MWh`,
  })),
)

// MEDIUM: 切换用户时重置旧状态，避免残留数据
function resetState() {
  allStations.value = []
  allDevices.value = []
  selectedStationIds.value = []
  selectedDeviceIds.value = []
}

watch(
  [() => props.open, () => props.user],
  async ([newOpen]) => {
    if (newOpen && props.user) {
      resetState()
      await loadBindingData()
    }
  },
)

async function loadBindingData() {
  if (!props.user) return
  isLoading.value = true
  try {
    if (isTrader.value) {
      const [stations, bindings] = await Promise.all([
        stationStore.fetchAllActiveStations(),
        stationStore.fetchUserStationBindings(props.user.id),
      ])
      allStations.value = stations
      selectedStationIds.value = [...bindings.station_ids]
    } else if (isOperator.value) {
      const [devices, bindings] = await Promise.all([
        stationStore.fetchAllActiveDevices(),
        stationStore.fetchUserDeviceBindings(props.user.id),
      ])
      allDevices.value = devices
      selectedDeviceIds.value = [...bindings.device_ids]
    }
  } catch (err: unknown) {
    message.error(getErrorMessage(err, '加载绑定信息失败'))
  } finally {
    isLoading.value = false
  }
}

function handleStationTransferChange(targetKeys: (string | number)[]) {
  selectedStationIds.value = targetKeys.map(String)
}

function handleDeviceTransferChange(targetKeys: (string | number)[]) {
  selectedDeviceIds.value = targetKeys.map(String)
}

async function handleSave() {
  if (!props.user) return
  isSaving.value = true
  try {
    if (isTrader.value) {
      await stationStore.updateUserStationBindings(props.user.id, selectedStationIds.value)
      message.success('电站绑定已更新')
    } else if (isOperator.value) {
      await stationStore.updateUserDeviceBindings(props.user.id, selectedDeviceIds.value)
      message.success('设备绑定已更新')
    }
    emit('update:open', false)
  } catch (err: unknown) {
    message.error(getErrorMessage(err, '保存绑定失败'))
  } finally {
    isSaving.value = false
  }
}

function handleClose() {
  emit('update:open', false)
}
</script>

<template>
  <a-drawer
    :open="open"
    :title="`资源绑定配置 — ${user?.display_name || user?.username}（${roleLabels[user?.role || ''] || user?.role}）`"
    :width="640"
    @close="handleClose"
  >
    <a-spin :spinning="isLoading">
      <template v-if="!isBindableRole">
        <a-result
          status="info"
          title="该角色无需绑定资源"
          sub-title="仅交易员(trader)需要绑定电站，储能运维员(storage_operator)需要绑定设备。"
        />
      </template>

      <template v-else-if="isTrader">
        <p style="margin-bottom: 16px; color: #666;">
          将左侧可选电站移至右侧，即完成绑定。该交易员登录后仅能看到已绑定电站的数据。
        </p>
        <a-transfer
          :data-source="stationTransferData"
          :target-keys="selectedStationIds"
          :titles="['可选电站', '已绑定电站']"
          :render="(item: { title: string }) => item.title"
          :list-style="{ width: '260px', height: '400px' }"
          show-search
          :filter-option="(inputValue: string, option: { title: string; description: string }) =>
            option.title.includes(inputValue) || option.description.includes(inputValue)"
          @change="handleStationTransferChange"
        />
      </template>

      <template v-else-if="isOperator">
        <p style="margin-bottom: 16px; color: #666;">
          将左侧可选储能设备移至右侧，即完成绑定。该运维员仅能操作已绑定设备的调度指令。
        </p>
        <a-transfer
          :data-source="deviceTransferData"
          :target-keys="selectedDeviceIds"
          :titles="['可选设备', '已绑定设备']"
          :render="(item: { title: string }) => item.title"
          :list-style="{ width: '260px', height: '400px' }"
          show-search
          :filter-option="(inputValue: string, option: { title: string; description: string }) =>
            option.title.includes(inputValue) || option.description.includes(inputValue)"
          @change="handleDeviceTransferChange"
        />
      </template>
    </a-spin>

    <template #footer>
      <div style="display: flex; justify-content: flex-end; gap: 8px;">
        <a-button @click="handleClose">取消</a-button>
        <a-button
          v-if="isBindableRole"
          type="primary"
          :loading="isSaving"
          @click="handleSave"
        >
          保存绑定
        </a-button>
      </div>
    </template>
  </a-drawer>
</template>
