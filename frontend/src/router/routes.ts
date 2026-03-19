import type { RouteRecordRaw } from 'vue-router'
import AppLayout from '@/components/layout/AppLayout.vue'
import type { RoleType } from '@/types/role'

export type RouteMetaRole = {
  title?: string
  icon?: string
  hideInMenu?: boolean
  menuGroup?: string
  roles?: RoleType[]
}

export const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/login/Login.vue'),
    meta: { public: true, title: '登录' },
  },
  {
    path: '/',
    component: AppLayout,
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/dashboard/Dashboard.vue'),
        meta: { title: '工作台', icon: 'Odometer', roles: ['system_admin', 'logistics_admin', 'warehouse_procurement', 'campus_supplier', 'counselor_teacher'] },
      },
      // 后勤管理员 + 仓储采购员
      {
        path: 'goods',
        name: 'GoodsList',
        component: () => import('@/views/goods/GoodsList.vue'),
        meta: { title: '物资管理', icon: 'Box', roles: ['logistics_admin', 'warehouse_procurement'] },
      },
      {
        path: 'supplier',
        name: 'SupplierList',
        component: () => import('@/views/supplier/SupplierList.vue'),
        meta: { title: '供应商管理', icon: 'OfficeBuilding', roles: ['system_admin'] },
      },
      {
        path: 'purchase',
        name: 'PurchaseList',
        component: () => import('@/views/purchase/PurchaseList.vue'),
        meta: { title: '采购管理', icon: 'ShoppingCart', roles: ['logistics_admin'] },
      },
      {
        path: 'purchase/apply',
        name: 'PurchaseApply',
        component: () => import('@/views/purchase/PurchaseApply.vue'),
        meta: { title: '采购申请', icon: 'Edit', hideInMenu: true, roles: ['counselor_teacher'] },
      },
      // 仓储 - 后勤管理员 + 仓储采购员
      {
        path: 'stock/in',
        name: 'StockInList',
        component: () => import('@/views/stock/StockInList.vue'),
        meta: { title: '入库管理', icon: 'Upload', menuGroup: 'stock', roles: ['warehouse_procurement'] },
      },
      {
        path: 'stock/out',
        name: 'StockOutList',
        component: () => import('@/views/stock/StockOutList.vue'),
        meta: { title: '出库管理', icon: 'Download', menuGroup: 'stock', roles: ['warehouse_procurement'] },
      },
      {
        path: 'stock/inventory',
        name: 'InventoryList',
        component: () => import('@/views/stock/InventoryList.vue'),
        meta: { title: '库存查询', icon: 'Box', menuGroup: 'stock', roles: ['warehouse_procurement'] },
      },
      // 配送 - 仅仓储执行
      {
        path: 'delivery',
        name: 'DeliveryList',
        component: () => import('@/views/delivery/DeliveryList.vue'),
        meta: { title: '配送管理', icon: 'Van', menuGroup: 'stock', roles: ['warehouse_procurement'] },
      },
      {
        path: 'delivery/map',
        name: 'DeliveryMap',
        component: () => import('@/views/delivery/DeliveryMap.vue'),
        meta: { title: '配送地图', icon: 'Location', menuGroup: 'stock', roles: ['warehouse_procurement'] },
      },
      // 仓储大屏
      {
        path: 'screen/warehouse',
        name: 'WarehouseScreen',
        component: () => import('@/views/screen/WarehouseScreen.vue'),
        meta: { title: '仓储大屏', icon: 'Monitor', menuGroup: 'stock', roles: ['warehouse_procurement'] },
      },
      // 后勤大屏
      {
        path: 'screen/logistics',
        name: 'LogisticsScreen',
        component: () => import('@/views/screen/LogisticsScreen.vue'),
        meta: { title: '后勤大屏', icon: 'Monitor', roles: ['logistics_admin'] },
      },
      // 溯源 - 教师、后勤、仓储
      {
        path: 'trace',
        name: 'TraceQuery',
        component: () => import('@/views/trace/TraceQuery.vue'),
        meta: { title: '溯源查询', icon: 'Connection', roles: ['system_admin', 'logistics_admin', 'warehouse_procurement', 'counselor_teacher'] },
      },
      // 预警 - 后勤管理员 + 仓储采购员
      {
        path: 'warning',
        name: 'WarningList',
        component: () => import('@/views/warning/WarningList.vue'),
        meta: { title: '预警中心', icon: 'Warning', roles: ['logistics_admin', 'warehouse_procurement'] },
      },
      // AI 助手 - 所有人
      {
        path: 'ai/chat',
        name: 'AIChat',
        component: () => import('@/views/ai/AIChat.vue'),
        meta: { title: 'AI 助手', icon: 'ChatDotRound', roles: ['system_admin', 'logistics_admin', 'warehouse_procurement', 'campus_supplier', 'counselor_teacher'] },
      },
      // 辅导员教师专属 - 我的申请
      {
        path: 'my-applications',
        name: 'MyApplications',
        component: () => import('@/views/teacher/MyApplications.vue'),
        meta: { title: '我的申请', icon: 'Document', roles: ['counselor_teacher'] },
      },
      // 校园合作供应商专属 - 我的订单
      {
        path: 'supplier/orders',
        name: 'SupplierOrders',
        component: () => import('@/views/supplier/SupplierOrders.vue'),
        meta: { title: '我的订单', icon: 'List', roles: ['campus_supplier'] },
      },
      // 校园合作供应商专属 - 物流-仓储配送管理
      {
        path: 'supplier/logistics',
        name: 'SupplierLogistics',
        component: () => import('@/views/supplier/SupplierLogistics.vue'),
        meta: { title: '物流-仓储配送管理', icon: 'Van', roles: ['campus_supplier'] },
      },
      // 用户管理 - 管理员
      {
        path: 'user',
        name: 'UserManage',
        component: () => import('@/views/user/UserManage.vue'),
        meta: { title: '用户管理', icon: 'User', roles: ['system_admin'] },
      },
      // 审计日志 + 异常监督 - 管理员
      {
        path: 'audit',
        name: 'AuditLogs',
        component: () => import('@/views/audit/AuditLogs.vue'),
        meta: { title: '审计与异常监督', icon: 'Monitor', roles: ['system_admin'] },
      },
      // 安全中心 - 点击后跳转独立界面，内含 IDS / 安全态势感知
      {
        path: 'security',
        component: () => import('@/views/security/SecurityCenterLayout.vue'),
        redirect: '/security/ids',
        meta: { title: '安全中心', icon: 'Lock', menuGroup: 'security', roles: ['system_admin'] },
        children: [
          {
            path: 'ids',
            name: 'IDSManage',
            component: () => import('@/views/security/SecurityIDS.vue'),
            meta: { title: 'IDS 入侵检测', hideInMenu: true, roles: ['system_admin'] },
          },
          {
            path: 'situation',
            name: 'SecuritySituation',
            component: () => import('@/views/security/SecuritySituation.vue'),
            meta: { title: '安全态势感知', hideInMenu: true, roles: ['system_admin'] },
          },
        ],
      },
      {
        path: 'ids',
        redirect: '/security/ids',
        meta: { hideInMenu: true },
      },
    ],
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/error/NotFound.vue'),
    meta: { public: true },
  },
]
