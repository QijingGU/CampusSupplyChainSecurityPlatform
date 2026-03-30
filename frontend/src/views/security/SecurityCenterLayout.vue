<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Lock, Monitor, ArrowLeft, FolderOpened } from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const loading = ref(true)

const navItems = [
  { path: '/security/ids', label: 'IDS 入侵检测', icon: Lock },
  { path: '/security/situation', label: '安全态势感知', icon: Monitor },
  { path: '/security/sandbox', label: '安全沙箱', icon: FolderOpened },
]

// 安全中心仅管理员可访问，返回时跳转到管理员默认入口（用户管理）
function goBack() {
  router.push('/user')
}

function goTo(path: string) {
  if (route.path === path) return
  loading.value = true
  router.push(path)
}

const isActive = (path: string) => route.path === path || route.path.startsWith(path + '/')

let loadTimer: ReturnType<typeof setTimeout> | null = null
onMounted(() => {
  document.body.classList.add('security-center-active')
  loadTimer = setTimeout(() => { loading.value = false }, 280)
})
onBeforeUnmount(() => {
  document.body.classList.remove('security-center-active')
  if (loadTimer) clearTimeout(loadTimer)
})
</script>

<template>
  <div class="security-center">
    <div v-if="loading" class="loading-overlay">
      <div class="loading-spinner" />
      <span class="loading-text">安全中心加载中...</span>
    </div>
    <aside class="security-nav">
      <div class="nav-back" @click="goBack">
        <el-icon :size="18"><ArrowLeft /></el-icon>
        <span>返回平台</span>
      </div>
      <div class="nav-header">
        <div class="nav-logo">
          <el-icon :size="26"><Lock /></el-icon>
        </div>
        <span class="nav-title">安全中心</span>
      </div>
      <nav class="nav-list">
        <div
          v-for="item in navItems"
          :key="item.path"
          class="nav-item"
          :class="{ active: isActive(item.path) }"
          @click="goTo(item.path)"
        >
          <el-icon :size="20"><component :is="item.icon" /></el-icon>
          <span>{{ item.label }}</span>
        </div>
      </nav>
    </aside>
    <main class="security-main">
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>
  </div>
</template>

<style scoped>
.security-center {
  position: fixed;
  inset: 0;
  display: flex;
  background: #050505;
  z-index: 2000;
}

.loading-overlay {
  position: fixed;
  inset: 0;
  background: rgba(5, 5, 5, 0.95);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 24px;
  z-index: 1000;
  backdrop-filter: blur(8px);
}
.loading-spinner {
  width: 48px;
  height: 48px;
  border: 3px solid rgba(59, 130, 246, 0.2);
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}
.loading-text {
  font-size: 14px;
  font-family: monospace;
  color: rgba(255, 255, 255, 0.6);
  letter-spacing: 0.2em;
}

.security-nav {
  width: 228px;
  background: #0a0a0a;
  border-right: 1px solid rgba(255, 255, 255, 0.06);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}
.nav-back {
  padding: 18px 20px;
  display: flex;
  align-items: center;
  gap: 10px;
  color: rgba(255, 255, 255, 0.5);
  font-size: 15px;
  cursor: pointer;
  transition: color 0.2s;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}
.nav-back:hover {
  color: #3b82f6;
}
.nav-header {
  padding: 22px 20px 26px;
  display: flex;
  align-items: center;
  gap: 12px;
}
.nav-logo {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  background: rgba(59, 130, 246, 0.15);
  border: 1px solid rgba(59, 130, 246, 0.25);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #3b82f6;
}
.nav-title {
  font-size: 18px;
  font-weight: 700;
  color: #fff;
  letter-spacing: 0.02em;
}
.nav-list {
  flex: 1;
  padding: 12px 12px 20px;
}
.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 18px;
  min-height: 52px;
  border-radius: 12px;
  cursor: pointer;
  color: rgba(255, 255, 255, 0.62);
  font-size: 15px;
  line-height: 1.35;
  transition: all 0.2s;
  margin-bottom: 8px;
}
.nav-item:hover {
  background: rgba(255, 255, 255, 0.05);
  color: rgba(255, 255, 255, 0.9);
}
.nav-item.active {
  background: rgba(59, 130, 246, 0.15);
  color: #3b82f6;
  font-weight: 600;
}

.security-main {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
