import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/store/user'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    component: () => import('@/views/Layout.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        name: 'Dashboard',
        component: () => import('@/views/Dashboard.vue'),
        meta: { title: '首页' }
      },
      {
        path: 'documents',
        name: 'Documents',
        component: () => import('@/views/Documents.vue'),
        meta: { title: '文档管理' }
      },
      {
        path: 'documents/:id',
        name: 'DocumentDetail',
        component: () => import('@/views/DocumentDetail.vue'),
        meta: { title: '文档详情' }
      },
      {
        path: 'proofreading',
        name: 'Proofreading',
        component: () => import('@/views/Proofreading.vue'),
        meta: { title: '校对任务' }
      },
      {
        path: 'approval',
        name: 'Approval',
        component: () => import('@/views/Approval.vue'),
        meta: { title: '审批任务' }
      },
      {
        path: 'approval-settings',
        name: 'ApprovalSettings',
        component: () => import('@/views/ApprovalSettings.vue'),
        meta: { title: '审批节点设置' }
      },
      {
        path: 'numbers',
        name: 'Numbers',
        component: () => import('@/views/Numbers.vue'),
        meta: { title: '编号管理' }
      },
      {
        path: 'role-config',
        name: 'RoleConfig',
        component: () => import('@/views/RoleConfig.vue'),
        meta: { title: '审批角色配置' }
      },
      {
        path: 'users',
        name: 'Users',
        component: () => import('@/views/Users.vue'),
        meta: { title: '用户管理' }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
router.beforeEach((to, from, next) => {
  const userStore = useUserStore()
  const token = userStore.token

  if (to.meta.requiresAuth && !token) {
    next('/login')
  } else if (to.path === '/login' && token) {
    next('/')
  } else {
    next()
  }
})

export default router
