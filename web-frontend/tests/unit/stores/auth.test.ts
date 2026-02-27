import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAuthStore } from '../../../src/stores/auth'

// Mock auth API
vi.mock('../../../src/api/auth', () => ({
  authApi: {
    login: vi.fn(),
    logout: vi.fn(),
    refreshToken: vi.fn(),
    getMe: vi.fn(),
  },
}))

// Mock router
vi.mock('../../../src/router', () => ({
  default: {
    push: vi.fn(),
  },
}))

import { authApi } from '../../../src/api/auth'
import router from '../../../src/router'

describe('useAuthStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    vi.clearAllMocks()
  })

  afterEach(() => {
    localStorage.clear()
  })

  describe('initial state', () => {
    it('should be unauthenticated when no token in localStorage', () => {
      const store = useAuthStore()
      expect(store.isAuthenticated).toBe(false)
      expect(store.accessToken).toBeNull()
      expect(store.user).toBeNull()
    })

    it('should be authenticated when token exists in localStorage', () => {
      localStorage.setItem('access_token', 'test-token')
      const store = useAuthStore()
      expect(store.isAuthenticated).toBe(true)
      expect(store.accessToken).toBe('test-token')
    })
  })

  describe('login', () => {
    it('should store token and fetch user on successful login', async () => {
      const mockToken = { access_token: 'new-access-token', token_type: 'bearer' }
      const mockUser = { id: '1', username: 'admin', display_name: '管理员', phone: null, email: null, role: 'admin', is_active: true, is_locked: false, last_login_at: null, created_at: '2026-01-01', updated_at: '2026-01-01' }

      vi.mocked(authApi.login).mockResolvedValue(mockToken)
      vi.mocked(authApi.getMe).mockResolvedValue(mockUser)

      const store = useAuthStore()
      await store.login('admin', 'password')

      expect(store.accessToken).toBe('new-access-token')
      expect(store.isAuthenticated).toBe(true)
      expect(localStorage.getItem('access_token')).toBe('new-access-token')
      expect(store.user).toEqual(mockUser)
    })

    it('should throw on failed login', async () => {
      vi.mocked(authApi.login).mockRejectedValue(new Error('Login failed'))

      const store = useAuthStore()
      await expect(store.login('wrong', 'wrong')).rejects.toThrow()
      expect(store.isAuthenticated).toBe(false)
    })
  })

  describe('logout', () => {
    it('should clear auth state and redirect to login', async () => {
      localStorage.setItem('access_token', 'test-token')
      vi.mocked(authApi.logout).mockResolvedValue(undefined)

      const store = useAuthStore()
      store.accessToken = 'test-token'
      await store.logout()

      expect(store.accessToken).toBeNull()
      expect(store.user).toBeNull()
      expect(store.isAuthenticated).toBe(false)
      expect(localStorage.getItem('access_token')).toBeNull()
      expect(router.push).toHaveBeenCalledWith('/login')
    })

    it('should clear state even if API call fails', async () => {
      vi.mocked(authApi.logout).mockRejectedValue(new Error('Network error'))

      const store = useAuthStore()
      store.accessToken = 'test-token'
      await store.logout()

      expect(store.isAuthenticated).toBe(false)
      expect(router.push).toHaveBeenCalledWith('/login')
    })
  })

  describe('refreshToken', () => {
    it('should update token on successful refresh', async () => {
      vi.mocked(authApi.refreshToken).mockResolvedValue({
        access_token: 'refreshed-token',
        token_type: 'bearer',
      })

      const store = useAuthStore()
      const result = await store.refreshToken()

      expect(result).toBe('refreshed-token')
      expect(store.accessToken).toBe('refreshed-token')
      expect(localStorage.getItem('access_token')).toBe('refreshed-token')
    })

    it('should clear auth on failed refresh', async () => {
      vi.mocked(authApi.refreshToken).mockRejectedValue(new Error('Expired'))

      const store = useAuthStore()
      store.accessToken = 'old-token'
      const result = await store.refreshToken()

      expect(result).toBeNull()
      expect(store.isAuthenticated).toBe(false)
    })
  })

  describe('clearAuth', () => {
    it('should clear all auth state', () => {
      const store = useAuthStore()
      store.accessToken = 'token'
      store.user = { id: '1', username: 'test', display_name: null, phone: null, email: null, role: 'trader', is_active: true, is_locked: false, last_login_at: null, created_at: '', updated_at: '' }

      store.clearAuth()

      expect(store.accessToken).toBeNull()
      expect(store.user).toBeNull()
      expect(store.isAuthenticated).toBe(false)
      expect(localStorage.getItem('access_token')).toBeNull()
    })
  })
})
