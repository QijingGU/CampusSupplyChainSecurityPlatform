<script setup lang="ts">
import { onMounted } from 'vue'
import { ElConfigProvider } from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import { getUserInfo } from '@/api/auth'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()

onMounted(async () => {
  if (!userStore.token || userStore.userInfo) return
  try {
    const res: any = await getUserInfo()
    const user = res?.data || res
    if (user?.id && user?.role) {
      userStore.setUserInfo(user)
    }
  } catch {
    // Shared request interceptor already handles auth expiration and network failures.
  }
})
</script>

<template>
  <el-config-provider :locale="zhCn">
    <router-view />
  </el-config-provider>
</template>

<style>
#app {
  font-family: 'Plus Jakarta Sans', 'Inter', system-ui, sans-serif;
}
</style>
