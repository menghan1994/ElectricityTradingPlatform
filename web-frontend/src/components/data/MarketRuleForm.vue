<script setup lang="ts">
import { ref } from 'vue'
import type { FormInstance } from 'ant-design-vue'
import type { MarketRuleFormData } from '@/composables/useMarketRuleConfig'
import type { DeviationFormulaType, SettlementMethod } from '@/types/marketRule'
import { settlementMethodLabels, deviationFormulaTypeLabels } from '@/types/marketRule'
import DeviationFormulaEditor from './DeviationFormulaEditor.vue'

const props = defineProps<{
  formData: MarketRuleFormData
  isSaving: boolean
  province: string | null
}>()

const emit = defineEmits<{
  save: []
  reset: []
  addStep: []
  removeStep: [index: number]
}>()

const formRef = ref<FormInstance>()

async function handleSave() {
  try {
    await formRef.value?.validateFields()
    emit('save')
  } catch {
    // 校验失败，Ant Design 会自动显示错误信息
  }
}

defineExpose({ formRef })

const settlementOptions = Object.entries(settlementMethodLabels).map(([value, label]) => ({
  label,
  value,
}))

const formulaTypeOptions = Object.entries(deviationFormulaTypeLabels).map(([value, label]) => ({
  label,
  value,
}))
</script>

<template>
  <div v-if="!province" style="text-align: center; padding: 80px 0; color: #999;">
    请从左侧选择一个省份进行配置
  </div>

  <a-form v-else ref="formRef" :model="formData" layout="vertical">
    <a-form-item label="最高限价（元/MWh）" name="price_cap_upper" :rules="[{ required: true, message: '请输入最高限价' }]">
      <a-input-number
        :value="formData.price_cap_upper"
        :min="0"
        :step="100"
        style="width: 100%"
        placeholder="请输入最高限价"
        @update:value="formData.price_cap_upper = $event"
      />
    </a-form-item>

    <a-form-item label="最低限价（元/MWh）" name="price_cap_lower" :rules="[{ required: true, message: '请输入最低限价' }]">
      <a-input-number
        :value="formData.price_cap_lower"
        :min="0"
        :step="100"
        style="width: 100%"
        placeholder="请输入最低限价"
        @update:value="formData.price_cap_lower = $event"
      />
    </a-form-item>

    <a-form-item label="结算方式" name="settlement_method" :rules="[{ required: true, message: '请选择结算方式' }]">
      <a-select
        :value="formData.settlement_method"
        :options="settlementOptions"
        placeholder="请选择结算方式"
        @update:value="formData.settlement_method = $event as SettlementMethod"
      />
    </a-form-item>

    <a-form-item label="偏差考核公式" name="deviation_formula_type" :rules="[{ required: true, message: '请选择公式类型' }]">
      <a-select
        :value="formData.deviation_formula_type"
        :options="formulaTypeOptions"
        placeholder="请选择公式类型"
        @update:value="formData.deviation_formula_type = $event as DeviationFormulaType"
      />
    </a-form-item>

    <DeviationFormulaEditor
      :formula-type="formData.deviation_formula_type"
      :exemption-ratio="formData.exemption_ratio"
      :base-rate="formData.base_rate"
      :bandwidth-percent="formData.bandwidth_percent"
      :penalty-rate="formData.penalty_rate"
      :steps="formData.steps"
      @update:exemption-ratio="formData.exemption_ratio = $event"
      @update:base-rate="formData.base_rate = $event"
      @update:bandwidth-percent="formData.bandwidth_percent = $event"
      @update:penalty-rate="formData.penalty_rate = $event"
      @update:steps="formData.steps = $event"
      @add-step="emit('addStep')"
      @remove-step="emit('removeStep', $event)"
    />

    <div style="margin-top: 24px; display: flex; gap: 12px;">
      <a-button type="primary" :loading="isSaving" @click="handleSave">保存配置</a-button>
      <a-button @click="emit('reset')">重置</a-button>
    </div>
  </a-form>
</template>
