<template>
  <div class="users-page">
    <div class="page-header">
      <h2>用户管理</h2>
      <el-button type="primary" @click="showAddDialog = true">
        <el-icon><Plus /></el-icon> 添加用户
      </el-button>
    </div>

    <el-table :data="users" stripe v-loading="loading">
      <el-table-column prop="username" label="用户名" />
      <el-table-column prop="email" label="邮箱" />
      <el-table-column prop="is_admin" label="角色" width="100">
        <template #default="{ row }">
          <el-tag :type="row.is_admin ? 'danger' : ''" size="small">
            {{ row.is_admin ? '管理员' : '普通用户' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="is_active" label="状态" width="80">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
            {{ row.is_active ? '启用' : '禁用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="240">
        <template #default="{ row }">
          <el-button size="small" @click="openRbac(row)">权限</el-button>
          <el-button size="small" :type="row.is_active ? 'warning' : 'success'" @click="toggleActive(row)">
            {{ row.is_active ? '禁用' : '启用' }}
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="showAddDialog" title="添加用户" width="400px">
      <el-form :model="addForm" label-width="80px">
        <el-form-item label="用户名">
          <el-input v-model="addForm.username" />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="addForm.email" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="addForm.password" type="password" show-password />
        </el-form-item>
        <el-form-item label="管理员">
          <el-switch v-model="addForm.is_admin" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="handleAdd">确定</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showRbacDialog" title="账号权限" width="500px">
      <p>用户: <strong>{{ rbacUser?.username }}</strong></p>
      <el-checkbox-group v-model="rbacAccountIds">
        <el-checkbox v-for="acc in accountsStore.accounts" :key="acc.id" :value="acc.id">
          {{ acc.account_name }} ({{ acc.account_id }})
        </el-checkbox>
      </el-checkbox-group>
      <template #footer>
        <el-button @click="showRbacDialog = false">取消</el-button>
        <el-button type="primary" @click="saveRbac">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useAccountsStore } from '@/stores/accounts'
import api from '@/api/index'
import { ElMessage } from 'element-plus'
import type { UserInfo } from '@/types'

const accountsStore = useAccountsStore()
const users = ref<UserInfo[]>([])
const loading = ref(false)
const showAddDialog = ref(false)
const showRbacDialog = ref(false)
const rbacUser = ref<UserInfo | null>(null)
const rbacAccountIds = ref<number[]>([])

const addForm = reactive({ username: '', email: '', password: '', is_admin: false })

async function fetchUsers() {
  loading.value = true
  try {
    const res = await api.get('/users/')
    users.value = res.data
  } finally {
    loading.value = false
  }
}

async function handleAdd() {
  try {
    await api.post('/users/', addForm)
    ElMessage.success('用户创建成功')
    showAddDialog.value = false
    await fetchUsers()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '创建失败')
  }
}

async function toggleActive(user: UserInfo) {
  await api.put(`/users/${user.id}`, { is_active: !user.is_active })
  await fetchUsers()
}

async function openRbac(user: UserInfo) {
  rbacUser.value = user
  const res = await api.get(`/users/${user.id}/accounts`)
  rbacAccountIds.value = res.data.account_ids
  showRbacDialog.value = true
}

async function saveRbac() {
  if (!rbacUser.value) return
  await api.put(`/users/${rbacUser.value.id}/accounts`, { account_ids: rbacAccountIds.value })
  ElMessage.success('权限已更新')
  showRbacDialog.value = false
}

onMounted(() => {
  fetchUsers()
  accountsStore.fetchAccounts()
})
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
</style>
