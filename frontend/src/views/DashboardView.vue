<template>
  <div class="dashboard">
    <h2>仪表盘</h2>
    <el-row :gutter="16" class="stats-row">
      <el-col :span="6">
        <el-card shadow="hover">
          <el-statistic title="AWS 账号" :value="accountsStore.accounts.length" />
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <el-statistic title="资源总数" :value="totalResources" />
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="warning-card">
          <el-statistic title="证书告警" :value="certAlertCount" value-style="color: #e6a23c" />
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="danger-card">
          <el-statistic title="闲置资源" :value="idleCount" value-style="color: #f56c6c" />
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-top: 20px">
      <el-col :span="12">
        <el-card>
          <template #header>资源分布</template>
          <el-table :data="summaryData" stripe size="small">
            <el-table-column prop="resource_type" label="类型" />
            <el-table-column prop="count" label="数量" width="80" />
            <el-table-column prop="idle_count" label="闲置" width="80" />
            <el-table-column prop="untagged_count" label="无标签" width="80" />
          </el-table>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card>
          <template #header>证书到期预警</template>
          <div v-if="certAlerts">
            <el-tag v-if="certAlerts.critical.length" type="danger" class="alert-tag">
              紧急 (≤7天): {{ certAlerts.critical.length }}
            </el-tag>
            <el-tag v-if="certAlerts.warning.length" type="warning" class="alert-tag">
              警告 (≤15天): {{ certAlerts.warning.length }}
            </el-tag>
            <el-tag v-if="certAlerts.info.length" type="info" class="alert-tag">
              提醒 (≤30天): {{ certAlerts.info.length }}
            </el-tag>
            <el-table :data="certAlerts.critical.concat(certAlerts.warning).slice(0, 10)" stripe size="small" style="margin-top: 12px">
              <el-table-column prop="domain_name" label="域名" />
              <el-table-column prop="not_after" label="过期时间" width="180" />
              <el-table-column prop="alert_level" label="级别" width="80">
                <template #default="{ row }">
                  <el-tag :type="row.alert_level === 'critical' ? 'danger' : row.alert_level === 'warning' ? 'warning' : 'info'" size="small">
                    {{ row.alert_level }}
                  </el-tag>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useAccountsStore } from '@/stores/accounts'
import { getResourceSummary } from '@/api/resources'
import { getCertAlerts } from '@/api/certificates'
import type { ResourceSummary, CertAlertSummary } from '@/types'

const accountsStore = useAccountsStore()
const summaryData = ref<ResourceSummary[]>([])
const certAlerts = ref<CertAlertSummary | null>(null)

const totalResources = computed(() => summaryData.value.reduce((sum, r) => sum + r.count, 0))
const idleCount = computed(() => summaryData.value.reduce((sum, r) => sum + r.idle_count, 0))
const certAlertCount = computed(() => {
  if (!certAlerts.value) return 0
  return certAlerts.value.critical.length + certAlerts.value.warning.length + certAlerts.value.info.length
})

onMounted(async () => {
  await accountsStore.fetchAccounts()
  const [summaryRes, alertRes] = await Promise.all([
    getResourceSummary(),
    getCertAlerts(),
  ])
  summaryData.value = summaryRes.data
  certAlerts.value = alertRes.data
})
</script>

<style scoped>
.dashboard h2 { margin-bottom: 20px; }
.stats-row .el-card { text-align: center; }
.alert-tag { margin-right: 8px; margin-bottom: 8px; }
</style>
