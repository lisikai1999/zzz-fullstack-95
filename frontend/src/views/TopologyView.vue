<template>
  <div class="ops-console">
    <!-- Top bar: account selector + domain reverse-lookup -->
    <div class="console-toolbar">
      <div class="toolbar-left">
        <AccountSelector v-model="selectedAccount" style="width: 280px" />
        <el-button type="primary" :icon="Refresh" @click="loadGraph" :loading="graphLoading" :disabled="!selectedAccount">
          加载拓扑
        </el-button>
      </div>
      <div class="toolbar-right">
        <el-input
          v-model="domainQuery"
          placeholder="反查域名，如 api.example.com"
          clearable
          style="width: 300px"
          @keyup.enter="handleReverseLookup"
        >
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-button @click="handleReverseLookup" :loading="lookupLoading" :disabled="!selectedAccount || !domainQuery">
          反查链路
        </el-button>
      </div>
    </div>

    <!-- Main area: graph left, detail panel right -->
    <div class="console-body">
      <div class="graph-area" :class="{ 'with-panel': !!selectedNode }">
        <div ref="graphContainer" class="graph-canvas"></div>
        <div v-if="!graphData && !graphLoading" class="graph-empty">
          <el-empty description="选择账号后点击「加载拓扑」查看服务链路" />
        </div>
      </div>

      <!-- Right panel: Node detail + auto metrics + log links -->
      <transition name="slide">
        <div v-if="selectedNode" class="detail-panel">
          <div class="panel-header">
            <div class="panel-title">
              <el-tag :color="NODE_COLORS[selectedNode.node_type]" effect="dark" size="small" style="color:#fff; border:none">
                {{ NODE_LABELS[selectedNode.node_type] || selectedNode.node_type }}
              </el-tag>
              <span class="node-name">{{ selectedNode.label }}</span>
            </div>
            <el-button text @click="selectedNode = null"><el-icon><Close /></el-icon></el-button>
          </div>

          <!-- Basic info -->
          <el-descriptions :column="1" border size="small" class="section">
            <el-descriptions-item label="区域">{{ selectedNode.region }}</el-descriptions-item>
            <el-descriptions-item v-for="(val, key) in selectedNode.metadata" :key="key" :label="String(key)">
              {{ val }}
            </el-descriptions-item>
          </el-descriptions>

          <!-- Health check -->
          <div class="section">
            <div class="section-header">
              <span>健康状态</span>
              <el-button size="small" text @click="fetchHealth" :loading="healthLoading">
                <el-icon><Refresh /></el-icon> 检查
              </el-button>
            </div>
            <div v-if="healthData">
              <el-tag :type="healthData.health_status === 'healthy' ? 'success' : 'warning'" size="small">
                {{ healthData.health_status }}
              </el-tag>
              <el-descriptions v-if="healthData.details" :column="1" size="small" border style="margin-top:8px">
                <el-descriptions-item v-for="(v, k) in healthData.details" :key="k" :label="String(k)">{{ v }}</el-descriptions-item>
              </el-descriptions>
            </div>
          </div>

          <!-- Upstream/Downstream -->
          <div v-if="nodeContext" class="section">
            <div v-if="nodeContext.upstream.length" class="dep-list">
              <span class="dep-label">上游:</span>
              <el-tag v-for="u in nodeContext.upstream" :key="u.id" size="small" class="dep-tag" @click="selectNodeById(u.id)">
                {{ u.name }}
              </el-tag>
            </div>
            <div v-if="nodeContext.downstream.length" class="dep-list">
              <span class="dep-label">下游:</span>
              <el-tag v-for="d in nodeContext.downstream" :key="d.id" size="small" type="success" class="dep-tag" @click="selectNodeById(d.id)">
                {{ d.name }}
              </el-tag>
            </div>
          </div>

          <!-- Auto-loaded Metrics -->
          <div v-if="nodeContext && nodeContext.metrics.length" class="section">
            <div class="section-header"><span>关键指标</span></div>
            <div v-for="metric in nodeContext.metrics" :key="metric.key" class="metric-card">
              <div class="metric-header">
                <span>{{ metric.label }}</span>
                <el-button size="small" text @click="fetchMetric(metric)" :loading="metricLoading[metric.key]">
                  <el-icon><DataLine /></el-icon>
                </el-button>
              </div>
              <div v-if="metricData[metric.key]" class="metric-chart">
                <div class="sparkline">
                  <div
                    v-for="(dp, idx) in metricData[metric.key].slice(-30)"
                    :key="idx"
                    class="spark-bar"
                    :style="{ height: sparkHeight(dp.value, metric.key) + '%' }"
                    :title="`${dp.timestamp}: ${dp.value.toFixed(2)}`"
                  ></div>
                </div>
                <div class="metric-summary">
                  最新: <strong>{{ metricData[metric.key].slice(-1)[0]?.value.toFixed(2) || '-' }}</strong>
                </div>
              </div>
            </div>
          </div>

          <!-- Log group links -->
          <div v-if="nodeContext && nodeContext.log_groups.length" class="section">
            <div class="section-header"><span>日志</span></div>
            <div v-for="lg in nodeContext.log_groups" :key="lg.name" class="log-link">
              <el-button text type="primary" @click="openLogs(lg)">
                <el-icon><Document /></el-icon> {{ lg.label }}
              </el-button>
            </div>
          </div>

          <!-- Console link -->
          <div v-if="nodeContext" class="section">
            <el-button type="primary" plain size="small" @click="openConsole">
              <el-icon><Link /></el-icon> 在 AWS 控制台查看
            </el-button>
          </div>
        </div>
      </transition>
    </div>

    <!-- Log viewer drawer -->
    <el-drawer v-model="logDrawerVisible" :title="logDrawerTitle" size="50%">
      <div v-loading="logLoading">
        <div v-if="logEvents.length === 0 && !logLoading" class="log-empty">暂无日志</div>
        <div v-for="(evt, idx) in logEvents" :key="idx" class="log-event">
          <span class="log-ts">{{ evt.timestamp }}</span>
          <span class="log-msg">{{ evt.message }}</span>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onBeforeUnmount, reactive } from 'vue'
import { Graph } from '@antv/g6'
import { Refresh, Search, Close, DataLine, Document, Link } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import AccountSelector from '@/components/common/AccountSelector.vue'
import { getTopologyGraph, reverseLookup } from '@/api/topology'
import api from '@/api/index'
import type { TopologyNode, TopologyGraph } from '@/types'

const selectedAccount = ref<number | null>(null)
const graphContainer = ref<HTMLElement>()
const graphLoading = ref(false)
const lookupLoading = ref(false)
const domainQuery = ref('')
const selectedNode = ref<TopologyNode | null>(null)
const graphData = ref<TopologyGraph | null>(null)
const healthLoading = ref(false)
const healthData = ref<any>(null)
const nodeContext = ref<any>(null)
const metricLoading = reactive<Record<string, boolean>>({})
const metricData = reactive<Record<string, any[]>>({})
const logDrawerVisible = ref(false)
const logDrawerTitle = ref('')
const logLoading = ref(false)
const logEvents = ref<any[]>([])
let graph: any = null
let allNodes: TopologyNode[] = []

const NODE_COLORS: Record<string, string> = {
  route53: '#67c23a',
  alb: '#409eff',
  target_group: '#909399',
  ecs_service: '#e6a23c',
  ec2: '#f56c6c',
  rds: '#9b59b6',
  elasticache: '#1abc9c',
}

const NODE_LABELS: Record<string, string> = {
  route53: 'Route53',
  alb: 'ALB',
  target_group: 'Target Group',
  ecs_service: 'ECS Service',
  ec2: 'EC2',
  rds: 'RDS',
  elasticache: 'ElastiCache',
}

async function loadGraph() {
  if (!selectedAccount.value) return
  graphLoading.value = true
  selectedNode.value = null
  try {
    const res = await getTopologyGraph(selectedAccount.value)
    graphData.value = res.data
    allNodes = res.data.nodes
    renderGraph(res.data.nodes, res.data.edges)
  } catch (e: any) {
    ElMessage.error('加载拓扑失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    graphLoading.value = false
  }
}

function renderGraph(nodes: TopologyNode[], edges: any[]) {
  if (graph) { graph.destroy(); graph = null }
  if (!graphContainer.value || nodes.length === 0) return

  const g6Nodes = nodes.map((n) => ({
    id: n.id,
    data: { label: n.label, nodeType: n.node_type, region: n.region, metadata: n.metadata },
  }))
  const g6Edges = edges.map((e, i) => ({
    id: `edge-${i}`,
    source: e.source,
    target: e.target,
    data: { edgeType: e.edge_type },
  }))

  graph = new Graph({
    container: graphContainer.value,
    width: graphContainer.value.clientWidth,
    height: graphContainer.value.clientHeight,
    data: { nodes: g6Nodes, edges: g6Edges },
    layout: { type: 'dagre', rankdir: 'TB', nodesep: 60, ranksep: 80 },
    node: {
      style: (model: any) => ({
        size: 40,
        fill: NODE_COLORS[model.data?.nodeType] || '#409eff',
        stroke: '#fff',
        lineWidth: 2,
        labelText: model.data?.label || '',
        labelPlacement: 'bottom',
        labelFontSize: 11,
        labelFill: '#333',
      }),
    },
    edge: {
      style: { stroke: '#c0c4cc', lineWidth: 1.5, endArrow: true },
    },
    behaviors: ['drag-canvas', 'zoom-canvas', 'click-select'],
  })

  graph.on('node:click', (evt: any) => {
    const nodeId = evt.itemId || evt.target?.id
    const nodeData = allNodes.find((n) => n.id === nodeId)
    if (nodeData) selectNode(nodeData)
  })

  graph.render()
}

async function selectNode(node: TopologyNode) {
  selectedNode.value = node
  healthData.value = null
  nodeContext.value = null
  Object.keys(metricData).forEach(k => delete metricData[k])

  // Auto-fetch context (metrics config, log groups, upstream/downstream)
  try {
    const nodeDbId = node.id.split(':').slice(1).join(':')
    // Find the DB id by searching topology_nodes
    const res = await api.get(`/topology/${selectedAccount.value}/nodes/by-node-id`, {
      params: { node_type: node.node_type, node_id: nodeDbId }
    })
    nodeContext.value = res.data

    // Auto-load first metric
    if (nodeContext.value.metrics.length > 0) {
      fetchMetric(nodeContext.value.metrics[0])
    }
  } catch {
    // Fallback: try using the node directly
    nodeContext.value = { metrics: [], log_groups: [], console_url: '', upstream: [], downstream: [] }
  }
}

function selectNodeById(dbId: number) {
  // Navigate graph to node by DB id
  if (nodeContext.value) {
    api.get(`/topology/${selectedAccount.value}/nodes/${dbId}`).then(res => {
      const n = res.data
      const found = allNodes.find(an => an.node_type === n.node_type && an.id.includes(n.id))
      if (found) selectNode(found)
    })
  }
}

async function fetchHealth() {
  if (!selectedNode.value || !nodeContext.value) return
  healthLoading.value = true
  try {
    const res = await api.get(`/topology/${selectedAccount.value}/nodes/${nodeContext.value.node_id}/health`)
    healthData.value = res.data
  } catch {
    healthData.value = { health_status: 'error', details: { error: '检查失败' } }
  } finally {
    healthLoading.value = false
  }
}

async function fetchMetric(metric: any) {
  if (!nodeContext.value) return
  metricLoading[metric.key] = true
  try {
    const res = await api.post('/cloudwatch/query-metric', {
      account_id: selectedAccount.value,
      region: nodeContext.value.region,
      metric_key: metric.key,
      dimensions: metric.dimensions,
      period: 300,
      hours: 3,
    })
    metricData[metric.key] = res.data.data_points
  } catch {
    metricData[metric.key] = []
  } finally {
    metricLoading[metric.key] = false
  }
}

function sparkHeight(value: number, key: string): number {
  const points = metricData[key] || []
  if (points.length === 0) return 0
  const max = Math.max(...points.map((p: any) => p.value), 1)
  return Math.max((value / max) * 100, 2)
}

async function openLogs(lg: any) {
  if (!nodeContext.value) return
  logDrawerVisible.value = true
  logDrawerTitle.value = lg.label
  logLoading.value = true
  logEvents.value = []
  try {
    const res = await api.get('/cloudwatch/logs', {
      params: {
        account_id: selectedAccount.value,
        log_group: lg.name,
        region: nodeContext.value.region,
        hours: 1,
        limit: 200,
      }
    })
    logEvents.value = res.data.events
  } catch (e: any) {
    logEvents.value = []
    ElMessage.warning('日志获取失败，可能日志组不存在: ' + (e.response?.data?.detail || ''))
  } finally {
    logLoading.value = false
  }
}

function openConsole() {
  if (nodeContext.value?.console_url) {
    window.open(nodeContext.value.console_url, '_blank')
  }
}

async function handleReverseLookup() {
  if (!selectedAccount.value || !domainQuery.value) return
  lookupLoading.value = true
  selectedNode.value = null
  try {
    const res = await reverseLookup(selectedAccount.value, domainQuery.value)
    graphData.value = { nodes: res.data.chain, edges: res.data.edges }
    allNodes = res.data.chain
    renderGraph(res.data.chain, res.data.edges)
    ElMessage.success(`域名 "${domainQuery.value}" 链路: ${res.data.chain.length} 个节点`)
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '反查失败')
  } finally {
    lookupLoading.value = false
  }
}

watch(selectedAccount, () => {
  if (selectedAccount.value) loadGraph()
})

onBeforeUnmount(() => { if (graph) graph.destroy() })
</script>

<style scoped>
.ops-console {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 120px);
  gap: 12px;
}
.console-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-shrink: 0;
}
.toolbar-left, .toolbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}
.console-body {
  flex: 1;
  display: flex;
  gap: 12px;
  min-height: 0;
  overflow: hidden;
}
.graph-area {
  flex: 1;
  position: relative;
  border: 1px solid #ebeef5;
  border-radius: 6px;
  background: #fafbfc;
  transition: all 0.3s;
}
.graph-area.with-panel {
  flex: 0 0 60%;
}
.graph-canvas {
  width: 100%;
  height: 100%;
}
.graph-empty {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}
.detail-panel {
  width: 40%;
  max-width: 450px;
  overflow-y: auto;
  border: 1px solid #ebeef5;
  border-radius: 6px;
  background: #fff;
  padding: 16px;
}
.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}
.panel-title {
  display: flex;
  align-items: center;
  gap: 8px;
}
.node-name {
  font-weight: 600;
  font-size: 15px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 250px;
}
.section {
  margin-top: 16px;
}
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
  font-size: 13px;
  margin-bottom: 8px;
  color: #303133;
}
.dep-list {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
}
.dep-label {
  font-size: 12px;
  color: #909399;
}
.dep-tag {
  cursor: pointer;
}
.metric-card {
  border: 1px solid #ebeef5;
  border-radius: 4px;
  padding: 8px 12px;
  margin-bottom: 8px;
}
.metric-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
  font-weight: 500;
}
.metric-chart {
  margin-top: 6px;
}
.sparkline {
  display: flex;
  align-items: flex-end;
  gap: 1px;
  height: 40px;
  padding: 2px 0;
}
.spark-bar {
  flex: 1;
  background: #409eff;
  border-radius: 1px;
  min-width: 2px;
  transition: height 0.2s;
}
.metric-summary {
  font-size: 12px;
  color: #606266;
  margin-top: 4px;
}
.log-link {
  margin-bottom: 4px;
}
.log-event {
  display: flex;
  gap: 12px;
  font-size: 12px;
  font-family: monospace;
  padding: 4px 0;
  border-bottom: 1px solid #f0f0f0;
}
.log-ts {
  color: #909399;
  white-space: nowrap;
  flex-shrink: 0;
}
.log-msg {
  word-break: break-all;
}
.log-empty {
  text-align: center;
  color: #909399;
  padding: 40px;
}

.slide-enter-active, .slide-leave-active {
  transition: all 0.3s ease;
}
.slide-enter-from, .slide-leave-to {
  transform: translateX(20px);
  opacity: 0;
}
</style>
