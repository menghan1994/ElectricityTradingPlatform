import apiClient from './client'
import type { DeviationTemplate, MarketRuleCreate, MarketRuleRead } from '@/types/marketRule'

export const marketRuleApi = {
  async listMarketRules(): Promise<MarketRuleRead[]> {
    const response = await apiClient.get<MarketRuleRead[]>('/market-rules')
    return response.data
  },

  async getMarketRule(province: string): Promise<MarketRuleRead> {
    const response = await apiClient.get<MarketRuleRead>(`/market-rules/${province}`)
    return response.data
  },

  async upsertMarketRule(province: string, data: MarketRuleCreate): Promise<MarketRuleRead> {
    const response = await apiClient.put<MarketRuleRead>(`/market-rules/${province}`, data)
    return response.data
  },

  async deleteMarketRule(province: string): Promise<void> {
    await apiClient.delete(`/market-rules/${province}`)
  },

  async getDeviationTemplates(): Promise<DeviationTemplate[]> {
    const response = await apiClient.get<DeviationTemplate[]>('/market-rules/templates')
    return response.data
  },

  async getProvinceDefaults(province: string): Promise<Record<string, unknown>> {
    const response = await apiClient.get<Record<string, unknown>>(`/market-rules/defaults/${province}`)
    return response.data
  },
}
