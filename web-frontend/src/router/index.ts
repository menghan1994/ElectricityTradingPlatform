import { createRouter, createWebHistory } from 'vue-router'
import type { RoleType } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'

declare module 'vue-router' {
  interface RouteMeta {
    requiresAuth?: boolean
    roles?: RoleType[]
  }
}

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'Login',
      component: () => import('@/views/auth/LoginView.vue'),
      meta: { requiresAuth: false },
    },
    {
      path: '/',
      name: 'Dashboard',
      component: () => import('@/views/dashboard/DashboardView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/admin/users',
      name: 'UserManagement',
      component: () => import('@/views/admin/UserManagementView.vue'),
      meta: { requiresAuth: true, roles: ['admin'] },
    },
    {
      path: '/admin/stations',
      name: 'StationManagement',
      component: () => import('@/views/admin/StationManagementView.vue'),
      meta: { requiresAuth: true, roles: ['admin'] },
    },
  ],
})

router.beforeEach(async (to, _from, next) => {
  const authStore = useAuthStore()

  // 刷新后 token 存在但 user 尚未恢复，先获取用户信息
  if (authStore.isAuthenticated && !authStore.user) {
    await authStore.fetchMe()
  }

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next({ path: '/login', query: { redirect: to.fullPath } })
  } else if (to.path === '/login' && authStore.isAuthenticated) {
    next('/')
  } else if (to.meta.roles) {
    const allowedRoles = to.meta.roles
    if (!authStore.user || !allowedRoles.includes(authStore.user.role)) {
      next('/')
    } else {
      next()
    }
  } else {
    next()
  }
})

export default router
