import { createRouter, createWebHistory } from 'vue-router'
import { routes } from './routes'
import { useUserStore } from '@/stores/user'
import type { RoleType } from '@/types/role'
import type { RouteMetaRole } from './routes'

const router = createRouter({
  history: createWebHistory(),
  routes,
})

function getDefaultRedirect(role: RoleType): string {
  switch (role) {
    case 'system_admin':
      return '/user'
    case 'counselor_teacher':
      return '/ai/chat'
    case 'campus_supplier':
      return '/supplier/orders'
    default:
      return '/dashboard'
  }
}

router.beforeEach((to, _from, next) => {
  const userStore = useUserStore()
  const isPublic = to.meta.public as boolean

  if (isPublic) {
    next()
    return
  }

  if (!userStore.token) {
    next({ name: 'Login', query: { redirect: to.fullPath } })
    return
  }

  const routeRoles = (to.meta as RouteMetaRole)?.roles as RoleType[] | undefined
  const userRole = userStore.userInfo?.role as RoleType | undefined

  if (routeRoles?.length && userRole && !routeRoles.includes(userRole)) {
    next(getDefaultRedirect(userRole))
    return
  }

  // 辅导员教师/校园合作供应商访问根路径时跳转到其主入口（首次登录）
  if (to.path === '/') {
    const def = getDefaultRedirect(userRole!)
    if (def !== '/dashboard') {
      next(def)
      return
    }
  }

  next()
})

export default router
