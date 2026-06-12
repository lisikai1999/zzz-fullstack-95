<template>
  <el-container class="app-layout">
    <el-aside width="220px" class="sidebar">
      <div class="logo">
        <el-icon><Monitor /></el-icon>
        <span>AWS Ops</span>
      </div>
      <el-menu :default-active="route.path" router :collapse="false">
        <el-menu-item index="/">
          <el-icon><DataBoard /></el-icon>
          <span>仪表盘</span>
        </el-menu-item>
        <el-menu-item index="/topology">
          <el-icon><Share /></el-icon>
          <span>服务拓扑</span>
        </el-menu-item>
        <el-menu-item index="/resources">
          <el-icon><List /></el-icon>
          <span>资源清单</span>
        </el-menu-item>
        <el-menu-item index="/certificates">
          <el-icon><Key /></el-icon>
          <span>证书管理</span>
        </el-menu-item>
        <el-menu-item v-if="authStore.user?.is_admin" index="/accounts">
          <el-icon><OfficeBuilding /></el-icon>
          <span>账号管理</span>
        </el-menu-item>
        <el-menu-item v-if="authStore.user?.is_admin" index="/users">
          <el-icon><User /></el-icon>
          <span>用户管理</span>
        </el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="header">
        <div class="header-right">
          <span class="username">{{ authStore.user?.username }}</span>
          <el-button text @click="handleLogout">退出</el-button>
        </div>
      </el-header>
      <el-main>
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

function handleLogout() {
  authStore.logout()
  router.push('/login')
}
</script>

<style scoped>
.app-layout {
  height: 100vh;
}
.sidebar {
  background: #1d1e1f;
  color: #fff;
  overflow-y: auto;
}
.logo {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 20px 16px;
  font-size: 18px;
  font-weight: bold;
  color: #409eff;
}
.sidebar .el-menu {
  border-right: none;
  background: #1d1e1f;
}
.header {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  border-bottom: 1px solid #ebeef5;
  background: #fff;
}
.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}
.username {
  color: #606266;
}
</style>
