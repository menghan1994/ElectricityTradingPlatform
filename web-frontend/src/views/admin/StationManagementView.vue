<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { message } from 'ant-design-vue'
import type { FormInstance } from 'ant-design-vue'
import type { Rule } from 'ant-design-vue/es/form'
import { getErrorMessage, getErrorCode } from '@/api/errors'
import { useStationStore } from '@/stores/station'
import type { StationCreate, StationUpdate, StationRead, StationType } from '@/types/station'
import { stationTypeLabels } from '@/types/station'
import { provinceOptions } from '@/constants/provinces'

const stationStore = useStationStore()

// MEDIUM: 从 stationTypeLabels 生成选项，消除数据重复
const stationTypeOptions = (Object.entries(stationTypeLabels) as [StationType, string][]).map(
  ([value, label]) => ({ value, label }),
)

const createFormRules: Record<string, Rule[]> = {
  name: [{ required: true, message: '请输入电站名称' }],
  province: [{ required: true, message: '请选择省份' }],
  capacity_mw: [
    { required: true, message: '请输入装机容量' },
    { type: 'number', min: 0.01, message: '装机容量必须大于 0', trigger: 'change' },
  ],
  station_type: [{ required: true, message: '请选择电站类型' }],
}

// 编辑表单规则：字段非必填（StationUpdate 允许部分更新），但有值时校验格式
const editFormRules: Record<string, Rule[]> = {
  name: [{ required: false }],
  province: [{ required: false }],
  capacity_mw: [{ required: false }],
  station_type: [{ required: false }],
}

const createFormRef = ref<FormInstance>()
const editFormRef = ref<FormInstance>()

// Create station dialog
const createDialogVisible = ref(false)
const createForm = ref<StationCreate>({
  name: '',
  province: '',
  capacity_mw: 0.01,
  station_type: 'wind',
  has_storage: false,
})
const isCreating = ref(false)

// Edit station dialog
const editDialogVisible = ref(false)
const editStationId = ref('')
const editForm = ref<StationUpdate>({})
const editStationName = ref('')
const isEditing = ref(false)
const editOriginal = ref<StationRead | null>(null)

// Toggle active loading guard
const isToggling = ref(false)

// Filters
const searchText = ref('')
const selectedProvince = ref<string | undefined>(undefined)
const selectedType = ref<string | undefined>(undefined)

const columns = [
  { title: '电站名称', dataIndex: 'name', key: 'name' },
  { title: '省份', dataIndex: 'province', key: 'province' },
  { title: '类型', dataIndex: 'station_type', key: 'station_type' },
  { title: '容量(MW)', dataIndex: 'capacity_mw', key: 'capacity_mw' },
  { title: '储能', dataIndex: 'has_storage', key: 'has_storage' },
  { title: '状态', dataIndex: 'is_active', key: 'is_active' },
  { title: '操作', key: 'actions', width: 200 },
]

onMounted(() => {
  stationStore.fetchStations().catch(() => {
    message.error('加载电站列表失败')
  })
})

function handleTableChange(pagination: { current: number; pageSize: number }) {
  stationStore.fetchStations(pagination.current, pagination.pageSize).catch(() => {
    message.error('加载电站列表失败')
  })
}

function handleSearch() {
  // 显式设置 Store 筛选状态，避免 undefined 被误判为"不变更"（清除筛选时 select value 为 undefined）
  stationStore.searchQuery = searchText.value
  stationStore.provinceFilter = selectedProvince.value ?? ''
  stationStore.typeFilter = selectedType.value ?? ''
  stationStore.fetchStations(1).catch(() => {
    message.error('搜索失败')
  })
}

function handleFilterChange() {
  stationStore.searchQuery = searchText.value
  stationStore.provinceFilter = selectedProvince.value ?? ''
  stationStore.typeFilter = selectedType.value ?? ''
  stationStore.fetchStations(1).catch(() => {
    message.error('筛选失败')
  })
}

function openCreateDialog() {
  createForm.value = { name: '', province: '', capacity_mw: 0.01, station_type: 'wind', has_storage: false }
  createDialogVisible.value = true
}

async function handleCreate() {
  try {
    await createFormRef.value?.validateFields()
  } catch {
    return
  }
  isCreating.value = true
  try {
    await stationStore.createStation(createForm.value)
    createDialogVisible.value = false
    message.success('电站创建成功')
  } catch (err: unknown) {
    message.error(getErrorMessage(err, '创建失败'))
  } finally {
    isCreating.value = false
  }
}

function openEditDialog(record: StationRead) {
  editOriginal.value = record
  editStationId.value = record.id
  editStationName.value = record.name
  editForm.value = {
    name: record.name,
    province: record.province,
    capacity_mw: Number(record.capacity_mw),
    station_type: record.station_type,
    has_storage: record.has_storage,
  }
  editDialogVisible.value = true
}

async function handleEdit() {
  try {
    await editFormRef.value?.validateFields()
  } catch {
    return
  }

  // Compute only the fields that actually changed
  const changedFields: StationUpdate = {}
  const original = editOriginal.value
  if (original) {
    if (editForm.value.name !== original.name) changedFields.name = editForm.value.name
    if (editForm.value.province !== original.province) changedFields.province = editForm.value.province
    if (editForm.value.capacity_mw !== Number(original.capacity_mw)) changedFields.capacity_mw = editForm.value.capacity_mw
    if (editForm.value.station_type !== original.station_type) changedFields.station_type = editForm.value.station_type
    if (editForm.value.has_storage !== original.has_storage) changedFields.has_storage = editForm.value.has_storage
  }

  if (Object.keys(changedFields).length === 0) {
    editDialogVisible.value = false
    return
  }

  isEditing.value = true
  try {
    await stationStore.updateStation(editStationId.value, changedFields)
    editDialogVisible.value = false
    message.success('电站信息已更新')
  } catch (err: unknown) {
    message.error(getErrorMessage(err, '更新失败'))
  } finally {
    isEditing.value = false
  }
}

// HIGH-8: 处理停用时的 STATION_HAS_BINDINGS 409 错误
async function handleToggleActive(record: StationRead) {
  if (isToggling.value) return
  isToggling.value = true
  try {
    if (record.is_active) {
      await stationStore.updateStation(record.id, { is_active: false })
      message.success('电站已停用')
    } else {
      await stationStore.updateStation(record.id, { is_active: true })
      message.success('电站已启用')
    }
  } catch (err: unknown) {
    const code = getErrorCode(err)
    if (code === 'STATION_HAS_BINDINGS') {
      message.warning('该电站有交易员绑定关系，请先解除绑定后再停用')
    } else {
      message.error(getErrorMessage(err, '操作失败'))
    }
  } finally {
    isToggling.value = false
  }
}

const pagination = computed(() => ({
  current: stationStore.page,
  pageSize: stationStore.pageSize,
  total: stationStore.total,
  showSizeChanger: true,
  showTotal: (total: number) => `共 ${total} 条`,
}))
</script>

<template>
  <div>
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
      <h2 style="margin: 0;">电站管理</h2>
      <a-button type="primary" @click="openCreateDialog">+ 创建电站</a-button>
    </div>

    <div style="display: flex; gap: 12px; margin-bottom: 16px;">
      <a-input-search
        v-model:value="searchText"
        placeholder="搜索电站名称"
        style="width: 240px;"
        allow-clear
        @search="handleSearch"
        @pressEnter="handleSearch"
      />
      <a-select
        v-model:value="selectedProvince"
        placeholder="省份筛选"
        style="width: 140px;"
        allow-clear
        @change="handleFilterChange"
      >
        <a-select-option v-for="p in provinceOptions" :key="p" :value="p">{{ p }}</a-select-option>
      </a-select>
      <a-select
        v-model:value="selectedType"
        placeholder="类型筛选"
        style="width: 140px;"
        allow-clear
        @change="handleFilterChange"
      >
        <a-select-option v-for="opt in stationTypeOptions" :key="opt.value" :value="opt.value">
          {{ opt.label }}
        </a-select-option>
      </a-select>
    </div>

    <a-alert
      v-if="stationStore.error"
      type="error"
      :message="stationStore.error"
      show-icon
      closable
      style="margin-bottom: 16px;"
    />

    <a-table
      :columns="columns"
      :data-source="stationStore.stationList"
      :loading="stationStore.isLoading"
      :pagination="pagination"
      row-key="id"
      @change="handleTableChange"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'station_type'">
          {{ stationTypeLabels[record.station_type as StationType] || record.station_type }}
        </template>

        <template v-else-if="column.key === 'has_storage'">
          <a-tag :color="record.has_storage ? 'blue' : 'default'">
            {{ record.has_storage ? '是' : '否' }}
          </a-tag>
        </template>

        <template v-else-if="column.key === 'is_active'">
          <a-tag :color="record.is_active ? 'green' : 'red'">
            {{ record.is_active ? '启用' : '已停用' }}
          </a-tag>
        </template>

        <template v-else-if="column.key === 'actions'">
          <a-space>
            <a-button size="small" @click="openEditDialog(record)">编辑</a-button>
            <a-popconfirm
              :title="record.is_active ? '确定停用该电站？' : '确定启用该电站？'"
              ok-text="确定"
              cancel-text="取消"
              @confirm="handleToggleActive(record)"
            >
              <a-button size="small" :danger="record.is_active">
                {{ record.is_active ? '停用' : '启用' }}
              </a-button>
            </a-popconfirm>
          </a-space>
        </template>
      </template>
    </a-table>

    <!-- 创建电站对话框 -->
    <a-modal
      v-model:open="createDialogVisible"
      title="创建电站"
      :confirm-loading="isCreating"
      @ok="handleCreate"
    >
      <a-form ref="createFormRef" :model="createForm" :rules="createFormRules" :label-col="{ span: 6 }" :wrapper-col="{ span: 16 }">
        <a-form-item label="电站名称" name="name">
          <a-input v-model:value="createForm.name" placeholder="请输入电站名称" />
        </a-form-item>
        <a-form-item label="省份" name="province">
          <a-select v-model:value="createForm.province" placeholder="请选择省份">
            <a-select-option v-for="p in provinceOptions" :key="p" :value="p">{{ p }}</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="装机容量(MW)" name="capacity_mw">
          <a-input-number v-model:value="createForm.capacity_mw" :min="0.01" :step="10" style="width: 100%;" />
        </a-form-item>
        <a-form-item label="电站类型" name="station_type">
          <a-select v-model:value="createForm.station_type" :options="stationTypeOptions" />
        </a-form-item>
        <a-form-item label="配备储能" name="has_storage">
          <a-switch v-model:checked="createForm.has_storage" />
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 编辑电站对话框 -->
    <a-modal
      v-model:open="editDialogVisible"
      :title="`编辑电站 - ${editStationName}`"
      :confirm-loading="isEditing"
      @ok="handleEdit"
    >
      <a-form ref="editFormRef" :model="editForm" :rules="editFormRules" :label-col="{ span: 6 }" :wrapper-col="{ span: 16 }">
        <a-form-item label="电站名称" name="name">
          <a-input v-model:value="editForm.name" placeholder="请输入电站名称" />
        </a-form-item>
        <a-form-item label="省份" name="province">
          <a-select v-model:value="editForm.province" placeholder="请选择省份">
            <a-select-option v-for="p in provinceOptions" :key="p" :value="p">{{ p }}</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="装机容量(MW)" name="capacity_mw">
          <a-input-number v-model:value="editForm.capacity_mw" :min="0.01" :step="10" style="width: 100%;" />
        </a-form-item>
        <a-form-item label="电站类型" name="station_type">
          <a-select v-model:value="editForm.station_type" :options="stationTypeOptions" />
        </a-form-item>
        <a-form-item label="配备储能" name="has_storage">
          <a-switch v-model:checked="editForm.has_storage" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>
