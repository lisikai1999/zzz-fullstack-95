<template>
  <div class="resources-page">
    <h2>资源清单</h2>
    <el-card class="filter-card">
      <el-row :gutter="12">
        <el-col :span="4">
          <AccountSelector v-model="filters.account_id" />
        </el-col>
        <el-col :span="4">
          <el-select v-model="filters.region" placeholder="区域" clearable>
            <el-option v-for="r in regions" :key="r" :label="r" :value="r" />
          </el-select>
        </el-col>
        <el-col :span="4">
          <el-select v-model="filters.resource_type" placeholder="资源类型" clearable>
            <el-option label="EC2" value="ec2_instance" />
            <el-option label="RDS" value="rds_instance" />
            <el-option label="ECS Service" value="ecs_service" />
            <el-option label="ALB" value="alb" />
            <el-option label="ElastiCache" value="elasticache_cluster" />
          </el-select>
        </el-col>
        <el-col :span="3">
          <el-checkbox v-model="filters.idle_only">仅闲置</el-checkbox>
        </el-col>
        <el-col :span="3">
          <el-checkbox v-model="filters.untagged_only">仅无标签</el-checkbox>
        </el-col>
        <el-col :span="3">
          <el-button type="primary" @click="fetchData">查询</el-button>
        </el-col>
      </el-row>
    </el-card>

    <el-table :data="resources" stripe v-loading="loading" style="margin-top: 16px">
      <el-table-column prop="resource_type" label="类型" width="130">
        <template #default="{ row }">
          <el-tag size="small">{{ row.resource_type }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="resource_name" label="名称" min-width="160" show-overflow-tooltip />
      <el-table-column prop="resource_id" label="资源 ID" min-width="200" show-overflow-tooltip />
      <el-table-column prop="region" label="区域" width="130" />
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.status === 'running' || row.status === 'available' ? 'success' : 'info'" size="small">
            {{ row.status }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="标记" width="120">
        <template #default="{ row }">
          <el-tag v-if="row.is_idle" type="danger" size="small" style="margin-right: 4px">闲置</el-tag>
          <el-tag v-if="row.is_untagged" type="warning" size="small">无标签</el-tag>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      v-model:current-page="page"
      :page-size="100"
      :total="resources.length >= 100 ? (page + 1) * 100 : page * 100 + resources.length"
      layout="prev, pager, next"
      style="margin-top: 16px; justify-content: center"
      @current-change="fetchData"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { getResources } from '@/api/resources'
import AccountSelector from '@/components/common/AccountSelector.vue'
import type { Resource } from '@/types'

const resources = ref<Resource[]>([])
const loading = ref(false)
const page = ref(1)
const filters = reactive({
  account_id: null as number | null,
  region: '' as string,
  resource_type: '' as string,
  idle_only: false,
  untagged_only: false,
})

const regions = [
  'us-east-1', 'us-east-2', 'us-west-1', 'us-west-2',
  'eu-west-1', 'eu-west-2', 'eu-central-1',
  'ap-southeast-1', 'ap-northeast-1',
]

async function fetchData() {
  loading.value = true
  try {
    const params: Record<string, any> = { skip: (page.value - 1) * 100, limit: 100 }
    if (filters.account_id) params.account_id = filters.account_id
    if (filters.region) params.region = filters.region
    if (filters.resource_type) params.resource_type = filters.resource_type
    if (filters.idle_only) params.idle_only = true
    if (filters.untagged_only) params.untagged_only = true
    const res = await getResources(params)
    resources.value = res.data
  } finally {
    loading.value = false
  }
}

onMounted(fetchData)
</script>

<style scoped>
.filter-card { margin-bottom: 0; }
</style>
