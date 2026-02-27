import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useUserStore } from '../../../src/stores/user'

vi.mock('../../../src/api/user', () => ({
  userApi: {
    listUsers: vi.fn(),
    getUser: vi.fn(),
    createUser: vi.fn(),
    updateUser: vi.fn(),
    resetPassword: vi.fn(),
    toggleActive: vi.fn(),
    assignRole: vi.fn(),
  },
}))

import { userApi } from '../../../src/api/user'

const mockUserList = {
  items: [
    { id: '1', username: 'admin', display_name: '管理员', phone: null, email: null, role: 'admin', is_active: true, is_locked: false, last_login_at: null, created_at: '2026-01-01', updated_at: '2026-01-01' },
    { id: '2', username: 'trader1', display_name: '交易员1', phone: null, email: null, role: 'trader', is_active: true, is_locked: false, last_login_at: null, created_at: '2026-01-01', updated_at: '2026-01-01' },
  ],
  total: 2,
  page: 1,
  page_size: 20,
}

describe('useUserStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  describe('initial state', () => {
    it('should have empty user list initially', () => {
      const store = useUserStore()
      expect(store.userList).toEqual([])
      expect(store.total).toBe(0)
      expect(store.page).toBe(1)
      expect(store.pageSize).toBe(20)
      expect(store.isLoading).toBe(false)
    })
  })

  describe('fetchUsers', () => {
    it('should fetch and update user list', async () => {
      vi.mocked(userApi.listUsers).mockResolvedValue(mockUserList)

      const store = useUserStore()
      await store.fetchUsers()

      expect(store.userList).toEqual(mockUserList.items)
      expect(store.total).toBe(2)
      expect(store.isLoading).toBe(false)
    })

    it('should pass page and pageSize parameters', async () => {
      vi.mocked(userApi.listUsers).mockResolvedValue(mockUserList)

      const store = useUserStore()
      await store.fetchUsers(2, 10)

      expect(userApi.listUsers).toHaveBeenCalledWith(2, 10, undefined)
    })

    it('should set isLoading during fetch', async () => {
      let resolvePromise: (value: unknown) => void
      const promise = new Promise((resolve) => { resolvePromise = resolve })
      vi.mocked(userApi.listUsers).mockReturnValue(promise as never)

      const store = useUserStore()
      const fetchPromise = store.fetchUsers()

      expect(store.isLoading).toBe(true)

      resolvePromise!(mockUserList)
      await fetchPromise

      expect(store.isLoading).toBe(false)
    })

    it('should reset isLoading and set error on failure', async () => {
      vi.mocked(userApi.listUsers).mockRejectedValue(new Error('Network error'))

      const store = useUserStore()
      await expect(store.fetchUsers()).rejects.toThrow()
      expect(store.isLoading).toBe(false)
      expect(store.error).toBe('Network error')
    })
  })

  describe('searchUsers', () => {
    it('should reset page and search with query', async () => {
      vi.mocked(userApi.listUsers).mockResolvedValue(mockUserList)

      const store = useUserStore()
      store.page = 3
      await store.searchUsers('admin')

      expect(store.page).toBe(1)
      expect(store.searchQuery).toBe('admin')
      expect(userApi.listUsers).toHaveBeenCalled()
    })
  })

  describe('createUser', () => {
    it('should create user and refresh list', async () => {
      const mockResult = { user: mockUserList.items[0], temp_password: 'TempPass@123' }
      vi.mocked(userApi.createUser).mockResolvedValue(mockResult)
      vi.mocked(userApi.listUsers).mockResolvedValue(mockUserList)

      const store = useUserStore()
      const result = await store.createUser({ username: 'newuser', role: 'trader' })

      expect(result.temp_password).toBe('TempPass@123')
      expect(userApi.createUser).toHaveBeenCalledWith({ username: 'newuser', role: 'trader' })
      expect(userApi.listUsers).toHaveBeenCalled()
    })
  })

  describe('updateUser', () => {
    it('should update user and refresh list', async () => {
      vi.mocked(userApi.updateUser).mockResolvedValue(mockUserList.items[0])
      vi.mocked(userApi.listUsers).mockResolvedValue(mockUserList)

      const store = useUserStore()
      await store.updateUser('1', { display_name: '新名字' })

      expect(userApi.updateUser).toHaveBeenCalledWith('1', { display_name: '新名字' })
      expect(userApi.listUsers).toHaveBeenCalled()
    })
  })

  describe('resetPassword', () => {
    it('should reset password and return temp password', async () => {
      vi.mocked(userApi.resetPassword).mockResolvedValue({ temp_password: 'ResetPass@456' })

      const store = useUserStore()
      const result = await store.resetPassword('1')

      expect(result.temp_password).toBe('ResetPass@456')
      expect(userApi.resetPassword).toHaveBeenCalledWith('1')
    })
  })

  describe('toggleActive', () => {
    it('should toggle active status and refresh list', async () => {
      vi.mocked(userApi.toggleActive).mockResolvedValue(mockUserList.items[0])
      vi.mocked(userApi.listUsers).mockResolvedValue(mockUserList)

      const store = useUserStore()
      await store.toggleActive('1', false)

      expect(userApi.toggleActive).toHaveBeenCalledWith('1', false)
      expect(userApi.listUsers).toHaveBeenCalled()
    })
  })

  describe('assignRole', () => {
    it('should assign role and refresh list', async () => {
      vi.mocked(userApi.assignRole).mockResolvedValue(mockUserList.items[0])
      vi.mocked(userApi.listUsers).mockResolvedValue(mockUserList)

      const store = useUserStore()
      await store.assignRole('1', 'admin')

      expect(userApi.assignRole).toHaveBeenCalledWith('1', 'admin')
      expect(userApi.listUsers).toHaveBeenCalled()
    })
  })
})
