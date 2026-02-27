import apiClient from './client'
import type { RoleType, UserRead } from './auth'

export interface AdminUserCreate {
  username: string
  display_name?: string | null
  phone?: string | null
  email?: string | null
  role?: RoleType
}

export interface UserUpdate {
  display_name?: string | null
  phone?: string | null
  email?: string | null
}

export interface UserListResponse {
  items: UserRead[]
  total: number
  page: number
  page_size: number
}

export interface AdminCreateUserResponse {
  user: UserRead
  temp_password: string
}

export interface AdminResetPasswordResponse {
  temp_password: string
}

export interface RoleAssignRequest {
  role: RoleType
}

export interface StatusToggleRequest {
  is_active: boolean
}

export const userApi = {
  async listUsers(page: number = 1, pageSize: number = 20, search?: string): Promise<UserListResponse> {
    const params: Record<string, string | number> = { page, page_size: pageSize }
    if (search) {
      params.search = search
    }
    const response = await apiClient.get<UserListResponse>('/users', { params })
    return response.data
  },

  async getUser(userId: string): Promise<UserRead> {
    const response = await apiClient.get<UserRead>(`/users/${userId}`)
    return response.data
  },

  async createUser(data: AdminUserCreate): Promise<AdminCreateUserResponse> {
    const response = await apiClient.post<AdminCreateUserResponse>('/users', data)
    return response.data
  },

  async updateUser(userId: string, data: UserUpdate): Promise<UserRead> {
    const response = await apiClient.put<UserRead>(`/users/${userId}`, data)
    return response.data
  },

  async resetPassword(userId: string): Promise<AdminResetPasswordResponse> {
    const response = await apiClient.post<AdminResetPasswordResponse>(`/users/${userId}/reset_password`)
    return response.data
  },

  async toggleActive(userId: string, isActive: boolean): Promise<UserRead> {
    const response = await apiClient.put<UserRead>(`/users/${userId}/status`, {
      is_active: isActive,
    } satisfies StatusToggleRequest)
    return response.data
  },

  async assignRole(userId: string, role: RoleType): Promise<UserRead> {
    const response = await apiClient.put<UserRead>(`/users/${userId}/role`, {
      role,
    } satisfies RoleAssignRequest)
    return response.data
  },
}
