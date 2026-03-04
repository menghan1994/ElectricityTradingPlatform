<script setup lang="ts">
import type { EmsFormat } from '@/types/dataImport'

defineProps<{
  modelValue: EmsFormat
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: EmsFormat): void
}>()

const emsFormatOptions: { value: EmsFormat; label: string }[] = [
  { value: 'standard', label: '标准格式' },
  { value: 'sungrow', label: '阳光电源' },
  { value: 'huawei', label: '华为' },
  { value: 'catl', label: '宁德时代' },
]
</script>

<template>
  <div style="display: flex; align-items: center; gap: 8px;">
    <span>EMS 格式:</span>
    <a-select
      :value="modelValue"
      style="width: 200px;"
      @update:value="emit('update:modelValue', $event)"
    >
      <a-select-option
        v-for="opt in emsFormatOptions"
        :key="opt.value"
        :value="opt.value"
      >
        {{ opt.label }}
      </a-select-option>
    </a-select>
  </div>
</template>
