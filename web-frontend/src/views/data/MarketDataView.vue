<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { message } from 'ant-design-vue'
import DataFreshnessBadge from '@/components/common/DataFreshnessBadge.vue'
import { useMarketData } from '@/composables/useMarketData'
import { FRESHNESS_STATUS_LABELS, PRICE_SOURCE_LABELS } from '@/types/marketData'
import type { MarketDataSource, MarketDataSourceCreate } from '@/types/marketData'

const {
  marketDataList,
  marketDataTotal,
  freshnessMap,
  dataSourceList,
  dataSourceTotal,
  isLoading,
  isLoadingSources,
  isFetching,
  isUploading,
  fetchMarketData,
  triggerManualFetch,
  uploadMarketData,
  loadDataSources,
  createDataSource,
  updateDataSource,
  deleteDataSource,
} = useMarketData()

const activeTab = ref('data')
const selectedProvince = ref<string | undefined>(undefined)
const selectedDate = ref<string | undefined>(undefined)
const page = ref(1)
const pageSize = ref(96)
const sourcePage = ref(1)

// 数据源表单
const showSourceModal = ref(false)
const editingSource = ref<MarketDataSource | null>(null)
const sourceForm = ref<MarketDataSourceCreate>({
  province: '',
  source_name: '',
  api_endpoint: null,
  api_key: null,
  api_auth_type: 'api_key',
  fetch_schedule: '0 7,12,17 * * *',
  is_active: true,
  cache_ttl_seconds: 3600,
})

const currentFreshness = computed(() => {
  if (!selectedProvince.value) return null
  return freshnessMap.value.find((f) => f.province === selectedProvince.value) ?? null
})

const priceColumns = [
  { title: '时段', dataIndex: 'period', width: 80 },
  { title: '出清价格(元/MWh)', dataIndex: 'clearing_price', width: 160 },
  { title: '数据来源', dataIndex: 'source', width: 120 },
  { title: '获取时间', dataIndex: 'fetched_at', width: 200 },
]

const sourceColumns = [
  { title: '省份', dataIndex: 'province', width: 100 },
  { title: '数据源名称', dataIndex: 'source_name', width: 160 },
  { title: 'API端点', dataIndex: 'api_endpoint', width: 200, ellipsis: true },
  { title: '获取频率', dataIndex: 'fetch_schedule', width: 140 },
  { title: '最后获取', dataIndex: 'last_fetch_at', width: 180 },
  { title: '状态', dataIndex: 'last_fetch_status', width: 80 },
  { title: '启用', dataIndex: 'is_active', width: 80 },
  { title: '操作', key: 'action', width: 150 },
]

const fetchStatusMap: Record<string, { text: string; color: string }> = {
  pending: { text: '待获取', color: 'default' },
  success: { text: '成功', color: 'green' },
  failed: { text: '失败', color: 'red' },
}

async function handleSearch() {
  page.value = 1
  await fetchMarketData({
    province: selectedProvince.value,
    trading_date: selectedDate.value,
    page: page.value,
    page_size: pageSize.value,
  })
}

async function handlePageChange(p: number, ps: number) {
  page.value = p
  pageSize.value = ps
  await fetchMarketData({
    province: selectedProvince.value,
    trading_date: selectedDate.value,
    page: p,
    page_size: ps,
  })
}

async function handleFetch() {
  if (!selectedProvince.value || !selectedDate.value) {
    message.warning('请先选择省份和日期')
    return
  }
  const result = await triggerManualFetch(selectedProvince.value, selectedDate.value)
  if (result?.status === 'success') {
    await handleSearch()
  }
}

async function handleUpload(info: { file: File }) {
  if (!selectedProvince.value) {
    message.warning('请先选择省份')
    return
  }
  const result = await uploadMarketData(info.file, selectedProvince.value)
  if (result?.status === 'success') {
    await handleSearch()
  }
}

function openCreateSource() {
  editingSource.value = null
  sourceForm.value = {
    province: '',
    source_name: '',
    api_endpoint: null,
    api_key: null,
    api_auth_type: 'api_key',
    fetch_schedule: '0 7,12,17 * * *',
    is_active: true,
    cache_ttl_seconds: 3600,
  }
  showSourceModal.value = true
}

function openEditSource(source: MarketDataSource) {
  editingSource.value = source
  sourceForm.value = {
    province: source.province,
    source_name: source.source_name,
    api_endpoint: source.api_endpoint,
    api_key: null,
    api_auth_type: source.api_auth_type,
    fetch_schedule: source.fetch_schedule,
    is_active: source.is_active,
    cache_ttl_seconds: source.cache_ttl_seconds,
  }
  showSourceModal.value = true
}

async function handleSaveSource() {
  if (editingSource.value) {
    const { province, ...rest } = sourceForm.value
    await updateDataSource(editingSource.value.id, rest)
  } else {
    await createDataSource(sourceForm.value)
  }
  showSourceModal.value = false
}

async function handleDeleteSource(sourceId: string) {
  await deleteDataSource(sourceId)
}

function handleDateChange(_date: unknown, dateString: string | string[]) {
  selectedDate.value = Array.isArray(dateString) ? dateString[0] : dateString || undefined
}

onMounted(async () => {
  await loadDataSources()
})
</script>

<template>
  <div>
    <h2 style="margin-bottom: 16px;">市场数据管理</h2>

    <a-tabs v-model:activeKey="activeTab">
      <!-- 市场数据 Tab -->
      <a-tab-pane key="data" tab="出清价格">
        <!-- 新鲜度提示 -->
        <DataFreshnessBadge
          v-if="selectedProvince"
          :province="selectedProvince"
          :last-updated="currentFreshness?.last_updated"
          :freshness-data="currentFreshness"
        />

        <!-- 筛选栏 -->
        <a-space style="margin-bottom: 16px;">
          <a-select
            v-model:value="selectedProvince"
            placeholder="选择省份"
            style="width: 160px;"
            allow-clear
          >
            <a-select-option
              v-for="source in dataSourceList"
              :key="source.province"
              :value="source.province"
            >
              {{ source.source_name }}
            </a-select-option>
          </a-select>

          <a-date-picker
            :value="undefined"
            placeholder="选择日期"
            @change="handleDateChange"
          />

          <a-button type="primary" @click="handleSearch" :loading="isLoading">
            查询
          </a-button>

          <a-button @click="handleFetch" :loading="isFetching">
            手动获取
          </a-button>

          <a-upload
            :show-upload-list="false"
            :before-upload="() => false"
            @change="handleUpload"
          >
            <a-button :loading="isUploading">
              手动上传
            </a-button>
          </a-upload>
        </a-space>

        <!-- 价格表格 -->
        <a-table
          :columns="priceColumns"
          :data-source="marketDataList"
          :loading="isLoading"
          :pagination="{
            current: page,
            pageSize: pageSize,
            total: marketDataTotal,
            showSizeChanger: true,
            pageSizeOptions: ['20', '50', '96'],
            onChange: handlePageChange,
          }"
          row-key="id"
          size="small"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.dataIndex === 'source'">
              {{ PRICE_SOURCE_LABELS[record.source as keyof typeof PRICE_SOURCE_LABELS] || record.source }}
            </template>
            <template v-else-if="column.dataIndex === 'fetched_at'">
              {{ record.fetched_at ? new Date(record.fetched_at).toLocaleString('zh-CN') : '-' }}
            </template>
          </template>
        </a-table>
      </a-tab-pane>

      <!-- 数据源配置 Tab -->
      <a-tab-pane key="sources" tab="数据源配置">
        <div style="margin-bottom: 16px;">
          <a-button type="primary" @click="openCreateSource">新增数据源</a-button>
        </div>

        <a-table
          :columns="sourceColumns"
          :data-source="dataSourceList"
          :loading="isLoadingSources"
          :pagination="{
            current: sourcePage,
            pageSize: 20,
            total: dataSourceTotal,
          }"
          row-key="id"
          size="small"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.dataIndex === 'last_fetch_at'">
              {{ record.last_fetch_at ? new Date(record.last_fetch_at).toLocaleString('zh-CN') : '-' }}
            </template>
            <template v-else-if="column.dataIndex === 'last_fetch_status'">
              <a-tag :color="fetchStatusMap[record.last_fetch_status]?.color">
                {{ fetchStatusMap[record.last_fetch_status]?.text || record.last_fetch_status }}
              </a-tag>
            </template>
            <template v-else-if="column.dataIndex === 'is_active'">
              <a-tag :color="record.is_active ? 'green' : 'default'">
                {{ record.is_active ? '启用' : '禁用' }}
              </a-tag>
            </template>
            <template v-else-if="column.key === 'action'">
              <a-space>
                <a @click="openEditSource(record)">编辑</a>
                <a-popconfirm
                  title="确定删除此数据源？"
                  @confirm="handleDeleteSource(record.id)"
                >
                  <a style="color: #ff4d4f;">删除</a>
                </a-popconfirm>
              </a-space>
            </template>
          </template>
        </a-table>
      </a-tab-pane>

      <!-- 新鲜度概览 Tab -->
      <a-tab-pane key="freshness" tab="数据新鲜度">
        <a-table
          :data-source="freshnessMap"
          :pagination="false"
          row-key="province"
          size="small"
        >
          <a-table-column title="省份" data-index="province" />
          <a-table-column title="最后更新" data-index="last_updated">
            <template #default="{ record }">
              {{ record.last_updated ? new Date(record.last_updated).toLocaleString('zh-CN') : '无数据' }}
            </template>
          </a-table-column>
          <a-table-column title="距今" data-index="hours_ago">
            <template #default="{ record }">
              {{ record.hours_ago != null ? `${record.hours_ago}小时` : '-' }}
            </template>
          </a-table-column>
          <a-table-column title="状态" data-index="status">
            <template #default="{ record }">
              <a-tag
                :color="{ fresh: 'green', stale: 'default', expired: 'orange', critical: 'red' }[record.status]"
              >
                {{ FRESHNESS_STATUS_LABELS[record.status as keyof typeof FRESHNESS_STATUS_LABELS] }}
              </a-tag>
            </template>
          </a-table-column>
        </a-table>
      </a-tab-pane>
    </a-tabs>

    <!-- 数据源编辑弹窗 -->
    <a-modal
      v-model:open="showSourceModal"
      :title="editingSource ? '编辑数据源' : '新增数据源'"
      @ok="handleSaveSource"
    >
      <a-form layout="vertical">
        <a-form-item label="省份标识" :required="!editingSource">
          <a-input
            v-model:value="sourceForm.province"
            placeholder="如 guangdong"
            :disabled="!!editingSource"
          />
        </a-form-item>
        <a-form-item label="数据源名称" required>
          <a-input v-model:value="sourceForm.source_name" placeholder="如 广东电力交易中心" />
        </a-form-item>
        <a-form-item label="API端点">
          <a-input v-model:value="sourceForm.api_endpoint" placeholder="https://..." />
        </a-form-item>
        <a-form-item label="API密钥">
          <a-input-password
            v-model:value="sourceForm.api_key"
            :placeholder="editingSource ? '留空则不修改' : '输入API密钥'"
          />
        </a-form-item>
        <a-form-item label="认证方式">
          <a-select v-model:value="sourceForm.api_auth_type">
            <a-select-option value="api_key">API Key</a-select-option>
            <a-select-option value="bearer">Bearer Token</a-select-option>
            <a-select-option value="none">无认证</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="获取频率 (Cron)">
          <a-input v-model:value="sourceForm.fetch_schedule" placeholder="0 7,12,17 * * *" />
        </a-form-item>
        <a-form-item label="缓存TTL (秒)">
          <a-input-number v-model:value="sourceForm.cache_ttl_seconds" :min="1" style="width: 100%;" />
        </a-form-item>
        <a-form-item label="启用">
          <a-switch v-model:checked="sourceForm.is_active" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>
