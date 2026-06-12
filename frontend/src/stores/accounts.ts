import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getAccounts } from '@/api/accounts'
import type { AWSAccount } from '@/types'

export const useAccountsStore = defineStore('accounts', () => {
  const accounts = ref<AWSAccount[]>([])
  const loading = ref(false)

  async function fetchAccounts() {
    loading.value = true
    try {
      const res = await getAccounts()
      accounts.value = res.data
    } finally {
      loading.value = false
    }
  }

  return { accounts, loading, fetchAccounts }
})
