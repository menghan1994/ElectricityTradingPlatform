<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { message } from 'ant-design-vue'
import { usePredictionModelConfig } from '@/composables/usePredictionModelConfig'
import { stationApi } from '@/api/station'
import type { StationRead } from '@/types/station'
import type {
  ConnectionTestResult,
  PredictionModel,
  PredictionModelCreate,
  PredictionModelUpdate,
} from '@/types/prediction'
import {
  AUTH_TYPE_LABELS,
  FETCH_STATUS_COLORS,
  FETCH_STATUS_LABELS,
  MODEL_STATUS_COLORS,
  MODEL_STATUS_LABELS,
  MODEL_TYPE_LABELS,
} from '@/types/prediction'
import type { FetchStatus } from '@/types/prediction'
import dayjs from 'dayjs'

const {
  models,
  modelsTotal,
  modelStatuses,
  isLoading,
  isTestingConnection,
  isFetching,
  fetchModels,
  createModel,
  updateModel,
  deleteModel,
  testConnection,
  triggerFetch,
} = usePredictionModelConfig()

// 拉取日期选择
const fetchDatePickerVisible = ref(false)
const fetchTargetModelId = ref<string | null>(null)
const fetchDate = ref<string>(dayjs().add(1, 'day').format('YYYY-MM-DD'))

const currentPage = ref(1)
const pageSize = ref(20)
const filterStationId = ref<string | undefined>(undefined)

// 电站列表（用于选择器）
const stations = ref<StationRead[]>([])
async function loadStations() {
  try {
    const resp = await stationApi.listStations(1, 100)
    stations.value = resp.items
  } catch {
    // 静默
  }
}

// 弹窗状态
const modalVisible = ref(false)
const isEditing = ref(false)
const editingModelId = ref<string | null>(null)
const formState = ref<PredictionModelCreate & { api_key?: string | null }>({
  model_name: '',
  model_type: 'wind',
  api_endpoint: '',
  api_key: null,
  api_auth_type: 'api_key',
  call_frequency_cron: '0 6,12 * * *',
  timeout_seconds: 30,
  station_id: '',
})

// 连接测试结果
const testResult = ref<ConnectionTestResult | null>(null)
const testResultModelId = ref<string | null>(null)

// 状态统计 - 使用 modelStatuses（全量状态），而非分页后的 models
const statusCounts = computed(() => {
  const source = modelStatuses.value.length > 0 ? modelStatuses.value : models.value
  const running = source.filter(m => m.status === 'running').length
  const error = source.filter(m => m.status === 'error').length
  const disabled = source.filter(m => m.status === 'disabled').length
  return { running, error, disabled }
})

// 调用频率预设选项
const cronPresets = [
  { label: '每日2次 (6:00, 12:00)', value: '0 6,12 * * *' },
  { label: '每日3次 (6:00, 12:00, 18:00)', value: '0 6,12,18 * * *' },
  { label: '每6小时', value: '0 */6 * * *' },
]
const isCustomCron = ref(false)

const columns = [
  { title: '模型名称', dataIndex: 'model_name', key: 'model_name', width: 150 },
  { title: '关联电站', key: 'station', width: 120 },
  { title: '类型', dataIndex: 'model_type', key: 'model_type', width: 80 },
  { title: 'API端点', dataIndex: 'api_endpoint', key: 'api_endpoint', ellipsis: true },
  { title: '状态', dataIndex: 'status', key: 'status', width: 100 },
  { title: '最后检查', dataIndex: 'last_check_at', key: 'last_check_at', width: 170 },
  { title: '最后拉取', key: 'last_fetch', width: 170 },
  { title: '操作', key: 'actions', width: 300, fixed: 'right' as const },
]

function getStationName(stationId: string): string {
  const station = stations.value.find(s => s.id === stationId)
  return station?.name || stationId.slice(0, 8)
}

function formatDateTime(dt: string | null): string {
  if (!dt) return '-'
  return new Date(dt).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' })
}

function truncateUrl(url: string, maxLen = 40): string {
  return url.length > maxLen ? `${url.slice(0, maxLen)}...` : url
}

function fetchData() {
  fetchModels({
    station_id: filterStationId.value,
    page: currentPage.value,
    page_size: pageSize.value,
  })
}

function handlePageChange(page: number, size: number) {
  currentPage.value = page
  pageSize.value = size
  fetchData()
}

function handleFilterChange() {
  currentPage.value = 1
  fetchData()
}

function openCreateModal() {
  isEditing.value = false
  editingModelId.value = null
  formState.value = {
    model_name: '',
    model_type: 'wind',
    api_endpoint: '',
    api_key: null,
    api_auth_type: 'api_key',
    call_frequency_cron: '0 6,12 * * *',
    timeout_seconds: 30,
    station_id: '',
  }
  isCustomCron.value = false
  modalVisible.value = true
}

function openEditModal(record: PredictionModel) {
  isEditing.value = true
  editingModelId.value = record.id
  const presetMatch = cronPresets.some(p => p.value === record.call_frequency_cron)
  isCustomCron.value = !presetMatch
  formState.value = {
    model_name: record.model_name,
    model_type: record.model_type,
    api_endpoint: record.api_endpoint,
    api_key: null,
    api_auth_type: record.api_auth_type,
    call_frequency_cron: record.call_frequency_cron,
    timeout_seconds: record.timeout_seconds,
    station_id: record.station_id,
  }
  modalVisible.value = true
}

async function handleModalOk() {
  // 前端表单基础验证
  if (!isEditing.value) {
    if (!formState.value.model_name?.trim()) {
      message.warning('请输入模型名称')
      return
    }
    if (!formState.value.station_id) {
      message.warning('请选择关联电站')
      return
    }
    if (!formState.value.api_endpoint?.trim()) {
      message.warning('请输入API端点')
      return
    }
  }

  let success: boolean
  if (isEditing.value && editingModelId.value) {
    const updateData: PredictionModelUpdate = {}
    if (formState.value.model_name) updateData.model_name = formState.value.model_name
    if (formState.value.model_type) updateData.model_type = formState.value.model_type
    if (formState.value.api_endpoint) updateData.api_endpoint = formState.value.api_endpoint
    if (formState.value.api_key) updateData.api_key = formState.value.api_key
    if (formState.value.api_auth_type) updateData.api_auth_type = formState.value.api_auth_type
    if (formState.value.call_frequency_cron) updateData.call_frequency_cron = formState.value.call_frequency_cron
    if (formState.value.timeout_seconds !== undefined && formState.value.timeout_seconds !== null) {
      updateData.timeout_seconds = formState.value.timeout_seconds
    }
    success = await updateModel(editingModelId.value, updateData)
  } else {
    success = await createModel(formState.value as PredictionModelCreate)
  }

  if (success) {
    modalVisible.value = false
    fetchData()
  }
}

async function handleTestConnection(modelId: string) {
  testResultModelId.value = modelId
  testResult.value = null
  const result = await testConnection(modelId)
  testResult.value = result
}

function openFetchModal(modelId: string) {
  fetchTargetModelId.value = modelId
  fetchDate.value = dayjs().add(1, 'day').format('YYYY-MM-DD')
  fetchDatePickerVisible.value = true
}

async function handleFetch() {
  if (!fetchTargetModelId.value) return
  fetchDatePickerVisible.value = false
  await triggerFetch(fetchTargetModelId.value, fetchDate.value)
}

async function handleToggleActive(record: PredictionModel) {
  const success = await updateModel(record.id, { is_active: !record.is_active })
  if (success) fetchData()
}

async function handleDelete(modelId: string) {
  const success = await deleteModel(modelId)
  if (success) fetchData()
}

function handleCronChange(value: string) {
  if (value === '__custom__') {
    isCustomCron.value = true
    formState.value.call_frequency_cron = ''
  } else {
    isCustomCron.value = false
    formState.value.call_frequency_cron = value
  }
}

onMounted(() => {
  loadStations()
  fetchData()
})
</script>

<template>
  <div>
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
      <h2 style="margin: 0;">预测模型配置</h2>
      <a-button type="primary" @click="openCreateModal">新增模型</a-button>
    </div>

    <!-- 状态概览卡片 -->
    <a-row :gutter="16" style="margin-bottom: 16px;">
      <a-col :span="8">
        <a-card size="small">
          <a-statistic title="运行中" :value="statusCounts.running" :value-style="{ color: '#52C41A' }" />
        </a-card>
      </a-col>
      <a-col :span="8">
        <a-card size="small">
          <a-statistic title="异常" :value="statusCounts.error" :value-style="{ color: '#FF4D4F' }" />
        </a-card>
      </a-col>
      <a-col :span="8">
        <a-card size="small">
          <a-statistic title="已停用" :value="statusCounts.disabled" />
        </a-card>
      </a-col>
    </a-row>

    <!-- 过滤器 -->
    <div style="margin-bottom: 16px;">
      <a-select
        v-model:value="filterStationId"
        placeholder="按电站筛选"
        allow-clear
        style="width: 240px;"
        @change="handleFilterChange"
      >
        <a-select-option v-for="s in stations" :key="s.id" :value="s.id">
          {{ s.name }}
        </a-select-option>
      </a-select>
    </div>

    <!-- 连接测试结果 -->
    <div v-if="testResult" style="margin-bottom: 16px;">
      <a-alert
        v-if="testResult.success"
        type="success"
        :message="`连接成功，延迟 ${testResult.latency_ms}ms`"
        closable
        @close="testResult = null"
      />
      <a-alert
        v-else
        type="error"
        :message="`连接失败: ${testResult.error_message}`"
        closable
        @close="testResult = null"
      />
    </div>

    <!-- 模型列表 -->
    <a-table
      :columns="columns"
      :data-source="models"
      :loading="isLoading"
      :pagination="{
        current: currentPage,
        pageSize: pageSize,
        total: modelsTotal,
        showSizeChanger: true,
        showTotal: (t: number) => `共 ${t} 条`,
        onChange: handlePageChange,
      }"
      row-key="id"
      size="small"
      :scroll="{ x: 1000 }"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'station'">
          {{ getStationName(record.station_id) }}
        </template>
        <template v-else-if="column.key === 'model_type'">
          <a-tag>{{ MODEL_TYPE_LABELS[record.model_type as keyof typeof MODEL_TYPE_LABELS] || record.model_type }}</a-tag>
        </template>
        <template v-else-if="column.key === 'api_endpoint'">
          <a-tooltip :title="record.api_endpoint">
            {{ truncateUrl(record.api_endpoint) }}
          </a-tooltip>
        </template>
        <template v-else-if="column.key === 'status'">
          <a-tag :color="MODEL_STATUS_COLORS[record.status as keyof typeof MODEL_STATUS_COLORS]">
            {{ MODEL_STATUS_LABELS[record.status as keyof typeof MODEL_STATUS_LABELS] || record.status }}
          </a-tag>
        </template>
        <template v-else-if="column.key === 'last_check_at'">
          {{ formatDateTime(record.last_check_at) }}
        </template>
        <template v-else-if="column.key === 'last_fetch'">
          <template v-if="record.last_fetch_at">
            <div>{{ formatDateTime(record.last_fetch_at) }}</div>
            <a-tooltip v-if="record.last_fetch_status === 'failed' || record.last_fetch_status === 'partial'" :title="record.last_fetch_error">
              <a-tag :color="FETCH_STATUS_COLORS[record.last_fetch_status as FetchStatus]">
                {{ FETCH_STATUS_LABELS[record.last_fetch_status as FetchStatus] || record.last_fetch_status }}
              </a-tag>
            </a-tooltip>
            <a-tag v-else-if="record.last_fetch_status" :color="FETCH_STATUS_COLORS[record.last_fetch_status as FetchStatus]">
              {{ FETCH_STATUS_LABELS[record.last_fetch_status as FetchStatus] || record.last_fetch_status }}
            </a-tag>
          </template>
          <template v-else>-</template>
        </template>
        <template v-else-if="column.key === 'actions'">
          <a-space>
            <a-button type="link" size="small" @click="openEditModal(record)">编辑</a-button>
            <a-button
              type="link"
              size="small"
              :loading="isTestingConnection && testResultModelId === record.id"
              @click="handleTestConnection(record.id)"
            >
              测试连接
            </a-button>
            <a-button
              v-if="record.status === 'running'"
              type="link"
              size="small"
              :loading="isFetching && fetchTargetModelId === record.id"
              @click="openFetchModal(record.id)"
            >
              拉取数据
            </a-button>
            <a-button type="link" size="small" @click="handleToggleActive(record)">
              {{ record.is_active ? '停用' : '启用' }}
            </a-button>
            <a-popconfirm title="确认删除该预测模型？" @confirm="handleDelete(record.id)">
              <a-button type="link" size="small" danger>删除</a-button>
            </a-popconfirm>
          </a-space>
        </template>
      </template>
    </a-table>

    <!-- 新增/编辑弹窗 -->
    <a-modal
      v-model:open="modalVisible"
      :title="isEditing ? '编辑预测模型' : '新增预测模型'"
      :confirm-loading="isLoading"
      @ok="handleModalOk"
    >
      <a-form :label-col="{ span: 6 }" :wrapper-col="{ span: 16 }">
        <a-form-item label="模型名称" required>
          <a-input v-model:value="formState.model_name" placeholder="输入模型名称" />
        </a-form-item>
        <a-form-item label="关联电站" required>
          <a-select v-model:value="formState.station_id" placeholder="选择电站" :disabled="isEditing">
            <a-select-option v-for="s in stations" :key="s.id" :value="s.id">
              {{ s.name }}
            </a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="模型类型">
          <a-select v-model:value="formState.model_type">
            <a-select-option value="wind">风电</a-select-option>
            <a-select-option value="solar">光伏</a-select-option>
            <a-select-option value="hybrid">混合</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="API端点" required>
          <a-input v-model:value="formState.api_endpoint" placeholder="https://api.example.com/predict" />
        </a-form-item>
        <a-form-item label="认证方式">
          <a-select v-model:value="formState.api_auth_type">
            <a-select-option v-for="(label, key) in AUTH_TYPE_LABELS" :key="key" :value="key">
              {{ label }}
            </a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="认证密钥">
          <a-input-password
            v-model:value="formState.api_key"
            :placeholder="isEditing ? '留空则不修改' : '输入API密钥'"
          />
        </a-form-item>
        <a-form-item label="调用频率">
          <a-select
            :value="isCustomCron ? '__custom__' : formState.call_frequency_cron"
            @change="handleCronChange"
          >
            <a-select-option v-for="p in cronPresets" :key="p.value" :value="p.value">
              {{ p.label }}
            </a-select-option>
            <a-select-option value="__custom__">自定义 Cron</a-select-option>
          </a-select>
          <a-input
            v-if="isCustomCron"
            v-model:value="formState.call_frequency_cron"
            placeholder="Cron 表达式，如 0 */6 * * *"
            style="margin-top: 8px;"
          />
        </a-form-item>
        <a-form-item label="超时时间(秒)">
          <a-input-number v-model:value="formState.timeout_seconds" :min="1" :max="300" />
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 拉取日期选择弹窗 -->
    <a-modal
      v-model:open="fetchDatePickerVisible"
      title="选择预测日期"
      @ok="handleFetch"
      :confirm-loading="isFetching"
    >
      <a-form-item label="预测日期">
        <a-date-picker
          v-model:value="fetchDate"
          value-format="YYYY-MM-DD"
          style="width: 100%;"
        />
      </a-form-item>
    </a-modal>
  </div>
</template>
