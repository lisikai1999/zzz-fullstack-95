import api from './index'
import type { Resource, ResourceSummary } from '@/types'

export function getResources(params: Record<string, any> = {}) {
  return api.get<Resource[]>('/resources/', { params })
}

export function getResourceSummary(params: Record<string, any> = {}) {
  return api.get<ResourceSummary[]>('/resources/summary', { params })
}
