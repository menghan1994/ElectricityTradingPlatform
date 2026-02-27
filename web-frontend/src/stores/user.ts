import { ref } from 'vue'
import { defineStore } from 'pinia'
import type { RoleType, UserRead } from '@/api/auth'
import { userApi } from '@/api/user'
import type { AdminUserCreate, UserUpdate, AdminCreateUserResponse, AdminResetPasswordResponse } from '@/api/user'

export const useUserStore = defineStore('user', () => {
  const userList = ref<UserRead[]>([])
  const total = ref(0)
  const page = ref(1)
  const pageSize = ref(20)
  const isLoading = ref(false)
  const searchQuery = ref('')
  const error = ref<string | null>(null)

  async function fetchUsers(p?: number, ps?: number, search?: string): Promise<void> {
    isLoading.value = true
    error.value = null
    try {
      if (p !== undefined) page.value = p
      if (ps !== undefined) pageSize.value = ps
      if (search !== undefined) searchQuery.value = search

      const data = await userApi.listUsers(page.value, pageSize.value, searchQuery.value || undefined)
      userList.value = data.items
      total.value = data.total
      page.value = data.page
      pageSize.value = data.page_size
    } catch (e) {
      error.value = e instanceof Error ? e.message : '加载用户列表失败'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  async function searchUsers(query: string): Promise<void> {
    page.value = 1
    searchQuery.value = query
    await fetchUsers()
  }

  async function createUser(data: AdminUserCreate): Promise<AdminCreateUserResponse> {
    const result = await userApi.createUser(data)
    await fetchUsers()
    return result
  }

  async function updateUser(userId: string, data: UserUpdate): Promise<UserRead> {
    const result = await userApi.updateUser(userId, data)
    await fetchUsers()
    return result
  }

  async function resetPassword(userId: string): Promise<AdminResetPasswordResponse> {
    const result = await userApi.resetPassword(userId)
    await fetchUsers()
    return result
  }

  async function toggleActive(userId: string, isActive: boolean): Promise<UserRead> {
    const result = await userApi.toggleActive(userId, isActive)
    await fetchUsers()
    return result
  }

  async function assignRole(userId: string, role: RoleType): Promise<UserRead> {
    const result = await userApi.assignRole(userId, role)
    await fetchUsers()
    return result
  }

  return {
    userList,
    total,
    page,
    pageSize,
    isLoading,
    searchQuery,
    error,
    fetchUsers,
    searchUsers,
    createUser,
    updateUser,
    resetPassword,
    toggleActive,
    assignRole,
  }
})
