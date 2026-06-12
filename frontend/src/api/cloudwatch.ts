import api from './index'
import type { MetricResponse } from '@/types'

export function getMetrics(params: {
  account_id: number
  resource_id: string
  resource_type: string
  metric_key: string
  region: string
  period?: number
  hours?: number
}) {
  return api.get<MetricResponse>('/cloudwatch/metrics', { params })
}

export function getLogs(params: {
  account_id: number
  log_group: string
  region: string
  filter_pattern?: string
  hours?: number
  limit?: number
}) {
  return api.get('/cloudwatch/logs', { params })
}

export function getConsoleUrl(params: { region: string; resource_type: string; resource_id: string }) {
  return api.get<{ url: string }>('/cloudwatch/console-url', { params })
}
