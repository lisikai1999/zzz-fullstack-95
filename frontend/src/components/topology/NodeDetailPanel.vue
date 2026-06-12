<template>
  <el-card class="node-panel">
    <template #header>
      <div class="panel-header">
        <el-tag :type="tagType" size="small">{{ node.node_type }}</el-tag>
        <span class="node-label">{{ node.label }}</span>
        <el-button text size="small" @click="$emit('close')">
          <el-icon><Close /></el-icon>
        </el-button>
      </div>
    </template>

    <el-descriptions :column="1" border size="small">
      <el-descriptions-item label="ID">{{ node.id }}</el-descriptions-item>
      <el-descriptions-item label="类型">{{ node.node_type }}</el-descriptions-item>
      <el-descriptions-item label="区域">{{ node.region }}</el-descriptions-item>
    </el-descriptions>

    <div v-if="node.metadata" class="metadata-section">
      <h4>详情</h4>
      <el-descriptions :column="1" border size="small">
        <el-descriptions-item v-for="(val, key) in node.metadata" :key="key" :label="String(key)">
          {{ val }}
        </el-descriptions-item>
      </el-descriptions>
    </div>

    <div class="actions-section">
      <h4>操作</h4>
      <el-space wrap>
        <el-button size="small" type="primary" @click="openConsole">
          <el-icon><Monitor /></el-icon> CloudWatch
        </el-button>
        <el-button size="small" @click="checkHealth" :loading="healthLoading">
          <el-icon><CircleCheck /></el-icon> 健康检查
        </el-button>
      </el-space>
    </div>

    <div v-if="healthData" class="health-section">
      <h4>健康状态</h4>
      <el-tag :type="healthData.health_status === 'healthy' ? 'success' : 'warning'">
        {{ healthData.health_status }}
      </el-tag>
      <el-descriptions v-if="healthData.details" :column="1" border size="small" style="margin-top: 8px">
        <el-descriptions-item v-for="(val, key) in healthData.details" :key="key" :label="String(key)">
          {{ val }}
        </el-descriptions-item>
      </el-descriptions>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { getConsoleUrl } from '@/api/cloudwatch'
import type { TopologyNode } from '@/types'
import api from '@/api/index'

const props = defineProps<{
  node: TopologyNode
  accountId: number
}>()

defineEmits(['close'])

const healthLoading = ref(false)
const healthData = ref<any>(null)

const tagType = computed(() => {
  const map: Record<string, string> = {
    route53: 'success',
    alb: '',
    target_group: 'info',
    ecs_service: 'warning',
    ec2: 'danger',
    rds: '',
    elasticache: 'success',
  }
  return (map[props.node.node_type] || '') as any
})

async function openConsole() {
  const resourceId = props.node.id.split(':').slice(1).join(':')
  const res = await getConsoleUrl({
    region: props.node.region,
    resource_type: props.node.node_type,
    resource_id: resourceId,
  })
  window.open(res.data.url, '_blank')
}

async function checkHealth() {
  healthLoading.value = true
  try {
    const nodeDbId = props.node.id.split(':').slice(1).join(':')
    const res = await api.get(`/topology/${props.accountId}/nodes/${nodeDbId}/health`)
    healthData.value = res.data
  } catch {
    healthData.value = { health_status: 'error', details: { error: '检查失败' } }
  } finally {
    healthLoading.value = false
  }
}
</script>

<style scoped>
.node-panel { height: 100%; }
.panel-header {
  display: flex;
  align-items: center;
  gap: 8px;
}
.node-label {
  flex: 1;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
}
.metadata-section, .actions-section, .health-section {
  margin-top: 16px;
}
h4 {
  margin-bottom: 8px;
  color: #303133;
  font-size: 14px;
}
</style>
