import apiClient from './client'
import type {
  ConnectionTestResult,
  FetchResult,
  PowerPredictionListResponse,
  PredictionModel,
  PredictionModelCreate,
  PredictionModelListResponse,
  PredictionModelStatusListResponse,
  PredictionModelUpdate,
} from '@/types/prediction'

export const predictionApi = {
  async getPredictionModels(params?: {
    station_id?: string
    page?: number
    page_size?: number
  }): Promise<PredictionModelListResponse> {
    const response = await apiClient.get<PredictionModelListResponse>(
      '/prediction-models',
      { params },
    )
    return response.data
  },

  async createPredictionModel(data: PredictionModelCreate): Promise<PredictionModel> {
    const response = await apiClient.post<PredictionModel>('/prediction-models', data)
    return response.data
  },

  async updatePredictionModel(
    modelId: string,
    data: PredictionModelUpdate,
  ): Promise<PredictionModel> {
    const response = await apiClient.put<PredictionModel>(
      `/prediction-models/${modelId}`,
      data,
    )
    return response.data
  },

  async deletePredictionModel(modelId: string): Promise<void> {
    await apiClient.delete(`/prediction-models/${modelId}`)
  },

  async testConnection(modelId: string): Promise<ConnectionTestResult> {
    const response = await apiClient.post<ConnectionTestResult>(
      `/prediction-models/${modelId}/test-connection`,
    )
    return response.data
  },

  async getModelStatuses(): Promise<PredictionModelStatusListResponse> {
    const response = await apiClient.get<PredictionModelStatusListResponse>(
      '/prediction-models/status',
    )
    return response.data
  },

  async triggerFetch(modelId: string, predictionDate?: string): Promise<FetchResult> {
    const response = await apiClient.post<FetchResult>(
      `/prediction-models/${modelId}/fetch`,
      predictionDate ? { prediction_date: predictionDate } : {},
    )
    return response.data
  },

  async getPredictions(modelId: string, predictionDate: string): Promise<PowerPredictionListResponse> {
    const response = await apiClient.get<PowerPredictionListResponse>(
      `/prediction-models/${modelId}/predictions`,
      { params: { prediction_date: predictionDate } },
    )
    return response.data
  },

  async getStationPredictions(
    stationId: string,
    predictionDate: string,
    modelId?: string,
  ): Promise<PowerPredictionListResponse> {
    const response = await apiClient.get<PowerPredictionListResponse>(
      `/stations/${stationId}/predictions`,
      { params: { prediction_date: predictionDate, model_id: modelId } },
    )
    return response.data
  },
}
