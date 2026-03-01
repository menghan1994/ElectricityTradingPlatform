import apiClient from './client'
import type { StationWizardCreate, StationWizardResponse } from '@/types/wizard'

export const wizardApi = {
  async createStationWithDevices(data: StationWizardCreate): Promise<StationWizardResponse> {
    const response = await apiClient.post<StationWizardResponse>('/wizard/stations', data)
    return response.data
  },
}
