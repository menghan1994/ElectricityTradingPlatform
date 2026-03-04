<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { marketDataApi } from '@/api/marketData'
import type { FreshnessStatus, MarketDataFreshness } from '@/types/marketData'

const props = defineProps<{
  province: string
  lastUpdated?: string | null
  /** 外部传入的 freshness 数据，传入后组件不再自行轮询，避免重复请求。 */
  freshnessData?: MarketDataFreshness | null
}>()

const fetchedFreshness = ref<MarketDataFreshness | null>(null)
const pollTimer = ref<ReturnType<typeof setInterval> | null>(null)

const POLL_INTERVAL = 5 * 60 * 1000 // 5分钟

// 优先使用外部传入的 freshnessData，否则使用自行获取的
const freshness = computed(() => props.freshnessData ?? fetchedFreshness.value)

const status = computed<FreshnessStatus>(() => {
  if (freshness.value) return freshness.value.status
  if (!props.lastUpdated) return 'critical'

  const hoursAgo = (Date.now() - new Date(props.lastUpdated).getTime()) / (1000 * 3600)
  if (hoursAgo < 2) return 'fresh'
  if (hoursAgo < 12) return 'stale'
  if (hoursAgo < 24) return 'expired'
  return 'critical'
})

const hoursAgo = computed(() => {
  if (freshness.value?.hours_ago != null) return freshness.value.hours_ago
  if (!props.lastUpdated) return null
  return Math.round((Date.now() - new Date(props.lastUpdated).getTime()) / (1000 * 3600) * 10) / 10
})

async function fetchFreshness() {
  try {
    const response = await marketDataApi.getMarketDataFreshness()
    const item = response.items.find((f) => f.province === props.province)
    if (item) fetchedFreshness.value = item
  } catch {
    // 静默失败，不影响主流程
  }
}

function startPolling() {
  // 当外部已提供 freshnessData 时，不自行轮询
  if (props.freshnessData !== undefined) return
  fetchFreshness()
  pollTimer.value = setInterval(fetchFreshness, POLL_INTERVAL)
}

function stopPolling() {
  if (pollTimer.value) {
    clearInterval(pollTimer.value)
    pollTimer.value = null
  }
}

onMounted(startPolling)
onUnmounted(stopPolling)

// 当 freshnessData prop 变化时，动态切换轮询
watch(() => props.freshnessData, (newVal) => {
  if (newVal !== undefined) {
    stopPolling()
  }
})
</script>

<template>
  <!-- 正常：无特殊标识 -->
  <template v-if="status === 'fresh'" />

  <!-- 略过期（2-12小时）：灰色时间戳 -->
  <span v-else-if="status === 'stale'" style="color: #8c8c8c; font-size: 12px;">
    数据更新于 {{ hoursAgo }}小时前
  </span>

  <!-- 过期（12-24小时）：橙色Alert横幅 -->
  <a-alert
    v-else-if="status === 'expired'"
    type="warning"
    show-icon
    :message="`电价数据已超${Math.floor(hoursAgo ?? 0)}小时未更新`"
    style="margin-bottom: 12px;"
  />

  <!-- 严重过期（>24小时）：红色Alert横幅 -->
  <a-alert
    v-else-if="status === 'critical'"
    type="error"
    show-icon
    :message="hoursAgo != null ? `电价数据已超${Math.floor(hoursAgo)}小时未更新，报价功能受限` : '无市场数据，报价功能受限'"
    :description="'建议通过手动导入方式补充数据'"
    style="margin-bottom: 12px;"
  />
</template>
