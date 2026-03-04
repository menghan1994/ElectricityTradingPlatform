<script setup lang="ts">
import { ref } from 'vue'
import { message } from 'ant-design-vue'
import { InboxOutlined } from '@ant-design/icons-vue'
import type { StationRead } from '@/types/station'
import type { EmsFormat, ImportType } from '@/types/dataImport'
import EmsFormatSelector from '@/components/data/EmsFormatSelector.vue'

const props = defineProps<{
  stations: StationRead[]
  isUploading: boolean
  importType: ImportType
  emsFormat: EmsFormat
}>()

const emit = defineEmits<{
  (e: 'upload', file: File, stationId: string): void
  (e: 'update:emsFormat', value: EmsFormat): void
}>()

const selectedStationId = ref<string | null>(null)
const selectedFile = ref<File | null>(null)

const uploadHintMap: Record<ImportType, string> = {
  trading_data: '字段：交易日期、时段(1-96)、出清价格',
  station_output: '字段：交易日期、时段(1-96)、实际出力(kW)',
  storage_operation: '字段：交易日期、时段(1-96)、SOC、充放电功率(kW)、循环次数',
}

function handleBeforeUpload(file: File): false {
  const ext = file.name.split('.').pop()?.toLowerCase()
  if (!ext || !['xlsx', 'csv'].includes(ext)) {
    message.error('仅支持 .xlsx 和 .csv 格式文件')
    return false
  }
  const maxSize = 100 * 1024 * 1024
  if (file.size > maxSize) {
    message.error('文件大小不能超过 100MB')
    return false
  }
  selectedFile.value = file
  return false
}

function handleRemove(): void {
  selectedFile.value = null
}

function filterStationOption(input: string, option: { label?: string }): boolean {
  return (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
}

function handleStartImport(): void {
  if (!selectedStationId.value) {
    message.warning('请先选择目标电站')
    return
  }
  if (!selectedFile.value) {
    message.warning('请先选择要导入的文件')
    return
  }
  emit('upload', selectedFile.value, selectedStationId.value)
}
</script>

<template>
  <div>
    <a-upload-dragger
      :before-upload="handleBeforeUpload"
      :file-list="selectedFile ? [{ uid: '-1', name: selectedFile.name, status: 'done' }] : []"
      :multiple="false"
      accept=".xlsx,.csv"
      @remove="handleRemove"
    >
      <p class="ant-upload-drag-icon">
        <InboxOutlined />
      </p>
      <p class="ant-upload-text">拖拽文件到此区域，或点击上传</p>
      <p class="ant-upload-hint">支持 .xlsx / .csv 格式，单文件最大 100MB</p>
      <p class="ant-upload-hint">{{ uploadHintMap[importType] }}</p>
    </a-upload-dragger>

    <div style="margin-top: 16px; display: flex; align-items: center; gap: 16px; flex-wrap: wrap;">
      <span>目标电站:</span>
      <a-select
        v-model:value="selectedStationId"
        placeholder="请选择电站"
        style="width: 300px;"
        show-search
        :filter-option="filterStationOption"
      >
        <a-select-option
          v-for="station in stations"
          :key="station.id"
          :value="station.id"
          :label="station.name"
        >
          {{ station.name }}
        </a-select-option>
      </a-select>

      <EmsFormatSelector
        v-if="importType === 'storage_operation'"
        :model-value="emsFormat"
        @update:model-value="emit('update:emsFormat', $event)"
      />
    </div>

    <div style="margin-top: 16px;">
      <a-button
        type="primary"
        :loading="isUploading"
        :disabled="!selectedFile || !selectedStationId"
        @click="handleStartImport"
      >
        开始导入
      </a-button>
    </div>
  </div>
</template>
