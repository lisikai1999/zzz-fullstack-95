<template>
  <div class="certs-page">
    <h2>证书管理</h2>

    <el-row :gutter="12" class="alert-cards">
      <el-col :span="8">
        <el-card shadow="hover" class="alert-critical">
          <el-statistic title="紧急 (≤7天)" :value="alerts?.critical.length || 0" value-style="color: #f56c6c" />
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover">
          <el-statistic title="警告 (≤15天)" :value="alerts?.warning.length || 0" value-style="color: #e6a23c" />
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover">
          <el-statistic title="提醒 (≤30天)" :value="alerts?.info.length || 0" value-style="color: #909399" />
        </el-card>
      </el-col>
    </el-row>

    <el-card style="margin-top: 16px">
      <template #header>
        <div class="card-header">
          <span>证书列表</span>
          <el-space>
            <el-checkbox v-model="orphanOnly" @change="fetchCerts">仅孤儿证书</el-checkbox>
            <AccountSelector v-model="selectedAccount" style="width: 200px" />
            <el-button type="primary" size="small" @click="fetchCerts">刷新</el-button>
          </el-space>
        </div>
      </template>

      <el-table :data="certificates" stripe v-loading="loading">
        <el-table-column prop="domain_name" label="域名" min-width="200" show-overflow-tooltip />
        <el-table-column prop="status" label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="row.status === 'ISSUED' ? 'success' : 'warning'" size="small">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="not_after" label="过期时间" width="180" />
        <el-table-column label="告警级别" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.alert_level" :type="alertTagType(row.alert_level)" size="small">
              {{ row.alert_level }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="标记" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.is_orphan" type="danger" size="small">孤儿</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="region" label="区域" width="120" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getCertificates, getCertAlerts } from '@/api/certificates'
import AccountSelector from '@/components/common/AccountSelector.vue'
import type { Certificate, CertAlertSummary } from '@/types'

const certificates = ref<Certificate[]>([])
const alerts = ref<CertAlertSummary | null>(null)
const loading = ref(false)
const orphanOnly = ref(false)
const selectedAccount = ref<number | null>(null)

function alertTagType(level: string) {
  if (level === 'critical') return 'danger'
  if (level === 'warning') return 'warning'
  return 'info'
}

async function fetchCerts() {
  loading.value = true
  try {
    const params: Record<string, any> = {}
    if (orphanOnly.value) params.orphan_only = true
    if (selectedAccount.value) params.account_id = selectedAccount.value
    const res = await getCertificates(params)
    certificates.value = res.data
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  const [, alertRes] = await Promise.all([fetchCerts(), getCertAlerts()])
  alerts.value = alertRes.data
})
</script>

<style scoped>
.alert-cards { margin-bottom: 0; }
.card-header { display: flex; align-items: center; justify-content: space-between; }
</style>
