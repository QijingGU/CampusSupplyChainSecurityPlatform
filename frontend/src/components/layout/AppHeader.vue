<script setup lang="ts">
import { useUserStore } from '@/stores/user'
import { useRouter } from 'vue-router'
import { Fold, Expand, User, SwitchButton, ArrowDown } from '@element-plus/icons-vue'

defineProps<{ title: string; collapsed: boolean; immersive?: boolean }>()
defineEmits<{ (e: 'toggle'): void }>()

const userStore = useUserStore()
const router = useRouter()

function handleLogout() {
  userStore.logout()
  router.push('/login')
}
</script>

<template>
  <header class="app-header" :class="{ 'app-header--immersive': immersive }">
    <div class="header-left">
      <div class="toggle-btn" @click="$emit('toggle')">
        <el-icon :size="22"><Fold v-if="!collapsed" /><Expand v-else /></el-icon>
      </div>
      <h1 class="page-title">{{ title }}</h1>
    </div>

    <div class="header-right">
      <el-dropdown trigger="click" @command="handleLogout">
        <div class="user-avatar">
          <el-avatar :size="36">
            <el-icon><User /></el-icon>
          </el-avatar>
          <span class="user-name">{{ userStore.userInfo?.real_name || userStore.userInfo?.username || '用户' }}</span>
          <el-icon class="arrow"><ArrowDown /></el-icon>
        </div>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="logout">
              <el-icon><SwitchButton /></el-icon>
              退出登录
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </header>
</template>

<style lang="scss" scoped>
.app-header {
  height: 64px;
  padding: 0 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--bg-elevated);
  border-bottom: 1px solid var(--border-subtle);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.toggle-btn {
  width: 42px;
  height: 42px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  cursor: pointer;
  color: var(--text-secondary);
  transition: all var(--transition-fast);

  &:hover {
    background: var(--primary-muted);
    color: var(--primary);
  }
}

.page-title {
  font-size: 18px;
  font-weight: 600;
  margin: 0;
  color: var(--text-primary);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.user-avatar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 12px;
  border-radius: 10px;
  cursor: pointer;
  transition: all var(--transition-fast);

  &:hover {
    background: var(--bg-hover);
  }

  .user-name {
    font-size: 14px;
    color: var(--text-primary);
  }

  .arrow {
    font-size: 12px;
    color: var(--text-muted);
  }
}

.app-header--immersive {
  background: var(--screen-chrome-bg);
  border-bottom: 1px solid var(--screen-chrome-border);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);

  .page-title {
    color: var(--screen-text);
  }

  .toggle-btn {
    color: rgba(226, 232, 240, 0.75);

    &:hover {
      background: rgba(99, 102, 241, 0.2);
      color: var(--screen-accent-strong);
    }
  }

  .user-avatar:hover {
    background: rgba(99, 102, 241, 0.12);
  }

  .user-avatar .user-name {
    color: var(--screen-text);
  }

  .user-avatar .arrow {
    color: var(--screen-muted);
  }

  :deep(.el-avatar) {
    background: rgba(99, 102, 241, 0.35);
    color: var(--screen-accent-strong);
  }
}
</style>
