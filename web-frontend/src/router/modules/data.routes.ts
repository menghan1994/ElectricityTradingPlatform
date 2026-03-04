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
  {
    path: '/data/import',
    name: 'DataImport',
    component: () => import('@/views/data/DataImportView.vue'),
    meta: { requiresAuth: true, roles: ['admin'] },
  },
  {
    path: '/data/anomalies',
    name: 'AnomalyManagement',
    component: () => import('@/views/data/AnomalyManagementView.vue'),
    meta: { requiresAuth: true, roles: ['admin'] },
  },
  {
    path: '/data/market-data',
    name: 'MarketData',
    component: () => import('@/views/data/MarketDataView.vue'),
    meta: { requiresAuth: true, roles: ['admin'] },
  },
]
