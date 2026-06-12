import api from './index'
import type { UserInfo } from '@/types'

export function login(username: string, password: string) {
  return api.post<{ access_token: string; refresh_token: string }>('/auth/login', { username, password })
}

export function refreshToken(refresh_token: string) {
  return api.post<{ access_token: string; refresh_token: string }>('/auth/refresh', { refresh_token })
}

export function getMe() {
  return api.get<UserInfo>('/auth/me')
}
