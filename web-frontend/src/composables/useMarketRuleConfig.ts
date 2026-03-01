import { ref, reactive } from 'vue'
import { message } from 'ant-design-vue'
import { marketRuleApi } from '@/api/marketRule'
import type {
  MarketRuleRead,
  MarketRuleCreate,
  DeviationFormulaType,
  SettlementMethod,
  SteppedStep,
} from '@/types/marketRule'
import { stationProvinceOptions } from '@/constants/provinces'
import { getErrorMessage } from '@/api/errors'

export interface MarketRuleFormData {
  price_cap_upper: number | null
  price_cap_lower: number | null
  settlement_method: SettlementMethod
  deviation_formula_type: DeviationFormulaType
  exemption_ratio: number | null
  base_rate: number | null
  bandwidth_percent: number | null
  penalty_rate: number | null
  steps: SteppedStep[]
}

function createEmptyFormData(): MarketRuleFormData {
  return {
    price_cap_upper: null,
    price_cap_lower: null,
    settlement_method: 'spot',
    deviation_formula_type: 'stepped',
    exemption_ratio: null,
    base_rate: null,
    bandwidth_percent: null,
    penalty_rate: null,
    steps: [{ lower: 0.03, upper: 0.05, rate: 0.5 }],
  }
}

function formDataToCreatePayload(form: MarketRuleFormData): MarketRuleCreate {
  let deviation_formula_params: Record<string, unknown> = {}

  if (form.deviation_formula_type === 'stepped') {
    deviation_formula_params = {
      exemption_ratio: form.exemption_ratio,
      steps: form.steps,
    }
  } else if (form.deviation_formula_type === 'proportional') {
    deviation_formula_params = {
      exemption_ratio: form.exemption_ratio,
      base_rate: form.base_rate,
    }
  } else if (form.deviation_formula_type === 'bandwidth') {
    deviation_formula_params = {
      bandwidth_percent: form.bandwidth_percent,
      penalty_rate: form.penalty_rate,
    }
  }

  return {
    price_cap_upper: form.price_cap_upper ?? 0,
    price_cap_lower: form.price_cap_lower ?? 0,
    settlement_method: form.settlement_method,
    deviation_formula_type: form.deviation_formula_type,
    deviation_formula_params,
  }
}

function ruleToFormData(rule: MarketRuleRead): MarketRuleFormData {
  const form = createEmptyFormData()
  form.price_cap_upper = rule.price_cap_upper
  form.price_cap_lower = rule.price_cap_lower
  form.settlement_method = rule.settlement_method
  form.deviation_formula_type = rule.deviation_formula_type

  const params = rule.deviation_formula_params as Record<string, unknown>
  if (rule.deviation_formula_type === 'stepped') {
    form.exemption_ratio = params.exemption_ratio as number
    form.steps = (params.steps as SteppedStep[]) || []
  } else if (rule.deviation_formula_type === 'proportional') {
    form.exemption_ratio = params.exemption_ratio as number
    form.base_rate = params.base_rate as number
  } else if (rule.deviation_formula_type === 'bandwidth') {
    form.bandwidth_percent = params.bandwidth_percent as number
    form.penalty_rate = params.penalty_rate as number
  }

  return form
}

export function useMarketRuleConfig() {
  const rules = ref<MarketRuleRead[]>([])
  const selectedProvince = ref<string | null>(null)
  const isLoading = ref(false)
  const isSaving = ref(false)
  const formData = reactive<MarketRuleFormData>(createEmptyFormData())

  const configuredProvinces = ref<Set<string>>(new Set())

  const provinceList = stationProvinceOptions.map((p) => ({
    label: p.label,
    value: p.value,
    configured: false,
  }))

  async function loadRules() {
    isLoading.value = true
    try {
      rules.value = await marketRuleApi.listMarketRules()
      configuredProvinces.value = new Set(rules.value.map((r) => r.province))
    } catch (e) {
      message.error(getErrorMessage(e, '操作失败，请稍后重试'))
    } finally {
      isLoading.value = false
    }
  }

  let _selectProvinceVersion = 0

  async function selectProvince(province: string) {
    selectedProvince.value = province
    const existingRule = rules.value.find((r) => r.province === province)

    if (existingRule) {
      Object.assign(formData, ruleToFormData(existingRule))
    } else {
      // 尝试加载默认参数（带版本号防止竞态）
      const version = ++_selectProvinceVersion
      try {
        const defaults = await marketRuleApi.getProvinceDefaults(province)
        if (version !== _selectProvinceVersion) return
        if (defaults && Object.keys(defaults).length > 0) {
          const defaultForm = createEmptyFormData()
          defaultForm.price_cap_upper = defaults.price_cap_upper as number
          defaultForm.price_cap_lower = defaults.price_cap_lower as number
          defaultForm.settlement_method = (defaults.settlement_method as SettlementMethod) || 'spot'
          defaultForm.deviation_formula_type = (defaults.deviation_formula_type as DeviationFormulaType) || 'stepped'

          const params = defaults.deviation_formula_params as Record<string, unknown> | undefined
          if (params) {
            if (defaultForm.deviation_formula_type === 'stepped') {
              defaultForm.exemption_ratio = params.exemption_ratio as number
              defaultForm.steps = (params.steps as SteppedStep[]) || []
            } else if (defaultForm.deviation_formula_type === 'proportional') {
              defaultForm.exemption_ratio = params.exemption_ratio as number
              defaultForm.base_rate = params.base_rate as number
            } else if (defaultForm.deviation_formula_type === 'bandwidth') {
              defaultForm.bandwidth_percent = params.bandwidth_percent as number
              defaultForm.penalty_rate = params.penalty_rate as number
            }
          }
          Object.assign(formData, defaultForm)
        } else {
          if (version === _selectProvinceVersion) Object.assign(formData, createEmptyFormData())
        }
      } catch {
        if (version === _selectProvinceVersion) Object.assign(formData, createEmptyFormData())
      }
    }
  }

  async function saveRule() {
    if (!selectedProvince.value) {
      message.warning('请先选择省份')
      return
    }

    if (formData.price_cap_upper === null || formData.price_cap_lower === null) {
      message.warning('请填写限价范围')
      return
    }

    if (formData.price_cap_upper <= formData.price_cap_lower) {
      message.warning('最高限价必须大于最低限价')
      return
    }

    isSaving.value = true
    try {
      const payload = formDataToCreatePayload(formData)
      await marketRuleApi.upsertMarketRule(selectedProvince.value, payload)
      message.success('市场规则保存成功')
      await loadRules()
    } catch (e) {
      message.error(getErrorMessage(e, '操作失败，请稍后重试'))
    } finally {
      isSaving.value = false
    }
  }

  function resetForm() {
    if (selectedProvince.value) {
      selectProvince(selectedProvince.value)
    } else {
      Object.assign(formData, createEmptyFormData())
    }
  }

  function addStep() {
    const lastStep = formData.steps[formData.steps.length - 1]
    formData.steps.push({
      lower: lastStep ? lastStep.upper : 0,
      upper: 1.0,
      rate: 1.0,
    })
  }

  function removeStep(index: number) {
    if (formData.steps.length > 1) {
      formData.steps.splice(index, 1)
    }
  }

  return {
    rules,
    selectedProvince,
    isLoading,
    isSaving,
    formData,
    configuredProvinces,
    provinceList,
    loadRules,
    selectProvince,
    saveRule,
    resetForm,
    addStep,
    removeStep,
  }
}
