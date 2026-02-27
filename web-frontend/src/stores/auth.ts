import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { authApi, type UserRead } from '@/api/auth'
import router from '@/router'

export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref<string | null>(localStorage.getItem('access_token'))
  const user = ref<UserRead | null>(null)
  const isAuthenticated = computed(() => !!accessToken.value)

  async function login(username: string, password: string): Promise<void> {
    const data = await authApi.login(username, password)
    accessToken.value = data.access_token
    localStorage.setItem('access_token', data.access_token)
    await fetchMe()
  }

  async function logout(): Promise<void> {
    try {
      await authApi.logout()
    } catch {
      // 忽略登出 API 错误，确保前端状态清除
    }
    clearAuth()
    router.push('/login')
  }

  async function refreshToken(): Promise<string | null> {
    try {
      const data = await authApi.refreshToken()
      accessToken.value = data.access_token
      localStorage.setItem('access_token', data.access_token)
      return data.access_token
    } catch {
      clearAuth()
      return null
    }
  }

  async function fetchMe(): Promise<void> {
    try {
      user.value = await authApi.getMe()
    } catch {
      // Token 无效时清除认证状态
      clearAuth()
    }
  }

  function clearAuth(): void {
    accessToken.value = null
    user.value = null
    localStorage.removeItem('access_token')
  }

  return {
    accessToken,
    user,
    isAuthenticated,
    login,
    logout,
    refreshToken,
    fetchMe,
    clearAuth,
  }
})
