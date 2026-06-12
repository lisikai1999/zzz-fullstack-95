import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'Login',
      component: () => import('@/views/LoginView.vue'),
    },
    {
      path: '/',
      component: () => import('@/components/layout/AppLayout.vue'),
      meta: { requiresAuth: true },
      children: [
        { path: '', name: 'Dashboard', component: () => import('@/views/DashboardView.vue') },
        { path: 'topology', name: 'Topology', component: () => import('@/views/TopologyView.vue') },
        { path: 'resources', name: 'Resources', component: () => import('@/views/ResourcesView.vue') },
        { path: 'certificates', name: 'Certificates', component: () => import('@/views/CertificatesView.vue') },
        { path: 'accounts', name: 'Accounts', component: () => import('@/views/AccountsView.vue'), meta: { requiresAdmin: true } },
        { path: 'users', name: 'Users', component: () => import('@/views/UsersView.vue'), meta: { requiresAdmin: true } },
      ],
    },
  ],
})

router.beforeEach(async (to) => {
  const authStore = useAuthStore()

  if (to.meta.requiresAuth && !authStore.accessToken) {
    return '/login'
  }

  if (authStore.accessToken && !authStore.user) {
    await authStore.fetchUser()
  }

  if (to.meta.requiresAdmin && authStore.user && !authStore.user.is_admin) {
    return '/'
  }
})

export default router
