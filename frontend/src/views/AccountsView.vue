<template>
  <div class="accounts-page">
    <div class="page-header">
      <h2>AWS 账号管理</h2>
      <el-button type="primary" @click="showAddDialog = true">
        <el-icon><Plus /></el-icon> 添加账号
      </el-button>
    </div>

    <el-table :data="accountsStore.accounts" stripe v-loading="accountsStore.loading">
      <el-table-column prop="account_name" label="账号名称" />
      <el-table-column prop="account_id" label="AWS Account ID" width="150" />
      <el-table-column prop="default_region" label="默认区域" width="130" />
      <el-table-column prop="is_active" label="状态" width="80">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'danger'" size="small">
            {{ row.is_active ? '启用' : '禁用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="last_sync_at" label="上次同步" width="180" />
      <el-table-column label="操作" width="200">
        <template #default="{ row }">
          <el-button size="small" @click="handleTest(row.id)">测试连接</el-button>
          <el-button size="small" type="danger" @click="handleDelete(row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="showAddDialog" title="添加 AWS 账号" width="500px">
      <el-form :model="addForm" label-width="120px">
        <el-form-item label="账号名称">
          <el-input v-model="addForm.account_name" />
        </el-form-item>
        <el-form-item label="AWS Account ID">
          <el-input v-model="addForm.account_id" maxlength="12" />
        </el-form-item>
        <el-form-item label="Access Key">
          <el-input v-model="addForm.access_key" />
        </el-form-item>
        <el-form-item label="Secret Key">
          <el-input v-model="addForm.secret_key" type="password" show-password />
        </el-form-item>
        <el-form-item label="默认区域">
          <el-select v-model="addForm.default_region">
            <el-option v-for="r in regions" :key="r" :label="r" :value="r" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="handleAdd" :loading="addLoading">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useAccountsStore } from '@/stores/accounts'
import { createAccount, testConnection, deleteAccount } from '@/api/accounts'
import { ElMessage, ElMessageBox } from 'element-plus'

const accountsStore = useAccountsStore()
const showAddDialog = ref(false)
const addLoading = ref(false)
const addForm = reactive({
  account_name: '',
  account_id: '',
  access_key: '',
  secret_key: '',
  default_region: 'us-east-1',
})

const regions = [
  'us-east-1', 'us-east-2', 'us-west-1', 'us-west-2',
  'eu-west-1', 'eu-west-2', 'eu-central-1',
  'ap-southeast-1', 'ap-northeast-1',
]

async function handleAdd() {
  addLoading.value = true
  try {
    await createAccount(addForm)
    ElMessage.success('账号添加成功')
    showAddDialog.value = false
    await accountsStore.fetchAccounts()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '添加失败')
  } finally {
    addLoading.value = false
  }
}

async function handleTest(id: number) {
  try {
    const res = await testConnection(id)
    ElMessage.success(`连接成功: ${res.data.arn}`)
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '连接失败')
  }
}

async function handleDelete(id: number) {
  await ElMessageBox.confirm('确定删除该账号？', '确认')
  try {
    await deleteAccount(id)
    ElMessage.success('已删除')
    await accountsStore.fetchAccounts()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '删除失败')
  }
}

onMounted(() => accountsStore.fetchAccounts())
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
</style>
