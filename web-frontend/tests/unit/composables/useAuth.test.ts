import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { mount } from '@vue/test-utils'
import { defineComponent, nextTick } from 'vue'
import { useAuth } from '../../../src/composables/useAuth'

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

// Helper component to test composable in mounted context
function withSetup<T>(composable: () => T): { result: T; unmount: () => void } {
  let result!: T
  const TestComponent = defineComponent({
    setup() {
      result = composable()
      return {}
    },
    template: '<div></div>',
  })

  const pinia = createPinia()
  const wrapper = mount(TestComponent, {
    global: {
      plugins: [pinia],
    },
  })

  return { result, unmount: () => wrapper.unmount() }
}

describe('useAuth', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    vi.useFakeTimers()
  })

  afterEach(() => {
    localStorage.clear()
    vi.useRealTimers()
    vi.clearAllMocks()
  })

  it('should return authStore', () => {
    const { result, unmount } = withSetup(() => useAuth())
    expect(result.authStore).toBeDefined()
    expect(result.authStore.isAuthenticated).toBe(false)
    unmount()
  })

  it('should provide startWatching and stopWatching functions', () => {
    const { result, unmount } = withSetup(() => useAuth())
    expect(typeof result.startWatching).toBe('function')
    expect(typeof result.stopWatching).toBe('function')
    unmount()
  })

  it('should start watching activity when authenticated', () => {
    localStorage.setItem('access_token', 'test-token')
    const addSpy = vi.spyOn(document, 'addEventListener')

    const { unmount } = withSetup(() => useAuth())

    // Should add listeners for activity events
    const addedEvents = addSpy.mock.calls.map(call => call[0])
    expect(addedEvents).toContain('mousemove')
    expect(addedEvents).toContain('keydown')
    expect(addedEvents).toContain('click')

    addSpy.mockRestore()
    unmount()
  })

  it('should remove listeners on unmount', () => {
    localStorage.setItem('access_token', 'test-token')
    const removeSpy = vi.spyOn(document, 'removeEventListener')

    const { unmount } = withSetup(() => useAuth())
    unmount()

    const removedEvents = removeSpy.mock.calls.map(call => call[0])
    expect(removedEvents).toContain('mousemove')
    expect(removedEvents).toContain('keydown')

    removeSpy.mockRestore()
  })
})
