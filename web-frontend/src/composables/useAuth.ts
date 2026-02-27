import { onMounted, onUnmounted, watch } from 'vue'
import { useAuthStore } from '@/stores/auth'

const INACTIVITY_TIMEOUT_MS = 30 * 60 * 1000 // 30分钟
const ACTIVITY_EVENTS = ['mousemove', 'keydown', 'click', 'scroll', 'touchstart'] as const

/**
 * 认证组合式函数 — 管理30分钟无操作自动登出
 */
export function useAuth() {
  const authStore = useAuthStore()
  let inactivityTimer: ReturnType<typeof setTimeout> | null = null

  function resetTimer(): void {
    if (inactivityTimer) {
      clearTimeout(inactivityTimer)
    }
    if (authStore.isAuthenticated) {
      inactivityTimer = setTimeout(() => {
        authStore.logout()
      }, INACTIVITY_TIMEOUT_MS)
    }
  }

  function startWatching(): void {
    for (const event of ACTIVITY_EVENTS) {
      document.addEventListener(event, resetTimer, { passive: true })
    }
    resetTimer()
  }

  function stopWatching(): void {
    for (const event of ACTIVITY_EVENTS) {
      document.removeEventListener(event, resetTimer)
    }
    if (inactivityTimer) {
      clearTimeout(inactivityTimer)
      inactivityTimer = null
    }
  }

  // 响应认证状态变化：登录后开始监听，登出后停止
  watch(() => authStore.isAuthenticated, (isAuth) => {
    if (isAuth) {
      startWatching()
    } else {
      stopWatching()
    }
  })

  onMounted(() => {
    if (authStore.isAuthenticated) {
      startWatching()
    }
  })

  onUnmounted(() => {
    stopWatching()
  })

  return {
    authStore,
    startWatching,
    stopWatching,
  }
}
