/**
 * router/index.js — 路由配置。
 * 业务路由需要登录（meta.requiresAuth），由全局守卫拦截。
 */
import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '../stores/user'

const routes = [
  {
    path: '/',
    redirect: '/dashboard',
  },
  {
    path: '/login',
    name: 'login',
    component: () => import('../views/LoginView.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/dashboard',
    name: 'dashboard',
    component: () => import('../views/DashboardView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/chat',
    name: 'chat',
    component: () => import('../views/ChatView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/knowledge',
    name: 'knowledge',
    component: () => import('../views/KnowledgeView.vue'),
    meta: { requiresAuth: true },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

/**
 * 全局前置守卫：未登录跳转 /login
 */
router.beforeEach((to, _from, next) => {
  const user = useUserStore()

  // 已登录但显式要求注册新账号（/login?register=1）→ 放行登录页
  if (to.name === 'login' && to.query.register === '1') {
    next()
    return
  }
  if (to.meta.requiresAuth && !user.token) {
    next('/login')
  } else if (to.name === 'login' && user.token) {
    next('/dashboard')
  } else {
    next()
  }
})

export default router
