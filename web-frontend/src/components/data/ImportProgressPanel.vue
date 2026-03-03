<script setup lang="ts">
import { computed } from 'vue'
import type { ImportJob } from '@/types/dataImport'

const props = defineProps<{
  job: ImportJob
}>()

const emit = defineEmits<{
  (e: 'cancel', jobId: string): void
}>()

const progressPercent = computed(() => {
  if (!props.job.total_records || props.job.total_records === 0) {
    return 0
  }
  return Math.round((props.job.processed_records / props.job.total_records) * 100)
})

const progressStatus = computed(() => {
  if (props.job.status === 'completed') return 'success'
  if (props.job.status === 'failed') return 'exception'
  return 'active'
})
</script>

<template>
  <a-card title="当前导入进度" size="small">
    <a-progress
      :percent="progressPercent"
      :status="progressStatus"
      :stroke-color="{ from: '#108ee9', to: '#87d068' }"
    />
    <div style="margin-top: 8px; display: flex; justify-content: space-between; align-items: center;">
      <span style="color: #666;">
        <template v-if="job.status === 'pending'">正在准备...</template>
        <template v-else>
          正在解析第 {{ job.processed_records.toLocaleString() }} /
          {{ job.total_records.toLocaleString() }} 条数据
        </template>
      </span>
      <a-popconfirm
        v-if="job.status === 'processing'"
        title="确定要取消导入吗？已处理的数据不会丢失。"
        ok-text="确定取消"
        cancel-text="继续导入"
        @confirm="emit('cancel', job.id)"
      >
        <a-button danger size="small">取消导入</a-button>
      </a-popconfirm>
    </div>
    <div v-if="job.error_message" style="margin-top: 8px; color: #ff4d4f;">
      错误信息: {{ job.error_message }}
    </div>
  </a-card>
</template>
