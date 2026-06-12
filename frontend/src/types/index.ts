export interface UserInfo {
  id: number
  username: string
  email: string
  is_active: boolean
  is_admin: boolean
}

export interface AWSAccount {
  id: number
  account_id: string
  account_name: string
  default_region: string
  is_active: boolean
  last_sync_at: string | null
}

export interface Resource {
  id: number
  account_id: number
  resource_type: string
  resource_id: string
  resource_name: string | null
  region: string
  tags: string | null
  metadata_json: string | null
  status: string | null
  is_idle: boolean
  is_untagged: boolean
}

export interface TopologyNode {
  id: string
  label: string
  node_type: string
  region: string
  metadata: Record<string, any> | null
}

export interface TopologyEdge {
  source: string
  target: string
  edge_type: string
}

export interface TopologyGraph {
  nodes: TopologyNode[]
  edges: TopologyEdge[]
}

export interface Certificate {
  id: number
  account_id: number
  certificate_arn: string
  domain_name: string
  san_names: string | null
  status: string
  not_before: string | null
  not_after: string
  in_use_by: string | null
  is_orphan: boolean
  alert_level: string | null
  region: string
}

export interface CertAlertSummary {
  critical: Certificate[]
  warning: Certificate[]
  info: Certificate[]
}

export interface MetricDataPoint {
  timestamp: string
  value: number
}

export interface MetricResponse {
  metric_key: string
  resource_arn: string
  data_points: MetricDataPoint[]
}

export interface ResourceSummary {
  resource_type: string
  count: number
  idle_count: number
  untagged_count: number
}
