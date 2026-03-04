<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { dataImportApi } from '@/api/dataImport'
import type { ImportJob } from '@/types/dataImport'

const props = defineProps<{
  initialFilters?: {
    anomaly_type?: string
    status?: string
    import_job_id?: string
  }
}>()

const emit = defineEmits<{
  (e: 'search', filters: {
    anomaly_type?: string
    status?: string
    import_job_id?: string
  }): void
  (e: 'reset'): void
}>()

const selectedAnomalyType = ref<string | undefined>(undefined)
const selectedStatus = ref<string | undefined>('pending')
const selectedJobId = ref<string | undefined>(undefined)
const importJobs = ref<ImportJob[]>([])

const anomalyTypeOptions = [
  { value: 'missing', label: '缺失' },
  { value: 'format_error', label: '格式错误' },
  { value: 'out_of_range', label: '超范围' },
  { value: 'duplicate', label: '重复' },
]

const statusOptions = [
  { value: 'pending', label: '待处理' },
  { value: 'confirmed_normal', label: '已确认正常' },
  { value: 'corrected', label: '已修正' },
  { value: 'deleted', label: '已删除' },
]

watch(
  () => props.initialFilters,
  (val) => {
    if (val) {
      selectedAnomalyType.value = val.anomaly_type
      selectedStatus.value = val.status || 'pending'
      selectedJobId.value = val.import_job_id
    }
  },
  { immediate: true },
)

async function loadImportJobs(): Promise<void> {
  try {
    const response = await dataImportApi.listImportJobs({ page_size: 100 })
    importJobs.value = response.items
  } catch {
    // 静默失败，不影响筛选功能
  }
}

function handleSearch(): void {
  const filters: Record<string, string | undefined> = {}
  if (selectedAnomalyType.value) filters.anomaly_type = selectedAnomalyType.value
  if (selectedStatus.value) filters.status = selectedStatus.value
  if (selectedJobId.value) filters.import_job_id = selectedJobId.value
  emit('search', filters)
}

function handleReset(): void {
  selectedAnomalyType.value = undefined
  selectedStatus.value = 'pending'
  selectedJobId.value = undefined
  emit('reset')
}

onMounted(() => {
  loadImportJobs()
})
</script>

<template>
  <div style="margin-bottom: 16px; display: flex; align-items: center; gap: 12px; flex-wrap: wrap;">
    <div style="display: flex; align-items: center; gap: 4px;">
      <span>导入批次:</span>
      <a-select
        v-model:value="selectedJobId"
        placeholder="全部"
        allow-clear
        style="width: 220px;"
        :options="importJobs.map(j => ({ value: j.id, label: j.original_file_name }))"
      />
    </div>

    <div style="display: flex; align-items: center; gap: 4px;">
      <span>异常类型:</span>
      <a-select
        v-model:value="selectedAnomalyType"
        placeholder="全部"
        allow-clear
        style="width: 130px;"
        :options="anomalyTypeOptions"
      />
    </div>

    <div style="display: flex; align-items: center; gap: 4px;">
      <span>状态:</span>
      <a-select
        v-model:value="selectedStatus"
        placeholder="全部"
        allow-clear
        style="width: 140px;"
        :options="statusOptions"
      />
    </div>

    <a-space>
      <a-button type="primary" @click="handleSearch">查询</a-button>
      <a-button @click="handleReset">重置</a-button>
    </a-space>
  </div>
</template>
