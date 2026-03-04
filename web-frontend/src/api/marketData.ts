import apiClient from './client'
import type {
  MarketClearingPriceListResponse,
  MarketDataFetchResult,
  MarketDataFreshnessListResponse,
  MarketDataSource,
  MarketDataSourceCreate,
  MarketDataSourceListResponse,
  MarketDataSourceUpdate,
} from '@/types/marketData'

export const marketDataApi = {
  async getMarketData(params: {
    province?: string
    trading_date?: string
    page?: number
    page_size?: number
  }): Promise<MarketClearingPriceListResponse> {
    const response = await apiClient.get<MarketClearingPriceListResponse>('/market-data', {
      params,
    })
    return response.data
  },

  async getMarketDataFreshness(): Promise<MarketDataFreshnessListResponse> {
    const response = await apiClient.get<MarketDataFreshnessListResponse>(
      '/market-data/freshness',
    )
    return response.data
  },

  async triggerFetch(
    province: string,
    tradingDate: string,
  ): Promise<MarketDataFetchResult> {
    const response = await apiClient.post<MarketDataFetchResult>('/market-data/fetch', null, {
      params: { province, trading_date: tradingDate },
    })
    return response.data
  },

  async uploadMarketData(
    file: File,
    province: string,
  ): Promise<MarketDataFetchResult> {
    const formData = new FormData()
    formData.append('file', file)
    const response = await apiClient.post<MarketDataFetchResult>(
      '/market-data/upload',
      formData,
      { params: { province }, timeout: 120000 },
    )
    return response.data
  },

  async getDataSources(params?: {
    page?: number
    page_size?: number
    is_active?: boolean
  }): Promise<MarketDataSourceListResponse> {
    const response = await apiClient.get<MarketDataSourceListResponse>('/market-data/sources', {
      params,
    })
    return response.data
  },

  async createDataSource(data: MarketDataSourceCreate): Promise<MarketDataSource> {
    const response = await apiClient.post<MarketDataSource>('/market-data/sources', data)
    return response.data
  },

  async updateDataSource(
    sourceId: string,
    data: MarketDataSourceUpdate,
  ): Promise<MarketDataSource> {
    const response = await apiClient.put<MarketDataSource>(
      `/market-data/sources/${sourceId}`,
      data,
    )
    return response.data
  },

  async deleteDataSource(sourceId: string): Promise<void> {
    await apiClient.delete(`/market-data/sources/${sourceId}`)
  },
}
