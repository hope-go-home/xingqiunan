/**
 * stores/task.js — 任务状态管理（Pinia）。
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as taskApi from '../api/tasks'

export const useTaskStore = defineStore('task', () => {
  // ---- state ----
  const tasks = ref([])
  const loading = ref(false)

  // ---- getters ----
  const pendingCount   = computed(() => tasks.value.filter(t => t.status === 'pending').length)
  const runningCount   = computed(() => tasks.value.filter(t => t.status === 'running').length)
  const completedCount = computed(() => tasks.value.filter(t => t.status === 'completed').length)
  const failedCount    = computed(() => tasks.value.filter(t => t.status === 'failed').length)

  // ---- actions ----
  /** 拉取任务列表。silent=true 时不显示 loading，避免自动刷新闪烁 */
  async function fetchTasks(silent) {
    if (!silent) loading.value = true
    try {
      tasks.value = await taskApi.listTasks()
    } finally {
      if (!silent) loading.value = false
    }
  }

  /** 创建新任务 */
  async function addTask(payload) {
    const task = await taskApi.createTask(payload)
    tasks.value.unshift(task)
    return task
  }

  return {
    tasks, loading,
    pendingCount, runningCount, completedCount, failedCount,
    fetchTasks, addTask,
  }
})
