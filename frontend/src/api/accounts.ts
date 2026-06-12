import api from './index'
import type { AWSAccount } from '@/types'

export function getAccounts() {
  return api.get<AWSAccount[]>('/accounts/')
}

export function createAccount(data: { account_id: string; account_name: string; access_key: string; secret_key: string; default_region: string }) {
  return api.post<AWSAccount>('/accounts/', data)
}

export function updateAccount(id: number, data: Record<string, any>) {
  return api.put<AWSAccount>(`/accounts/${id}`, data)
}

export function deleteAccount(id: number) {
  return api.delete(`/accounts/${id}`)
}

export function testConnection(id: number) {
  return api.post(`/accounts/${id}/test-connection`)
}
