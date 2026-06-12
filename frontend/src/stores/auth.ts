import { defineStore } from 'pinia'
import { ref } from 'vue'
import { login as loginApi, refreshToken, getMe } from '@/api/auth'
import type { UserInfo } from '@/types'

export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref(localStorage.getItem('access_token') || '')
  const refreshTokenValue = ref(localStorage.getItem('refresh_token') || '')
  const user = ref<UserInfo | null>(null)

  async function login(username: string, password: string) {
    const res = await loginApi(username, password)
    accessToken.value = res.data.access_token
    refreshTokenValue.value = res.data.refresh_token
    localStorage.setItem('access_token', res.data.access_token)
    localStorage.setItem('refresh_token', res.data.refresh_token)
    await fetchUser()
  }

  async function refresh(): Promise<boolean> {
    if (!refreshTokenValue.value) return false
    try {
      const res = await refreshToken(refreshTokenValue.value)
      accessToken.value = res.data.access_token
      refreshTokenValue.value = res.data.refresh_token
      localStorage.setItem('access_token', res.data.access_token)
      localStorage.setItem('refresh_token', res.data.refresh_token)
      return true
    } catch {
      return false
    }
  }

  async function fetchUser() {
    try {
      const res = await getMe()
      user.value = res.data
    } catch {
      user.value = null
    }
  }

  function logout() {
    accessToken.value = ''
    refreshTokenValue.value = ''
    user.value = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  }

  return { accessToken, refreshTokenValue, user, login, refresh, fetchUser, logout }
})
