import type { RouteRecordRaw } from 'vue-router'

export const dataRoutes: RouteRecordRaw[] = [
  {
    path: '/data/stations',
    name: 'StationConfig',
    component: () => import('@/views/data/StationConfigView.vue'),
    meta: { requiresAuth: true, roles: ['admin'] },
  },
  {
    path: '/data/market-rules',
    name: 'MarketRuleConfig',
    component: () => import('@/views/data/MarketRuleConfigView.vue'),
    meta: { requiresAuth: true, roles: ['admin'] },
  },
]
