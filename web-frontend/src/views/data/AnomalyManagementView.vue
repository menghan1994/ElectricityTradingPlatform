<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useAnomalyManagement } from '@/composables/useAnomalyManagement'
import AnomalyCorrectModal from '@/components/data/AnomalyCorrectModal.vue'
import AnomalyFilterBar from '@/components/data/AnomalyFilterBar.vue'
import type { ImportAnomaly } from '@/types/dataImport'

const route = useRoute()
const {
  anomalies,
  total,
  isLoading,
  selectedIds,
  summary,
  loadAnomalies,
  loadSummary,
  correctAnomaly,
  confirmNormal,
  deleteAnomaly,
  bulkDelete,
  bulkConfirmNormal,
  clearSelection,
} = useAnomalyManagement()

const currentPage = ref(1)
const pageSize = ref(20)
const filters = ref<{
  anomaly_type?: string
  status?: string
  import_job_id?: string
}>({ status: 'pending' })

const correctModalVisible = ref(false)
const currentAnomaly = ref<ImportAnomaly | null>(null)

const anomalyTypeLabels: Record<string, string> = {
  missing: '缺失',
  format_error: '格式错误',
  out_of_range: '超范围',
  duplicate: '重复',
}

const anomalyTypeColors: Record<string, string> = {
  missing: 'orange',
  format_error: 'red',
  out_of_range: 'purple',
  duplicate: 'blue',
}

const statusLabels: Record<string, string> = {
  pending: '待处理',
  confirmed_normal: '已确认正常',
  corrected: '已修正',
  deleted: '已删除',
}

const statusColors: Record<string, string> = {
  pending: 'default',
  confirmed_normal: 'green',
  corrected: 'green',
  deleted: '',
}

const columns = [
  { title: '行号', dataIndex: 'row_number', key: 'row_number', width: 80 },
  { title: '异常类型', dataIndex: 'anomaly_type', key: 'anomaly_type', width: 120 },
  { title: '字段', dataIndex: 'field_name', key: 'field_name', width: 120 },
  { title: '原始值', dataIndex: 'raw_value', key: 'raw_value', width: 150 },
  { title: '描述', dataIndex: 'description', key: 'description' },
  { title: '状态', dataIndex: 'status', key: 'status', width: 120 },
  { title: '操作', key: 'actions', width: 200, fixed: 'right' as const },
]

const selectedRowKeys = computed(() => Array.from(selectedIds.value))

const rowSelection = computed(() => ({
  selectedRowKeys: selectedRowKeys.value,
  onChange: (keys: string[]) => {
    selectedIds.value = new Set(keys)
  },
  getCheckboxProps: (record: ImportAnomaly) => ({
    disabled: record.status !== 'pending',
  }),
}))

function handleSearch(searchFilters: {
  anomaly_type?: string
  status?: string
  import_job_id?: string
}): void {
  filters.value = searchFilters
  currentPage.value = 1
  clearSelection()
  fetchData()
}

function handleReset(): void {
  filters.value = { status: 'pending' }
  currentPage.value = 1
  clearSelection()
  fetchData()
}

function fetchData(): void {
  loadAnomalies({
    page: currentPage.value,
    page_size: pageSize.value,
    ...filters.value,
  })
  loadSummary({ status: 'pending' })
}

const pendingTotal = computed(() =>
  summary.value.reduce((sum, item) => sum + item.count, 0),
)

function handlePageChange(page: number, size: number): void {
  currentPage.value = page
  pageSize.value = size
  fetchData()
}

function openCorrectModal(anomaly: ImportAnomaly): void {
  currentAnomaly.value = anomaly
  correctModalVisible.value = true
}

async function handleCorrect(correctedValue: string): Promise<void> {
  if (!currentAnomaly.value) return
  const success = await correctAnomaly(currentAnomaly.value.id, correctedValue)
  if (success) {
    correctModalVisible.value = false
    currentAnomaly.value = null
  }
}

async function handleConfirmNormal(anomalyId: string): Promise<void> {
  await confirmNormal(anomalyId)
}

function canCorrect(anomaly: ImportAnomaly): boolean {
  return (
    anomaly.status === 'pending'
    && anomaly.anomaly_type !== 'duplicate'
  )
}

onMounted(() => {
  // 检查 URL 参数中的 import_job_id
  const jobId = route.query.import_job_id as string | undefined
  if (jobId) {
    filters.value.import_job_id = jobId
  }
  fetchData()
})
</script>

<template>
  <div>
    <h2 style="margin-bottom: 16px;">异常数据管理</h2>

    <a-row :gutter="16" style="margin-bottom: 16px;">
      <a-col :span="6">
        <a-card size="small">
          <a-statistic title="待处理总数" :value="pendingTotal" />
        </a-card>
      </a-col>
      <a-col v-for="item in summary" :key="item.anomaly_type" :span="6">
        <a-card size="small">
          <a-statistic
            :title="anomalyTypeLabels[item.anomaly_type] || item.anomaly_type"
            :value="item.count"
          />
        </a-card>
      </a-col>
    </a-row>

    <AnomalyFilterBar
      :initial-filters="filters"
      @search="handleSearch"
      @reset="handleReset"
    />

    <div
      v-if="selectedIds.size > 0"
      style="margin: 16px 0; padding: 8px 16px; background: #e6f7ff; border-radius: 4px; display: flex; align-items: center; gap: 12px;"
    >
      <span>已选中 {{ selectedIds.size }} 项</span>
      <a-space>
        <a-popconfirm
          title="确认将选中项标记为正常数据？"
          @confirm="bulkConfirmNormal"
        >
          <a-button size="small">批量确认正常</a-button>
        </a-popconfirm>
        <a-popconfirm
          :title="`确认删除选中的 ${selectedIds.size} 条异常数据？`"
          @confirm="bulkDelete"
        >
          <a-button size="small" danger>批量删除</a-button>
        </a-popconfirm>
      </a-space>
    </div>

    <a-table
      :columns="columns"
      :data-source="anomalies"
      :loading="isLoading"
      :row-selection="rowSelection"
      :pagination="{
        current: currentPage,
        pageSize: pageSize,
        total: total,
        showSizeChanger: true,
        showTotal: (t: number) => `共 ${t} 条`,
        onChange: handlePageChange,
      }"
      row-key="id"
      size="small"
      :scroll="{ x: 900 }"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'anomaly_type'">
          <a-tag :color="anomalyTypeColors[record.anomaly_type]">
            {{ anomalyTypeLabels[record.anomaly_type] || record.anomaly_type }}
          </a-tag>
        </template>
        <template v-else-if="column.key === 'raw_value'">
          {{ record.raw_value || '-' }}
        </template>
        <template v-else-if="column.key === 'status'">
          <a-tag :color="statusColors[record.status]">
            {{ statusLabels[record.status] || record.status }}
          </a-tag>
        </template>
        <template v-else-if="column.key === 'actions'">
          <a-space v-if="record.status === 'pending'">
            <a-button
              v-if="canCorrect(record)"
              type="link"
              size="small"
              @click="openCorrectModal(record)"
            >
              修正
            </a-button>
            <a-popconfirm
              title="确认标记为正常数据？"
              @confirm="handleConfirmNormal(record.id)"
            >
              <a-button type="link" size="small">确认正常</a-button>
            </a-popconfirm>
            <a-popconfirm
              title="确认删除该条异常数据？"
              @confirm="deleteAnomaly(record.id)"
            >
              <a-button type="link" size="small" danger>删除</a-button>
            </a-popconfirm>
          </a-space>
        </template>
      </template>
    </a-table>

    <AnomalyCorrectModal
      :visible="correctModalVisible"
      :anomaly="currentAnomaly"
      @confirm="handleCorrect"
      @cancel="correctModalVisible = false"
    />
  </div>
</template>
