/**
 * api/tasks.js — 任务 CRUD API。
 */

import api from './index'

/** 创建任务 */
export async function createTask(payload) {
  const { data } = await api.post('/tasks/', payload)
  return data
}

/** 获取当前用户所有任务 */
export async function listTasks() {
  const { data } = await api.get('/tasks/')
  return data
}

/** 查看单个任务详情 */
export async function getTask(taskId) {
  const { data } = await api.get(`/tasks/${taskId}`)
  return data
}
