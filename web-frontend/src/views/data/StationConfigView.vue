<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { stationApi } from '@/api/station'
import { provinceLabels } from '@/constants/provinces'
import { stationTypeLabels } from '@/types/station'
import type { StationRead } from '@/types/station'
import StationWizard from '@/components/data/StationWizard.vue'
import StationDetailDrawer from '@/components/data/StationDetailDrawer.vue'

const stations = ref<StationRead[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const isLoading = ref(false)
const showWizard = ref(false)
const showDetail = ref(false)
const selectedStation = ref<StationRead | null>(null)

const columns = [
  { title: '电站名称', dataIndex: 'name', key: 'name' },
  { title: '省份', dataIndex: 'province', key: 'province' },
  { title: '装机容量 (MW)', dataIndex: 'capacity_mw', key: 'capacity_mw' },
  { title: '电站类型', dataIndex: 'station_type', key: 'station_type' },
  { title: '配有储能', dataIndex: 'has_storage', key: 'has_storage' },
  { title: '状态', dataIndex: 'is_active', key: 'is_active' },
  { title: '操作', key: 'action', width: 100 },
]

async function loadStations() {
  isLoading.value = true
  try {
    const response = await stationApi.listStations(currentPage.value, pageSize.value)
    stations.value = response.items
    total.value = response.total
  } catch {
    stations.value = []
    total.value = 0
    // H12: 加载失败时提示用户
    message.error('电站列表加载失败，请稍后重试')
  } finally {
    isLoading.value = false
  }
}

function handlePageChange(page: number) {
  currentPage.value = page
  loadStations()
}

function handleWizardSuccess() {
  showWizard.value = false
  loadStations()
}

function viewDetail(station: StationRead) {
  selectedStation.value = station
  showDetail.value = true
}

onMounted(loadStations)
</script>

<template>
  <div>
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
      <h2 style="margin: 0;">电站配置</h2>
      <a-button type="primary" @click="showWizard = true">新建电站</a-button>
    </div>

    <a-modal v-model:open="showWizard" title="新建电站向导" :footer="null" width="900" :destroy-on-close="true">
      <StationWizard @success="handleWizardSuccess" @cancel="showWizard = false" />
    </a-modal>

    <a-table :columns="columns" :data-source="stations" :loading="isLoading" :pagination="{
      current: currentPage,
      pageSize: pageSize,
      total: total,
      showSizeChanger: false,
      onChange: handlePageChange,
    }" row-key="id">
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'province'">
          {{ provinceLabels[(record as StationRead).province] || (record as StationRead).province }}
        </template>
        <template v-else-if="column.key === 'station_type'">
          {{ stationTypeLabels[(record as StationRead).station_type] }}
        </template>
        <template v-else-if="column.key === 'has_storage'">
          <a-tag :color="(record as StationRead).has_storage ? 'blue' : 'default'">
            {{ (record as StationRead).has_storage ? '是' : '否' }}
          </a-tag>
        </template>
        <template v-else-if="column.key === 'is_active'">
          <a-tag :color="(record as StationRead).is_active ? 'green' : 'red'">
            {{ (record as StationRead).is_active ? '活跃' : '已停用' }}
          </a-tag>
        </template>
        <template v-else-if="column.key === 'action'">
          <a-button type="link" size="small" @click="viewDetail(record as StationRead)">详情</a-button>
        </template>
      </template>
    </a-table>

    <StationDetailDrawer :open="showDetail" :station="selectedStation" @close="showDetail = false" />
  </div>
</template>
