import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

// Mock API modules
vi.mock('../../../src/api/user', () => ({
  userApi: {
    listUsers: vi.fn().mockResolvedValue({
      items: [
        { id: '1', username: 'admin', display_name: '管理员', phone: null, email: null, role: 'admin', is_active: true, is_locked: false, last_login_at: null, created_at: '2026-01-01', updated_at: '2026-01-01' },
        { id: '2', username: 'trader1', display_name: '交易员1', phone: '13800138000', email: null, role: 'trader', is_active: true, is_locked: false, last_login_at: '2026-02-27T10:00:00', created_at: '2026-01-01', updated_at: '2026-01-01' },
      ],
      total: 2,
      page: 1,
      page_size: 20,
    }),
    createUser: vi.fn(),
    updateUser: vi.fn(),
    resetPassword: vi.fn(),
    toggleActive: vi.fn(),
    assignRole: vi.fn(),
  },
}))

vi.mock('../../../src/api/auth', () => ({
  authApi: {
    getMe: vi.fn(),
  },
}))

vi.mock('../../../src/router', () => ({
  default: {
    push: vi.fn(),
  },
}))

// Need to mock ant-design-vue message
vi.mock('ant-design-vue', async () => {
  const actual = await vi.importActual('ant-design-vue')
  return {
    ...actual,
    message: {
      success: vi.fn(),
      error: vi.fn(),
    },
    Modal: {
      confirm: vi.fn(),
    },
  }
})

import UserManagementView from '../../../src/views/admin/UserManagementView.vue'
import { useUserStore } from '../../../src/stores/user'
import { userApi } from '../../../src/api/user'

const defaultStubs = {
  'a-table': true,
  'a-button': { template: '<button><slot /></button>' },
  'a-input-search': true,
  'a-modal': true,
  'a-form': true,
  'a-form-item': true,
  'a-input': true,
  'a-select': true,
  'a-tag': true,
  'a-alert': true,
  'a-space': true,
  'a-popconfirm': true,
}

describe('UserManagementView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('should render the page title', () => {
    const wrapper = mount(UserManagementView, {
      global: { stubs: defaultStubs },
    })

    expect(wrapper.text()).toContain('用户管理')
  })

  it('should render create user button', () => {
    const wrapper = mount(UserManagementView, {
      global: { stubs: defaultStubs },
    })

    expect(wrapper.text()).toContain('创建用户')
  })

  it('should call fetchUsers on mount', () => {
    mount(UserManagementView, {
      global: { stubs: defaultStubs },
    })

    expect(userApi.listUsers).toHaveBeenCalled()
  })

  it('should use store for create user instead of direct API', async () => {
    vi.mocked(userApi.createUser).mockResolvedValue({
      user: { id: '3', username: 'new', display_name: null, phone: null, email: null, role: 'trader', is_active: true, is_locked: false, last_login_at: null, created_at: '2026-01-01', updated_at: '2026-01-01' },
      temp_password: 'Temp@123',
    })

    const store = useUserStore()
    const result = await store.createUser({ username: 'newuser', role: 'trader' })

    expect(result.temp_password).toBe('Temp@123')
    expect(userApi.createUser).toHaveBeenCalled()
  })

  it('should use store for toggle active instead of direct API', async () => {
    vi.mocked(userApi.toggleActive).mockResolvedValue({
      id: '1', username: 'admin', display_name: null, phone: null, email: null, role: 'admin', is_active: false, is_locked: false, last_login_at: null, created_at: '2026-01-01', updated_at: '2026-01-01',
    })

    const store = useUserStore()
    await store.toggleActive('1', false)

    expect(userApi.toggleActive).toHaveBeenCalledWith('1', false)
  })

  it('should use store for assign role instead of direct API', async () => {
    vi.mocked(userApi.assignRole).mockResolvedValue({
      id: '2', username: 'trader1', display_name: null, phone: null, email: null, role: 'admin', is_active: true, is_locked: false, last_login_at: null, created_at: '2026-01-01', updated_at: '2026-01-01',
    })

    const store = useUserStore()
    await store.assignRole('2', 'admin')

    expect(userApi.assignRole).toHaveBeenCalledWith('2', 'admin')
  })

  it('should use store for reset password instead of direct API', async () => {
    vi.mocked(userApi.resetPassword).mockResolvedValue({ temp_password: 'Reset@789' })

    const store = useUserStore()
    const result = await store.resetPassword('1')

    expect(result.temp_password).toBe('Reset@789')
    expect(userApi.resetPassword).toHaveBeenCalledWith('1')
  })
})
