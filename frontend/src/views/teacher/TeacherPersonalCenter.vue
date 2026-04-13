<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import TeacherOrdersPanel from './TeacherOrdersPanel.vue'
import TeacherAnalyticsPanel from './TeacherAnalyticsPanel.vue'
import TeacherSettingsPanel from './TeacherSettingsPanel.vue'

const route = useRoute()
const router = useRouter()

type TabKey = 'orders' | 'analytics' | 'settings'
const activeTab = ref<TabKey>('orders')

function tabFromQuery(q: unknown): TabKey {
  const t = String(q || '')
  if (t === 'analytics' || t === 'settings') return t
  return 'orders'
}

watch(
  () => route.query.tab,
  (t) => {
    const next = tabFromQuery(t)
    if (activeTab.value !== next) activeTab.value = next
  },
  { immediate: true }
)

watch(activeTab, (v) => {
  const cur = tabFromQuery(route.query.tab)
  if (cur === v) return
  router.replace({ path: route.path, query: { ...route.query, tab: v } })
})
</script>

<template>
  <div class="personal-page">
    <div class="page-intro">
      <h2>个人中心</h2>
      <p>订单进度、个人能效复盘与账号设置集中在一处。</p>
    </div>
    <el-tabs v-model="activeTab" class="main-tabs">
      <el-tab-pane label="我的订单" name="orders">
        <TeacherOrdersPanel />
      </el-tab-pane>
      <el-tab-pane label="个人能效看板" name="analytics">
        <TeacherAnalyticsPanel />
      </el-tab-pane>
      <el-tab-pane label="系统设置" name="settings">
        <TeacherSettingsPanel />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<style scoped lang="scss">
.personal-page {
  padding: 0;
}
.page-intro {
  margin-bottom: 16px;
  h2 {
    margin: 0 0 8px 0;
    font-size: 20px;
    font-weight: 600;
  }
  p {
    margin: 0;
    font-size: 13px;
    color: var(--text-secondary);
    line-height: 1.5;
  }
}
.main-tabs {
  :deep(.el-tabs__header) {
    margin-bottom: 20px;
  }
}
</style>
