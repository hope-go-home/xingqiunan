/**
 * api/auth.js — 认证相关 API：注册、登录。
 */

import api from './index'

/** 注册新用户 → { id, username } */
export async function register(payload) {
  const { data } = await api.post('/auth/register', payload)
  return data
}

/** 登录 → { access_token, user } */
export async function login(payload) {
  const { data } = await api.post('/auth/login', payload)
  return data
}
