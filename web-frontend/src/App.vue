<script setup lang="ts">
import { theme } from 'ant-design-vue'
import type { ThemeConfig } from 'ant-design-vue/es/config-provider/context'
import { useAuth } from '@/composables/useAuth'

const themeConfig: ThemeConfig = {
  token: {
    colorPrimary: '#1B3A5C',
    colorSuccess: '#52C41A',
    colorWarning: '#FA8C16',
    colorError: '#FF4D4F',
    colorInfo: '#1890FF',
    borderRadius: 4,
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif",
    fontSize: 14,
  },
  algorithm: theme.defaultAlgorithm,
}

const { authStore } = useAuth()
</script>

<template>
  <a-config-provider :theme="themeConfig">
    <a-layout style="min-height: 100vh">
      <a-layout-sider v-if="authStore.isAuthenticated" :width="240" theme="dark">
        <div style="height: 64px; display: flex; align-items: center; justify-content: center; color: white; font-size: 1.125rem; font-weight: 600;">
          电力交易平台
        </div>
        <a-menu theme="dark" mode="inline">
          <a-menu-item key="dashboard">
            <router-link to="/">首页</router-link>
          </a-menu-item>
          <a-menu-item v-if="authStore.user?.role === 'admin'" key="user-management">
            <router-link to="/admin/users">用户管理</router-link>
          </a-menu-item>
        </a-menu>
      </a-layout-sider>
      <a-layout>
        <a-layout-header style="background: #fff; padding: 0 24px; display: flex; align-items: center; justify-content: space-between;">
          <span style="font-size: 1rem; font-weight: 500;">电力交易智能决策平台</span>
          <div v-if="authStore.isAuthenticated" style="display: flex; align-items: center; gap: 12px;">
            <span>{{ authStore.user?.display_name || authStore.user?.username }}</span>
            <a-button size="small" @click="authStore.logout()">登出</a-button>
          </div>
        </a-layout-header>
        <a-layout-content style="margin: 16px; padding: 24px; background: #fff; border-radius: 4px; flex: 1;">
          <router-view />
        </a-layout-content>
      </a-layout>
    </a-layout>
  </a-config-provider>
</template>

<style>
html {
  font-size: 14px;
}

.ant-table .ant-table-cell,
.period-grid {
  font-family: 'JetBrains Mono', monospace;
}
</style>
