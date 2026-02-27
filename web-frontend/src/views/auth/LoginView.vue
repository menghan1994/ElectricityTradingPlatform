<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import type { Rule } from 'ant-design-vue/es/form'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const formState = reactive({
  username: '',
  password: '',
})

const loading = ref(false)
const errorMessage = ref('')
const errorType = ref<'warning' | 'error'>('warning')

const rules: Record<string, Rule[]> = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 8, message: '密码至少8个字符', trigger: 'blur' },
  ],
}

async function handleLogin(): Promise<void> {
  loading.value = true
  errorMessage.value = ''

  try {
    await authStore.login(formState.username, formState.password)
    const redirect = (route.query.redirect as string) || '/'
    router.push(redirect)
  } catch (err: unknown) {
    const response = (err as { response?: { data?: { code?: string; message?: string; detail?: { remaining_minutes?: number } } } }).response
    if (response?.data) {
      const { code, message, detail } = response.data
      if (code === 'ACCOUNT_LOCKED') {
        errorType.value = 'error'
        errorMessage.value = `账户已锁定，剩余 ${detail?.remaining_minutes ?? '?'} 分钟`
      } else if (code === 'INVALID_CREDENTIALS') {
        errorType.value = 'warning'
        errorMessage.value = message || '用户名或密码错误'
      } else {
        errorType.value = 'error'
        errorMessage.value = message || '登录失败'
      }
    } else {
      errorType.value = 'error'
      errorMessage.value = '网络连接失败，请检查网络'
    }
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div style="display: flex; justify-content: center; align-items: center; min-height: 60vh;">
    <a-card title="登录" style="width: 400px;">
      <a-alert
        v-if="errorMessage"
        :message="errorMessage"
        :type="errorType"
        show-icon
        closable
        style="margin-bottom: 16px;"
        @close="errorMessage = ''"
      />
      <a-form
        :model="formState"
        :rules="rules"
        layout="vertical"
        @finish="handleLogin"
      >
        <a-form-item label="用户名" name="username">
          <a-input
            v-model:value="formState.username"
            placeholder="请输入用户名"
            :disabled="loading"
          />
        </a-form-item>
        <a-form-item label="密码" name="password">
          <a-input-password
            v-model:value="formState.password"
            placeholder="请输入密码"
            :disabled="loading"
            @pressEnter="handleLogin"
          />
        </a-form-item>
        <a-form-item>
          <a-button type="primary" html-type="submit" block :loading="loading">
            登录
          </a-button>
        </a-form-item>
      </a-form>
    </a-card>
  </div>
</template>
