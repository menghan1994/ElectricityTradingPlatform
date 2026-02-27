import apiClient from './client'

export interface TokenResponse {
  access_token: string
  token_type: string
}

export type RoleType = 'admin' | 'trader' | 'storage_operator' | 'trading_manager' | 'executive_readonly'

export interface UserRead {
  id: string
  username: string
  display_name: string | null
  phone: string | null
  email: string | null
  role: RoleType
  is_active: boolean
  is_locked: boolean
  last_login_at: string | null
  created_at: string
  updated_at: string
}

export interface ChangePasswordRequest {
  old_password: string
  new_password: string
}

export const authApi = {
  async login(username: string, password: string): Promise<TokenResponse> {
    const response = await apiClient.post<TokenResponse>('/auth/login', {
      username,
      password,
    })
    return response.data
  },

  async refreshToken(): Promise<TokenResponse> {
    const response = await apiClient.post<TokenResponse>('/auth/refresh')
    return response.data
  },

  async logout(): Promise<void> {
    await apiClient.post('/auth/logout')
  },

  async getMe(): Promise<UserRead> {
    const response = await apiClient.get<UserRead>('/auth/me')
    return response.data
  },

  async changePassword(oldPassword: string, newPassword: string): Promise<void> {
    await apiClient.post('/auth/change_password', {
      old_password: oldPassword,
      new_password: newPassword,
    } satisfies ChangePasswordRequest)
  },
}
