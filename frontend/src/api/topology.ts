import api from './index'
import type { TopologyGraph, TopologyNode } from '@/types'

export function getTopologyGraph(accountId: number) {
  return api.get<TopologyGraph>(`/topology/${accountId}/graph`)
}

export function getNodeContext(accountId: number, nodeType: string, nodeId: string) {
  return api.get(`/topology/${accountId}/nodes/by-node-id`, {
    params: { node_type: nodeType, node_id: nodeId }
  })
}

export function getNodeHealth(accountId: number, nodeDbId: number) {
  return api.get(`/topology/${accountId}/nodes/${nodeDbId}/health`)
}

export function reverseLookup(accountId: number, domain: string) {
  return api.get(`/topology/${accountId}/reverse-lookup`, { params: { domain } })
}
