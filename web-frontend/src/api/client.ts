import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios'

const apiClient = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 独立的 axios 实例用于 refresh 请求，避免拦截器无限循环
const refreshClient = axios.create({
  baseURL: '/api/v1',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
})

apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error),
)

// Token 刷新锁：防止并发请求同时触发多次 refresh
let isRefreshing = false
let pendingRequests: Array<{
  resolve: (token: string) => void
  reject: (error: unknown) => void
}> = []

function onRefreshed(token: string): void {
  pendingRequests.forEach(({ resolve }) => resolve(token))
  pendingRequests = []
}

function onRefreshFailed(error: unknown): void {
  pendingRequests.forEach(({ reject }) => reject(error))
  pendingRequests = []
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<{ code?: string }>) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean }

    if (
      error.response?.status === 401
      && error.response?.data?.code === 'TOKEN_EXPIRED'
      && originalRequest
      && !originalRequest._retry
    ) {
      originalRequest._retry = true

      if (isRefreshing) {
        // 等待正在进行的刷新完成
        return new Promise((resolve, reject) => {
          pendingRequests.push({
            resolve: (token: string) => {
              originalRequest.headers.Authorization = `Bearer ${token}`
              resolve(apiClient(originalRequest))
            },
            reject,
          })
        })
      }

      isRefreshing = true

      try {
        const response = await refreshClient.post<{ access_token: string }>('/auth/refresh')
        const newToken = response.data.access_token
        localStorage.setItem('access_token', newToken)
        originalRequest.headers.Authorization = `Bearer ${newToken}`
        onRefreshed(newToken)
        return apiClient(originalRequest)
      } catch (refreshError) {
        onRefreshFailed(refreshError)
        localStorage.removeItem('access_token')
        window.location.href = '/login'
        return Promise.reject(refreshError)
      } finally {
        isRefreshing = false
      }
    }

    // 其他 401 错误（非 TOKEN_EXPIRED）
    if (error.response?.status === 401 && error.response?.data?.code !== 'TOKEN_EXPIRED') {
      localStorage.removeItem('access_token')
      window.location.href = '/login'
    }

    return Promise.reject(error)
  },
)

export default apiClient
