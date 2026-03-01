export type SettlementMethod = 'spot' | 'contract' | 'hybrid'
export type DeviationFormulaType = 'stepped' | 'proportional' | 'bandwidth'

export interface SteppedStep {
  lower: number
  upper: number
  rate: number
}

export interface SteppedParams {
  exemption_ratio: number
  steps: SteppedStep[]
}

export interface ProportionalParams {
  exemption_ratio: number
  base_rate: number
}

export interface BandwidthParams {
  bandwidth_percent: number
  penalty_rate: number
}

export type DeviationFormulaParams = SteppedParams | ProportionalParams | BandwidthParams

export interface MarketRuleRead {
  id: string
  province: string
  price_cap_upper: number
  price_cap_lower: number
  settlement_method: SettlementMethod
  deviation_formula_type: DeviationFormulaType
  deviation_formula_params: DeviationFormulaParams
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface MarketRuleCreate {
  price_cap_upper: number
  price_cap_lower: number
  settlement_method: SettlementMethod
  deviation_formula_type: DeviationFormulaType
  deviation_formula_params: Record<string, unknown>
}

export interface DeviationTemplate {
  province: string
  deviation_formula_type: string
  default_params: Record<string, unknown>
}

export const settlementMethodLabels: Record<SettlementMethod, string> = {
  spot: '现货结算',
  contract: '合同结算',
  hybrid: '混合结算',
}

export const deviationFormulaTypeLabels: Record<DeviationFormulaType, string> = {
  stepped: '阶梯式',
  proportional: '比例式',
  bandwidth: '带宽式',
}
