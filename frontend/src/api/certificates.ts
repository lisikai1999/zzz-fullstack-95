import api from './index'
import type { Certificate, CertAlertSummary } from '@/types'

export function getCertificates(params: Record<string, any> = {}) {
  return api.get<Certificate[]>('/certificates/', { params })
}

export function getCertAlerts() {
  return api.get<CertAlertSummary>('/certificates/alerts')
}

export function getCertOrphans() {
  return api.get<Certificate[]>('/certificates/orphans')
}
