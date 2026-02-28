<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { message } from 'ant-design-vue'
import type { FormInstance } from 'ant-design-vue'
import type { Rule } from 'ant-design-vue/es/form'
import { getErrorMessage } from '@/api/errors'
import type { RoleType, UserRead } from '@/api/auth'
import type { AdminUserCreate, UserUpdate } from '@/api/user'
import { useUserStore } from '@/stores/user'
import { roleLabels, roleColors, roleOptions } from '@/constants/roles'
import BindingConfigDrawer from '@/components/admin/BindingConfigDrawer.vue'

const userStore = useUserStore()

// Form validation rules
const createFormRules: Record<string, Rule[]> = {
  username: [
    { required: true, message: '请输入用户名' },
    { min: 3, max: 32, message: '用户名长度 3-32 个字符' },
    { pattern: /^[a-zA-Z][a-zA-Z0-9_]*$/, message: '用户名需以字母开头，仅含字母、数字和下划线' },
  ],
  email: [
    { type: 'email', message: '请输入有效的邮箱地址' },
  ],
}

const editFormRules: Record<string, Rule[]> = {
  email: [
    { type: 'email', message: '请输入有效的邮箱地址' },
  ],
}

const createFormRef = ref<FormInstance>()
const editFormRef = ref<FormInstance>()

// Create user dialog
const createDialogVisible = ref(false)
const createForm = ref<AdminUserCreate>({
  username: '',
  display_name: '',
  phone: '',
  email: '',
  role: 'trader',
})
const isCreating = ref(false)

// Edit user dialog
const editDialogVisible = ref(false)
const editForm = ref<UserUpdate & { id: string; username: string; role: string }>({
  id: '',
  username: '',
  role: '',
  display_name: '',
  phone: '',
  email: '',
})
const isEditing = ref(false)

// Temp password dialog
const tempPasswordVisible = ref(false)
const tempPassword = ref('')

// Role assign
const roleAssignVisible = ref(false)
const roleAssignUserId = ref('')
const roleAssignUsername = ref('')
const roleAssignValue = ref<RoleType | null>(null)
const isAssigningRole = ref(false)

// Binding drawer
const bindingDrawerVisible = ref(false)
const bindingTargetUser = ref<UserRead | null>(null)

// Search
const searchText = ref('')

const columns = [
  { title: '用户名', dataIndex: 'username', key: 'username' },
  { title: '姓名', dataIndex: 'display_name', key: 'display_name' },
  { title: '角色', dataIndex: 'role', key: 'role' },
  { title: '状态', dataIndex: 'is_active', key: 'is_active' },
  { title: '最后登录', dataIndex: 'last_login_at', key: 'last_login_at' },
  { title: '操作', key: 'actions', width: 320 },
]

onMounted(() => {
  userStore.fetchUsers().catch(() => {
    message.error('加载用户列表失败')
  })
})

function handleTableChange(pagination: { current: number; pageSize: number }) {
  userStore.fetchUsers(pagination.current, pagination.pageSize).catch(() => {
    message.error('加载用户列表失败')
  })
}

function handleSearch() {
  userStore.searchUsers(searchText.value)
}

function openCreateDialog() {
  createForm.value = { username: '', display_name: '', phone: '', email: '', role: 'trader' }
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
    const result = await userStore.createUser(createForm.value)
    createDialogVisible.value = false
    tempPassword.value = result.temp_password
    tempPasswordVisible.value = true
    message.success('用户创建成功')
  } catch (err: unknown) {
    message.error(getErrorMessage(err, '创建失败'))
  } finally {
    isCreating.value = false
  }
}

function openEditDialog(record: UserRead) {
  editForm.value = {
    id: record.id,
    username: record.username,
    role: record.role,
    display_name: record.display_name,
    phone: record.phone,
    email: record.email,
  }
  editDialogVisible.value = true
}

async function handleEdit() {
  try {
    await editFormRef.value?.validateFields()
  } catch {
    return
  }
  isEditing.value = true
  try {
    const { id, username: _u, role: _r, ...data } = editForm.value
    await userStore.updateUser(id, data)
    editDialogVisible.value = false
    message.success('用户信息已更新')
  } catch (err: unknown) {
    message.error(getErrorMessage(err, '更新失败'))
  } finally {
    isEditing.value = false
  }
}

async function handleResetPassword(record: UserRead) {
  try {
    const result = await userStore.resetPassword(record.id)
    tempPassword.value = result.temp_password
    tempPasswordVisible.value = true
    message.success('密码已重置')
  } catch (err: unknown) {
    message.error(getErrorMessage(err, '重置密码失败'))
  }
}

async function handleToggleActive(record: UserRead) {
  try {
    await userStore.toggleActive(record.id, !record.is_active)
    message.success(record.is_active ? '用户已停用' : '用户已启用')
  } catch (err: unknown) {
    message.error(getErrorMessage(err, '操作失败'))
  }
}

function openBindingDrawer(record: UserRead) {
  bindingTargetUser.value = record
  bindingDrawerVisible.value = true
}

function openRoleAssign(record: UserRead) {
  roleAssignUserId.value = record.id
  roleAssignUsername.value = record.username
  roleAssignValue.value = record.role
  roleAssignVisible.value = true
}

async function handleRoleAssign() {
  if (!roleAssignValue.value) return
  isAssigningRole.value = true
  try {
    await userStore.assignRole(roleAssignUserId.value, roleAssignValue.value)
    roleAssignVisible.value = false
    message.success('角色分配成功')
  } catch (err: unknown) {
    message.error(getErrorMessage(err, '角色分配失败'))
  } finally {
    isAssigningRole.value = false
  }
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' })
}

function clearTempPassword() {
  tempPassword.value = ''
}

async function copyToClipboard(text: string) {
  try {
    await navigator.clipboard.writeText(text)
    message.success('已复制到剪贴板')
  } catch {
    message.error('复制失败，请手动复制')
  }
}

const pagination = computed(() => ({
  current: userStore.page,
  pageSize: userStore.pageSize,
  total: userStore.total,
  showSizeChanger: true,
  showTotal: (total: number) => `共 ${total} 条`,
}))
</script>

<template>
  <div>
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
      <h2 style="margin: 0;">用户管理</h2>
      <a-button type="primary" @click="openCreateDialog">+ 创建用户</a-button>
    </div>

    <div style="margin-bottom: 16px;">
      <a-input-search
        v-model:value="searchText"
        placeholder="搜索用户名或姓名"
        style="width: 300px;"
        allow-clear
        @search="handleSearch"
        @pressEnter="handleSearch"
      />
    </div>

    <a-alert
      v-if="userStore.error"
      type="error"
      :message="userStore.error"
      show-icon
      closable
      style="margin-bottom: 16px;"
    />

    <a-table
      :columns="columns"
      :data-source="userStore.userList"
      :loading="userStore.isLoading"
      :pagination="pagination"
      row-key="id"
      @change="handleTableChange"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'role'">
          <a-tag :color="roleColors[record.role] || 'default'">
            {{ roleLabels[record.role] || record.role }}
          </a-tag>
        </template>

        <template v-else-if="column.key === 'is_active'">
          <a-tag :color="record.is_active ? 'green' : 'red'">
            {{ record.is_active ? '活跃' : '已停用' }}
          </a-tag>
        </template>

        <template v-else-if="column.key === 'last_login_at'">
          {{ formatDate(record.last_login_at) }}
        </template>

        <template v-else-if="column.key === 'actions'">
          <a-space>
            <a-button size="small" @click="openEditDialog(record)">编辑</a-button>
            <a-popconfirm
              title="确定重置该用户密码？"
              ok-text="确定"
              cancel-text="取消"
              @confirm="handleResetPassword(record)"
            >
              <a-button size="small">重置密码</a-button>
            </a-popconfirm>
            <a-popconfirm
              :title="record.is_active ? '确定停用该用户？' : '确定启用该用户？'"
              ok-text="确定"
              cancel-text="取消"
              @confirm="handleToggleActive(record)"
            >
              <a-button size="small" :danger="record.is_active">
                {{ record.is_active ? '停用' : '启用' }}
              </a-button>
            </a-popconfirm>
            <a-button size="small" @click="openRoleAssign(record)">角色</a-button>
            <a-button
              v-if="record.role === 'trader' || record.role === 'storage_operator'"
              size="small"
              type="link"
              @click="openBindingDrawer(record)"
            >
              资源绑定
            </a-button>
          </a-space>
        </template>
      </template>
    </a-table>

    <!-- 创建用户对话框 -->
    <a-modal
      v-model:open="createDialogVisible"
      title="创建用户"
      :confirm-loading="isCreating"
      @ok="handleCreate"
    >
      <a-form ref="createFormRef" :model="createForm" :rules="createFormRules" :label-col="{ span: 6 }" :wrapper-col="{ span: 16 }">
        <a-form-item label="用户名" name="username">
          <a-input v-model:value="createForm.username" placeholder="请输入用户名" />
        </a-form-item>
        <a-form-item label="姓名" name="display_name">
          <a-input v-model:value="createForm.display_name" placeholder="请输入姓名" />
        </a-form-item>
        <a-form-item label="联系电话" name="phone">
          <a-input v-model:value="createForm.phone" placeholder="请输入联系电话" />
        </a-form-item>
        <a-form-item label="邮箱" name="email">
          <a-input v-model:value="createForm.email" placeholder="请输入邮箱" />
        </a-form-item>
        <a-form-item label="角色" name="role">
          <a-select v-model:value="createForm.role" :options="roleOptions" />
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 编辑用户对话框 -->
    <a-modal
      v-model:open="editDialogVisible"
      title="编辑用户"
      :confirm-loading="isEditing"
      @ok="handleEdit"
    >
      <a-form ref="editFormRef" :model="editForm" :rules="editFormRules" :label-col="{ span: 6 }" :wrapper-col="{ span: 16 }">
        <a-form-item label="用户名">
          <a-input :value="editForm.username" disabled />
        </a-form-item>
        <a-form-item label="当前角色">
          <a-tag :color="roleColors[editForm.role] || 'default'">
            {{ roleLabels[editForm.role] || editForm.role }}
          </a-tag>
        </a-form-item>
        <a-form-item label="姓名" name="display_name">
          <a-input v-model:value="editForm.display_name" placeholder="请输入姓名" />
        </a-form-item>
        <a-form-item label="联系电话" name="phone">
          <a-input v-model:value="editForm.phone" placeholder="请输入联系电话" />
        </a-form-item>
        <a-form-item label="邮箱" name="email">
          <a-input v-model:value="editForm.email" placeholder="请输入邮箱" />
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 临时密码展示对话框 -->
    <a-modal
      v-model:open="tempPasswordVisible"
      title="临时密码"
      :footer="null"
      :after-close="clearTempPassword"
    >
      <a-alert
        type="warning"
        message="请妥善保管临时密码，此密码仅显示一次。"
        style="margin-bottom: 16px;"
        show-icon
      />
      <div style="display: flex; align-items: center; gap: 8px;">
        <a-input :value="tempPassword" readonly style="font-family: monospace; font-size: 16px;" />
        <a-button @click="copyToClipboard(tempPassword)">复制</a-button>
      </div>
    </a-modal>

    <!-- 角色分配对话框 -->
    <a-modal
      v-model:open="roleAssignVisible"
      :title="`分配角色 - ${roleAssignUsername}`"
      :confirm-loading="isAssigningRole"
      @ok="handleRoleAssign"
    >
      <a-form :label-col="{ span: 6 }" :wrapper-col="{ span: 16 }">
        <a-form-item label="角色">
          <a-select v-model:value="roleAssignValue" :options="roleOptions" />
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 资源绑定抽屉 -->
    <BindingConfigDrawer
      v-model:open="bindingDrawerVisible"
      :user="bindingTargetUser"
    />
  </div>
</template>
