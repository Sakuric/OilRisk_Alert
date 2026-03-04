import http from './index'

export interface LlmConfigData {
  providerName: string
  apiUrl: string
  apiKey: string
  model: string
}

export function getLlmConfig() {
  return http.get<{ data: LlmConfigData }>('/api/config/llm')
}

export function updateLlmConfig(config: {
  providerName: string
  apiUrl: string
  apiKey: string
  model: string
}) {
  return http.put<{ data: LlmConfigData }>('/api/config/llm', config)
}
