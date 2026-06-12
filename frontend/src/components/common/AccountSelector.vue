<template>
  <el-select v-model="modelValue" placeholder="选择账号" clearable filterable @change="$emit('update:modelValue', $event)">
    <el-option
      v-for="acc in accountsStore.accounts"
      :key="acc.id"
      :label="`${acc.account_name} (${acc.account_id})`"
      :value="acc.id"
    />
  </el-select>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useAccountsStore } from '@/stores/accounts'

const modelValue = defineModel<number | null>()
const accountsStore = useAccountsStore()

onMounted(() => {
  if (accountsStore.accounts.length === 0) {
    accountsStore.fetchAccounts()
  }
})
</script>
