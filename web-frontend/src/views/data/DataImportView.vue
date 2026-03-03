<script setup lang="ts">
import { computed, onMounted, onUnmounted } from 'vue'
import { message } from 'ant-design-vue'
import { useDataImport } from '@/composables/useDataImport'
import { useStationStore } from '@/stores/station'
import { getErrorMessage } from '@/api/errors'
import { ref } from 'vue'
import type { StationRead } from '@/types/station'
import ImportUploader from '@/components/data/ImportUploader.vue'
import ImportProgressPanel from '@/components/data/ImportProgressPanel.vue'
import ImportResultSummary from '@/components/data/ImportResultSummary.vue'

const {
  currentJob,
  importResult,
  isUploading,
  importHistory,
  isLoadingHistory,
  uploadFile,
  stopPolling,
  cancelImport,
  resumeImport,
  loadImportHistory,
  resetCurrentJob,
} = useDataImport()

const stationStore = useStationStore()
const stations = ref<StationRead[]>([])
const isLoadingStations = ref(false)

async function loadStations(): Promise<void> {
  isLoadingStations.value = true
  try {
    stations.value = await stationStore.fetchAllActiveStations()
  } catch (e) {
    message.error(getErrorMessage(e, '加载电站列表失败'))
  } finally {
    isLoadingStations.value = false
  }
}

function handleUpload(file: File, stationId: string): void {
  uploadFile(file, stationId)
}

function handleCancel(jobId: string): void {
  cancelImport(jobId)
}

function handleResume(jobId: string): void {
  resumeImport(jobId)
}

function handleHistoryPageChange(page: number, pageSize: number): void {
  loadImportHistory(undefined, page, pageSize)
}

const showUploader = computed(() => {
  return !currentJob.value
})

const showProgress = computed(() => {
  return currentJob.value
    && (currentJob.value.status === 'processing' || currentJob.value.status === 'pending')
})

const showResult = computed(() => {
  return currentJob.value
    && (currentJob.value.status === 'completed' || currentJob.value.status === 'failed'
      || currentJob.value.status === 'cancelled')
})

const statusTagColor: Record<string, string> = {
  pending: 'default',
  processing: 'processing',
  completed: 'success',
  failed: 'error',
  cancelled: 'warning',
}

const statusLabel: Record<string, string> = {
  pending: '等待中',
  processing: '导入中',
  completed: '已完成',
  failed: '失败',
  cancelled: '已取消',
}

const historyColumns = [
  { title: '文件名', dataIndex: 'original_file_name', key: 'file', ellipsis: true },
  { title: '状态', dataIndex: 'status', key: 'status', width: 100 },
  { title: '成功', dataIndex: 'success_records', key: 'success', width: 80 },
  { title: '失败', dataIndex: 'failed_records', key: 'failed', width: 80 },
  { title: '完整性', dataIndex: 'data_completeness', key: 'completeness', width: 100 },
  { title: '操作时间', dataIndex: 'created_at', key: 'time', width: 160 },
]

function formatDate(dateStr: string): string {
  const d = new Date(dateStr)
  return d.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

onMounted(() => {
  loadStations()
  loadImportHistory()
})

onUnmounted(() => {
  stopPolling()
})
</script>

<template>
  <div>
    <h2 style="margin-bottom: 16px;">数据导入</h2>

    <a-spin :spinning="isLoadingStations">
      <!-- 上传区域 -->
      <div v-if="showUploader" style="margin-bottom: 24px;">
        <ImportUploader
          :stations="stations"
          :is-uploading="isUploading"
          @upload="handleUpload"
        />
      </div>

      <!-- 进度面板 -->
      <div v-if="showProgress && currentJob" style="margin-bottom: 24px;">
        <ImportProgressPanel
          :job="currentJob"
          @cancel="handleCancel"
        />
      </div>

      <!-- 结果汇总 -->
      <div v-if="showResult && currentJob" style="margin-bottom: 24px;">
        <ImportResultSummary
          :job="currentJob"
          :result="importResult"
          @resume="handleResume"
        />
        <div style="margin-top: 12px; text-align: center;">
          <a-button @click="resetCurrentJob">返回上传</a-button>
        </div>
      </div>

      <!-- 导入历史 -->
      <a-divider>导入历史</a-divider>

      <a-table
        :columns="historyColumns"
        :data-source="importHistory?.items ?? []"
        :loading="isLoadingHistory"
        :pagination="{
          total: importHistory?.total ?? 0,
          pageSize: importHistory?.page_size ?? 20,
          current: importHistory?.page ?? 1,
          showSizeChanger: true,
          showTotal: (total: number) => `共 ${total} 条`,
          onChange: handleHistoryPageChange,
        }"
        row-key="id"
        size="small"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'status'">
            <a-tag :color="statusTagColor[record.status]">
              {{ statusLabel[record.status] || record.status }}
            </a-tag>
          </template>
          <template v-else-if="column.key === 'completeness'">
            {{ record.data_completeness }}%
          </template>
          <template v-else-if="column.key === 'time'">
            {{ formatDate(record.created_at) }}
          </template>
        </template>
      </a-table>
    </a-spin>
  </div>
</template>
