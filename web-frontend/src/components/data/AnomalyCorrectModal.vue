<script setup lang="ts">
import { ref, watch } from 'vue'
import type { ImportAnomaly } from '@/types/dataImport'

const props = defineProps<{
  visible: boolean
  anomaly: ImportAnomaly | null
}>()

const emit = defineEmits<{
  (e: 'confirm', correctedValue: string): void
  (e: 'cancel'): void
}>()

const correctedValue = ref('')
const validationError = ref('')

const anomalyTypeLabels: Record<string, string> = {
  missing: '缺失',
  format_error: '格式错误',
  out_of_range: '超范围',
  duplicate: '重复',
}

const fieldHints: Record<string, string> = {
  clearing_price: '请输入正确的出清价格（元/MWh）',
  period: '请输入正确的时段号（1-96）',
  trading_date: '请输入正确的交易日期（YYYY-MM-DD）',
}

watch(
  () => props.visible,
  (newVal) => {
    if (newVal) {
      correctedValue.value = ''
      validationError.value = ''
    }
  },
)

function handleConfirm(): void {
  if (!correctedValue.value.trim()) {
    validationError.value = '修正值不能为空'
    return
  }
  validationError.value = ''
  emit('confirm', correctedValue.value.trim())
}

function handleCancel(): void {
  emit('cancel')
}
</script>

<template>
  <a-modal
    :open="visible"
    title="修正异常数据"
    :ok-text="'确认修正'"
    :cancel-text="'取消'"
    @ok="handleConfirm"
    @cancel="handleCancel"
  >
    <div v-if="anomaly">
      <a-descriptions :column="1" bordered size="small" style="margin-bottom: 16px;">
        <a-descriptions-item label="行号">{{ anomaly.row_number }}</a-descriptions-item>
        <a-descriptions-item label="异常类型">
          {{ anomalyTypeLabels[anomaly.anomaly_type] || anomaly.anomaly_type }}
        </a-descriptions-item>
        <a-descriptions-item label="字段">{{ anomaly.field_name }}</a-descriptions-item>
        <a-descriptions-item label="原始值">{{ anomaly.raw_value || '-' }}</a-descriptions-item>
        <a-descriptions-item label="描述">{{ anomaly.description }}</a-descriptions-item>
      </a-descriptions>

      <a-form-item
        label="修正值"
        :validate-status="validationError ? 'error' : ''"
        :help="validationError || fieldHints[anomaly.field_name] || '请输入修正后的值'"
      >
        <a-input
          v-model:value="correctedValue"
          placeholder="请输入修正值"
          @press-enter="handleConfirm"
        />
      </a-form-item>
    </div>
  </a-modal>
</template>
