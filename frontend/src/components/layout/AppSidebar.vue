<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { routes } from '@/router/routes'
import { useUserStore } from '@/stores/user'
import { useNoticeStore } from '@/stores/notice'
import type { RoleType } from '@/types/role'
import type { RouteMetaRole } from '@/router/routes'
import {
  Odometer,
  Box,
  OfficeBuilding,
  ShoppingCart,
  Edit,
  Upload,
  Download,
  Van,
  Connection,
  Warning,
  ChatDotRound,
  User,
  DArrowLeft,
  DArrowRight,
  Document,
  List,
  Monitor,
  Location,
  Lock,
  Star,
} from '@element-plus/icons-vue'

const props = defineProps<{ collapsed: boolean; immersive?: boolean }>()
defineEmits<{ (e: 'update:collapsed', v: boolean): void }>()

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const noticeStore = useNoticeStore()

const iconMap: Record<string, object> = {
  Odometer,
  Box,
  Lock,
  OfficeBuilding,
  ShoppingCart,
  Edit,
  Upload,
  Download,
  Van,
  Connection,
  Warning,
  ChatDotRound,
  User,
  Document,
  List,
  Monitor,
  Location,
  Star,
}

const userRole = computed(() => userStore.userInfo?.role as RoleType | undefined)

const menuItems = computed(() => {
  const children = routes.find((r) => r.path === '/')?.children || []
  return children.filter((r) => !r.meta?.hideInMenu && !r.meta?.public)
})

function canAccess(item: (typeof menuItems.value)[0]): boolean {
  const roles = (item.meta as RouteMetaRole)?.roles
  if (!roles?.length) return true
  return userRole.value ? roles.includes(userRole.value) : false
}

const stockItems = computed(() =>
  menuItems.value.filter((r) => r.meta?.menuGroup === 'stock' && canAccess(r))
)
const securityItems = computed(() =>
  menuItems.value.filter((r) => r.meta?.menuGroup === 'security' && canAccess(r))
)
const otherItems = computed(() =>
  menuItems.value.filter((r) => r.meta?.menuGroup !== 'stock' && r.meta?.menuGroup !== 'security' && canAccess(r))
)

function isActive(path: string) {
  const normalizedPath = normalizePath(path)
  return route.path === normalizedPath || route.path.startsWith(normalizedPath + '/')
}

function navigate(path: string) {
  router.push(normalizePath(path))
}

function normalizePath(path: string) {
  if (!path) return '/'
  return path.startsWith('/') ? path : `/${path}`
}

function getIcon(name: string) {
  return iconMap[name] || Box
}

function getBadgeCount(path: string) {
  return noticeStore.getBadgeForPath(normalizePath(path))
}
</script>

<template>
  <aside class="sidebar" :class="{ collapsed: collapsed, immersive: immersive }">
    <div class="logo">
      <div class="logo-icon">
        <span class="icon-text">链</span>
      </div>
      <span v-show="!collapsed" class="logo-text">供应链平台</span>
    </div>

    <nav class="nav">
      <template v-for="item in otherItems" :key="item.path">
        <div
          class="nav-item"
          :class="{ active: isActive(item.path as string) }"
          @click="navigate(item.path as string)"
        >
          <el-badge
            class="nav-icon-badge"
            :is-dot="collapsed && getBadgeCount(item.path as string) > 0"
            :hidden="!(collapsed && getBadgeCount(item.path as string) > 0)"
          >
            <el-icon class="nav-icon">
              <component :is="getIcon(item.meta?.icon as string)" />
            </el-icon>
          </el-badge>
          <el-badge
            :value="getBadgeCount(item.path as string)"
            :hidden="collapsed || getBadgeCount(item.path as string) <= 0"
            type="danger"
          >
            <span v-show="!collapsed" class="nav-label">{{ item.meta?.title }}</span>
          </el-badge>
        </div>
      </template>

      <div v-if="stockItems.length" class="nav-group">
        <div class="nav-group-title" :class="{ collapsed }">
          <el-icon><Box /></el-icon>
          <span v-show="!collapsed">仓储管理</span>
        </div>
        <div
          v-for="item in stockItems"
          :key="item.path"
          class="nav-item nested"
          :class="{ active: isActive(item.path as string) }"
          @click="navigate(item.path as string)"
        >
          <el-badge
            class="nav-icon-badge"
            :is-dot="collapsed && getBadgeCount(item.path as string) > 0"
            :hidden="!(collapsed && getBadgeCount(item.path as string) > 0)"
          >
            <el-icon class="nav-icon">
              <component :is="getIcon(item.meta?.icon as string)" />
            </el-icon>
          </el-badge>
          <el-badge
            :value="getBadgeCount(item.path as string)"
            :hidden="collapsed || getBadgeCount(item.path as string) <= 0"
            type="danger"
          >
            <span v-show="!collapsed" class="nav-label">{{ item.meta?.title }}</span>
          </el-badge>
        </div>
      </div>
      <div
        v-if="securityItems.length"
        class="nav-item"
        :class="{ active: route.path.startsWith('/security') }"
        @click="navigate('/security')"
      >
        <el-icon class="nav-icon"><Lock /></el-icon>
        <span v-show="!collapsed" class="nav-label">安全中心</span>
      </div>
    </nav>

    <div class="sidebar-footer">
      <div class="collapse-btn" @click="$emit('update:collapsed', !collapsed)">
        <el-icon><DArrowLeft v-if="!collapsed" /><DArrowRight v-else /></el-icon>
      </div>
    </div>
  </aside>
</template>

<style lang="scss" scoped>
.sidebar {
  position: fixed;
  left: 0;
  top: 0;
  bottom: 0;
  width: 220px;
  background: var(--bg-elevated);
  border-right: 1px solid var(--border-subtle);
  box-shadow: 1px 0 4px rgba(0, 0, 0, 0.03);
  display: flex;
  flex-direction: column;
  z-index: 100;
  transition: width var(--transition-base);

  &.immersive {
    background: var(--screen-chrome-bg);
    border-right: 1px solid var(--screen-chrome-border);
    box-shadow: 4px 0 24px rgba(0, 0, 0, 0.25);

    .logo {
      border-bottom-color: var(--screen-chrome-border);
    }

    .logo-text {
      color: var(--screen-text);
    }

    .nav-item {
      color: rgba(226, 232, 240, 0.72);

      &:hover {
        background: rgba(99, 102, 241, 0.18);
        color: var(--screen-accent-strong);
      }

      &.active {
        background: rgba(99, 102, 241, 0.24);
        color: var(--screen-accent-strong);
        box-shadow: inset 0 0 0 1px rgba(129, 140, 248, 0.2);
      }
    }

    .nav-group-title {
      color: rgba(148, 163, 184, 0.65);
    }

    .sidebar-footer {
      border-top-color: var(--screen-chrome-border);
    }

    .collapse-btn {
      color: rgba(148, 163, 184, 0.85);

      &:hover {
        background: rgba(99, 102, 241, 0.15);
        color: var(--screen-accent-strong);
      }
    }

    :deep(.el-badge__content) {
      border-color: var(--screen-panel-solid);
    }
  }

  &.collapsed {
    width: 68px;

    .nav-item .nav-label,
    .logo-text {
      opacity: 0;
      width: 0;
      overflow: hidden;
    }
  }
}

.logo {
  height: 64px;
  padding: 0 20px;
  display: flex;
  align-items: center;
  gap: 12px;
  border-bottom: 1px solid var(--border-subtle);

  &:hover .logo-icon {
    transform: scale(1.05);
  }
}

.logo-icon {
  width: 38px;
  height: 38px;
  border-radius: 10px;
  background: var(--gradient-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  box-shadow: 0 2px 8px rgba(79, 70, 229, 0.25);
  transition: transform var(--transition-fast);
}

.icon-text {
  font-size: 18px;
  font-weight: 700;
  color: #fff;
}

.logo-text {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;
  transition: opacity var(--transition-fast);
}

.nav {
  flex: 1;
  padding: 16px 12px;
  overflow-y: auto;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-radius: 12px;
  cursor: pointer;
  color: var(--text-secondary);
  transition: all var(--transition-fast);
  margin-bottom: 4px;

  &:hover {
    background: var(--primary-muted);
    color: var(--primary);
  }

  &.active {
    background: var(--primary-muted);
    color: var(--primary);
    font-weight: 600;
  }

  &.nested {
    padding-left: 44px;
  }
}

.nav-icon {
  font-size: 20px;
  flex-shrink: 0;
}

.nav-icon-badge {
  display: inline-flex;
}

.nav-label {
  white-space: nowrap;
  transition: opacity var(--transition-fast);
}

.nav-group {
  margin-top: 8px;
}

.nav-group-title {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 16px;
  font-size: 12px;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;

  .el-icon {
    font-size: 16px;
  }
}

.sidebar-footer {
  padding: 16px;
  border-top: 1px solid var(--border-subtle);
}

.collapse-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 8px;
  cursor: pointer;
  color: var(--text-muted);
  transition: all var(--transition-fast);

  &:hover {
    background: var(--bg-hover);
    color: var(--primary);
  }
}
</style>
