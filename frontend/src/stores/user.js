/**
 * stores/user.js — 用户状态管理（Pinia）。
 * 管理：登录 token、用户信息、登录/登出。
 * token 持久化到 localStorage。
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as authApi from '../api/auth'

export const useUserStore = defineStore('user', () => {
  // ---- state ----
  const token = ref(localStorage.getItem('token') || '')
  const user = ref(null)

  // 从 localStorage 恢复用户信息
  const savedUser = localStorage.getItem('user')
  if (savedUser) {
    try { user.value = JSON.parse(savedUser) } catch { /* 丢弃 */ }
  }

  // ---- getters ----
  const isLoggedIn = computed(() => !!token.value)
  const username = computed(() => user.value?.username || '')

  // ---- actions ----
  /** 登录 */
  async function loginAction(payload) {
    const res = await authApi.login(payload)
    token.value = res.access_token
    user.value = res.user
    localStorage.setItem('token', res.access_token)
    localStorage.setItem('user', JSON.stringify(res.user))
  }

  /** 注册 */
  async function registerAction(payload) {
    return await authApi.register(payload)
  }

  /** 登出 */
  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('user')
  }

  return { token, user, isLoggedIn, username, loginAction, registerAction, logout }
})
