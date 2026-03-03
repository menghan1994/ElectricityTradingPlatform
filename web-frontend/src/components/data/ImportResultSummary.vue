<script setup lang="ts">
import { computed } from 'vue'
import type { ImportJob, ImportResult } from '@/types/dataImport'

const props = defineProps<{
  job: ImportJob
  result: ImportResult | null
}>()

const emit = defineEmits<{
  (e: 'resume', jobId: string): void
}>()

const resultStatus = computed(() => {
  if (props.job.status === 'completed') return 'success'
  if (props.job.status === 'failed') return 'error'
  return 'info'
})

const resultTitle = computed(() => {
  if (props.job.status === 'completed') return '导入完成'
  if (props.job.status === 'failed') return '导入失败'
  if (props.job.status === 'cancelled') return '导入已取消'
  return '导入状态'
})

const canResume = computed(() =>
  props.job.status === 'failed' || props.job.status === 'cancelled',
)

const anomalyTypeLabels: Record<string, string> = {
  missing: '缺失',
  format_error: '格式错误',
  out_of_range: '超范围',
  duplicate: '重复',
}

const anomalyColumns = [
  { title: '异常类型', dataIndex: 'anomaly_type', key: 'anomaly_type' },
  { title: '数量', dataIndex: 'count', key: 'count' },
]
</script>

<template>
  <div>
    <a-result
      :status="resultStatus"
      :title="resultTitle"
      :sub-title="job.status === 'failed' ? job.error_message : undefined"
    >
      <template #extra>
        <a-button
          v-if="canResume"
          type="primary"
          @click="emit('resume', job.id)"
        >
          恢复导入
        </a-button>
      </template>
    </a-result>

    <a-row v-if="result" :gutter="16" style="margin-top: 16px;">
      <a-col :span="6">
        <a-statistic title="总记录数" :value="result.total_records" />
      </a-col>
      <a-col :span="6">
        <a-statistic title="成功数" :value="result.success_records" :value-style="{ color: '#3f8600' }" />
      </a-col>
      <a-col :span="6">
        <a-statistic title="失败数" :value="result.failed_records" :value-style="{ color: '#cf1322' }" />
      </a-col>
      <a-col :span="6">
        <a-statistic title="数据完整性" :value="result.data_completeness" suffix="%" :precision="2" />
      </a-col>
    </a-row>

    <div v-if="result && result.anomaly_summary.length > 0" style="margin-top: 16px;">
      <h4>异常分类汇总</h4>
      <a-table
        :columns="anomalyColumns"
        :data-source="result.anomaly_summary"
        :pagination="false"
        size="small"
        row-key="anomaly_type"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.dataIndex === 'anomaly_type'">
            {{ anomalyTypeLabels[record.anomaly_type] || record.anomaly_type }}
          </template>
        </template>
      </a-table>
    </div>
  </div>
</template>
