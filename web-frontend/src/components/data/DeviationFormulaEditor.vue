<script setup lang="ts">
import type { DeviationFormulaType, SteppedStep } from '@/types/marketRule'

const props = defineProps<{
  formulaType: DeviationFormulaType
  exemptionRatio: number | null
  baseRate: number | null
  bandwidthPercent: number | null
  penaltyRate: number | null
  steps: SteppedStep[]
}>()

const emit = defineEmits<{
  'update:exemptionRatio': [value: number | null]
  'update:baseRate': [value: number | null]
  'update:bandwidthPercent': [value: number | null]
  'update:penaltyRate': [value: number | null]
  'update:steps': [value: SteppedStep[]]
  addStep: []
  removeStep: [index: number]
}>()

function updateStepField(index: number, field: keyof SteppedStep, value: number) {
  const newSteps = [...props.steps]
  newSteps[index] = { ...newSteps[index], [field]: value }
  emit('update:steps', newSteps)
}
</script>

<template>
  <a-card size="small" title="偏差考核参数">
    <!-- 阶梯式 -->
    <template v-if="formulaType === 'stepped'">
      <a-form-item label="免考核带" name="exemption_ratio" :rules="[{ required: true, message: '请输入免考核比例' }]">
        <a-input-number
          :value="exemptionRatio"
          :min="0"
          :max="1"
          :step="0.01"
          style="width: 200px"
          @update:value="emit('update:exemptionRatio', $event)"
        />
        <span style="margin-left: 8px; color: #999;">取值 0~1，如 0.03 表示 3%</span>
      </a-form-item>

      <div v-for="(step, index) in steps" :key="index" style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
        <span>阶梯 {{ index + 1 }}:</span>
        <a-input-number
          :value="step.lower"
          :min="0"
          :max="1"
          :step="0.01"
          style="width: 100px"
          placeholder="下限"
          @update:value="updateStepField(index, 'lower', $event)"
        />
        <span>~</span>
        <a-input-number
          :value="step.upper"
          :min="0"
          :max="1"
          :step="0.01"
          style="width: 100px"
          placeholder="上限"
          @update:value="updateStepField(index, 'upper', $event)"
        />
        <span>, 倍率:</span>
        <a-input-number
          :value="step.rate"
          :min="0"
          :step="0.1"
          style="width: 100px"
          @update:value="updateStepField(index, 'rate', $event)"
        />
        <a-popconfirm
          v-if="steps.length > 1"
          title="确认删除此阶梯？"
          @confirm="emit('removeStep', index)"
        >
          <a-button type="text" danger size="small">删除</a-button>
        </a-popconfirm>
      </div>

      <a-button type="dashed" size="small" @click="emit('addStep')">+ 添加阶梯</a-button>
    </template>

    <!-- 比例式 -->
    <template v-else-if="formulaType === 'proportional'">
      <a-form-item label="免考核带" name="exemption_ratio" :rules="[{ required: true, message: '请输入免考核比例' }]">
        <a-input-number
          :value="exemptionRatio"
          :min="0"
          :max="1"
          :step="0.01"
          style="width: 200px"
          @update:value="emit('update:exemptionRatio', $event)"
        />
      </a-form-item>
      <a-form-item label="基础倍率" name="base_rate" :rules="[{ required: true, message: '请输入基础倍率' }]">
        <a-input-number
          :value="baseRate"
          :min="0"
          :step="0.1"
          style="width: 200px"
          @update:value="emit('update:baseRate', $event)"
        />
      </a-form-item>
    </template>

    <!-- 带宽式 -->
    <template v-else-if="formulaType === 'bandwidth'">
      <a-form-item label="带宽百分比" name="bandwidth_percent" :rules="[{ required: true, message: '请输入带宽百分比' }]">
        <a-input-number
          :value="bandwidthPercent"
          :min="0"
          :max="1"
          :step="0.01"
          style="width: 200px"
          @update:value="emit('update:bandwidthPercent', $event)"
        />
      </a-form-item>
      <a-form-item label="罚金系数" name="penalty_rate" :rules="[{ required: true, message: '请输入罚金系数' }]">
        <a-input-number
          :value="penaltyRate"
          :min="0"
          :step="0.1"
          style="width: 200px"
          @update:value="emit('update:penaltyRate', $event)"
        />
      </a-form-item>
    </template>
  </a-card>
</template>
