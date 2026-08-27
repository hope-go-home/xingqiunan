<!--
  App.vue — 全局布局壳。
  左侧固定侧边栏 + 右侧内容区。
  未登录时全屏渲染登录页。
-->
<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUserStore } from './stores/user'

const router = useRouter()
const route = useRoute()
const user = useUserStore()

const isLoginPage = computed(() => route.name === 'login')
const showUserMenu = ref(false)

// 侧栏收缩状态（记忆到 localStorage）
const collapsed = ref(localStorage.getItem('sb-collapsed') === '1')
function toggleCollapse() {
  collapsed.value = !collapsed.value
  localStorage.setItem('sb-collapsed', collapsed.value ? '1' : '0')
}

function closeMenu(e) { if (!e.target.closest('.user-actions')) showUserMenu.value = false }
onMounted(() => document.addEventListener('click', closeMenu))
onUnmounted(() => document.removeEventListener('click', closeMenu))

const navItems = [
  { name: 'dashboard', path: '/dashboard', label: '总览',   icon: '◫' },
  { name: 'chat',      path: '/chat',      label: '对话',   icon: '◈' },
  { name: 'knowledge', path: '/knowledge', label: '知识库', icon: '▣' },
]

function go(path) {
  router.push(path)
}

function logout() {
  user.logout()
  router.push('/login')
}
</script>

<template>
  <!-- 登录页全屏 -->
  <div v-if="isLoginPage" class="fullscreen-shell">
    <router-view />
  </div>

  <!-- 已登录：侧边栏 + 内容 -->
  <div v-else class="shell">
    <aside :class="['sidebar', { collapsed }]">
      <div class="sidebar-brand" @click="go('/dashboard')" title="TaskBench">
        <span class="brand-icon">◆</span>
        <span class="brand-text">TaskBench</span>
      </div>

      <nav class="sidebar-nav">
        <button
          v-for="item in navItems"
          :key="item.name"
          :class="['nav-btn', { active: route.name === item.name }]"
          :title="collapsed ? item.label : undefined"
          @click="go(item.path)"
        >
          <span class="nav-icon">{{ item.icon }}</span>
          <span class="nav-label">{{ item.label }}</span>
        </button>
      </nav>

      <div class="sidebar-footer">
        <span class="user-badge" @click="showUserMenu = !showUserMenu">{{ user.username?.charAt(0)?.toUpperCase() }}</span>
        <span class="user-name">{{ user.username }}</span>
        <div class="user-actions">
          <button class="user-menu-btn" @click="showUserMenu = !showUserMenu" title="账号管理">+</button>
          <div v-if="showUserMenu" class="user-dropdown">
            <button @click="showUserMenu = false; router.push('/login?register=1')">注册新账号</button>
            <button @click="showUserMenu = false; logout(); router.push('/login')">切换账号</button>
            <button @click="showUserMenu = false; logout()">退出登录</button>
          </div>
        </div>
      </div>

      <button class="collapse-btn" :title="collapsed ? '展开侧栏' : '收起侧栏'" @click="toggleCollapse">
        {{ collapsed ? '»' : '«' }}
      </button>
    </aside>

    <main class="main">
      <router-view v-slot="{ Component }">
        <keep-alive>
          <component :is="Component" />
        </keep-alive>
      </router-view>
    </main>
  </div>
</template>

<style>
/* ============================================
   Design Tokens — "Ink & Vellum" (制图纸)
   灵感：工程制图台 —— 内容区是铺在板上的坐标纸，
   卡片是钉住的图纸，mono 注记 + 朱红标记点缀。
   ============================================ */
:root {
  --paper:    #F4F5F2;   /* 页面背景：冷调绘图纸 */
  --white:    #FFFFFF;   /* 卡片 / 表面 */
  --steel:    #EFF0EB;   /* 输入框背景 */
  --border:   #DEE1DA;   /* 分割线 */

  --ink:      #172038;   /* 主文字：深墨蓝 */
  --slate:    #5D6373;   /* 次文字 */
  --muted:    #A2A7B0;   /* 占位符 */

  --cobalt:      #3D5BF5;   /* 主 CTA / 选中 */
  --cobalt-dim:  #2C46DB;   /* hover 加深 */
  --cobalt-bg:   #EDF1FE;   /* 选中背景（浅） */

  --vermilion:   #D9532B;   /* 注记红：仅用于小型标注记号 */

  --grid-line: rgba(23,32,56,0.045);  /* 坐标纸网格线 */

  --amber:      #E8950A;   /* 运行中 / 警告 */
  --amber-dim:  #C47B08;
  --amber-bg:   #FFF8EB;

  --verdant:      #10B981;   /* 完成 / 成功 */
  --verdant-dim:  #0D9C6C;
  --verdant-bg:   #ECFDF5;

  --crimson:      #EF4444;   /* 失败 / 删除 */
  --crimson-dim:  #D03030;
  --crimson-bg:   #FEF2F2;

  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 16px;

  --font-body: system-ui, -apple-system, 'Segoe UI', sans-serif;
  --font-mono: 'JetBrains Mono', 'Cascadia Code', 'Consolas', monospace;
}

/* ========== 全局 Reset ========== */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html, body, #app {
  height: 100%;
  background: var(--paper);
  color: var(--ink);
  font-family: var(--font-body);
  font-size: 14px;
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
}

a { color: var(--cobalt); text-decoration: none; }
button { font-family: inherit; cursor: pointer; border: none; }
input, textarea, select { font-family: inherit; }

/* ========== 壳布局 ========== */
.fullscreen-shell {
  height: 100%;
}

.shell {
  display: flex;
  height: 100%;
  overflow: hidden;
}

/* ========== 侧边栏 ========== */
.sidebar {
  width: 220px;
  min-width: 220px;
  background: var(--white);
  display: flex;
  flex-direction: column;
  border-right: 1px solid var(--border);
  user-select: none;
  position: relative;
  transition: width 0.2s ease, min-width 0.2s ease;
}
.sidebar.collapsed { width: 64px; min-width: 64px; }

.sidebar-brand {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 20px 18px;
  cursor: pointer;
  transition: opacity 0.15s;
  white-space: nowrap;
  overflow: hidden;
}
.sidebar-brand:hover { opacity: 0.7; }

.brand-icon {
  font-size: 20px;
  color: var(--cobalt);
  flex-shrink: 0;
  margin-left: -2px;
}
.brand-text {
  font-size: 16px;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--ink);
}

/* 导航 */
.sidebar-nav {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 0 12px;
}

.nav-btn {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--slate);
  font-size: 14px;
  font-weight: 500;
  transition: background 0.15s, color 0.15s;
  width: 100%;
  text-align: left;
  position: relative;
  white-space: nowrap;
}
.nav-btn:hover {
  background: var(--steel);
  color: var(--ink);
}
.nav-btn.active {
  background: var(--cobalt-bg);
  color: var(--cobalt);
  font-weight: 600;
}
.nav-btn.active::before {
  content: '';
  position: absolute;
  left: -12px;
  top: 8px;
  bottom: 8px;
  width: 3px;
  border-radius: 0 2px 2px 0;
  background: var(--cobalt);
}

.nav-icon {
  font-size: 16px;
  width: 20px;
  text-align: center;
  flex-shrink: 0;
}

/* 收缩态：隐藏文字，图标居中 */
.sidebar.collapsed .brand-text,
.sidebar.collapsed .nav-label,
.sidebar.collapsed .user-name,
.sidebar.collapsed .user-actions { display: none; }
.sidebar.collapsed .sidebar-brand { justify-content: center; padding: 20px 8px; }
.sidebar.collapsed .brand-icon { margin-left: 0; }
.sidebar.collapsed .nav-btn { justify-content: center; padding: 10px 8px; }
.sidebar.collapsed .sidebar-footer { justify-content: center; padding: 14px 8px; }

/* 收缩开关 */
.collapse-btn {
  position: absolute;
  right: -11px;
  bottom: 64px;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: var(--white);
  border: 1px solid var(--border);
  color: var(--slate);
  font-size: 12px;
  line-height: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 1px 4px rgba(19,26,48,0.12);
  z-index: 5;
  transition: color 0.15s, border-color 0.15s;
}
.collapse-btn:hover { color: var(--cobalt); border-color: var(--cobalt); }

/* 底部用户区 */
.sidebar-footer {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 14px 18px;
  border-top: 1px solid var(--border);
}

.user-badge {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--cobalt);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  flex-shrink: 0;
  cursor: pointer;
}

.user-name {
  flex: 1;
  font-size: 13px;
  color: var(--slate);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.user-actions { position: relative; }
.user-menu-btn {
  background: none; color: var(--muted); font-size: 16px; padding: 2px 6px;
  border-radius: var(--radius-sm); transition: color 0.15s;
}
.user-menu-btn:hover { color: var(--cobalt); }
.user-dropdown {
  position: absolute; bottom: 100%; right: 0; margin-bottom: 6px;
  background: var(--white); border: 1px solid var(--border);
  border-radius: var(--radius-sm); box-shadow: 0 8px 24px rgba(19,26,48,0.18);
  overflow: hidden; z-index: 20; min-width: 120px;
}
.user-dropdown button {
  display: block; width: 100%; padding: 9px 14px; background: none;
  color: var(--ink); font-size: 12px; text-align: left; transition: background 0.1s;
}
.user-dropdown button:hover { background: var(--steel); }
.user-dropdown button:last-child { color: var(--crimson); }

/* ========== 主内容区：铺在制图板上的坐标纸 ========== */
.main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  padding: 32px 40px;
  background-color: var(--paper);
  background-image:
    linear-gradient(var(--grid-line) 1px, transparent 1px),
    linear-gradient(90deg, var(--grid-line) 1px, transparent 1px);
  background-size: 28px 28px;
  min-height: 0;   /* flex child 高度约束 */
}

/* ========== 页面通用标题：图注式 ========== */
.page-header {
  margin-bottom: 28px;
}
.page-title {
  font-size: 24px;
  font-weight: 800;
  letter-spacing: -0.03em;
  color: var(--ink);
}
.page-subtitle {
  margin-top: 6px;
  color: var(--slate);
  font-size: 13px;
}
.page-subtitle::before {
  content: '';
  display: inline-block;
  width: 14px;
  height: 2px;
  background: var(--vermilion);
  margin-right: 8px;
  vertical-align: middle;
}

/* ========== 卡片：钉在板上的图纸 ========== */
.card {
  background: var(--white);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 20px;
  box-shadow: 0 1px 2px rgba(19,26,48,0.05), 0 10px 28px -18px rgba(19,26,48,0.14);
}

/* ========== 表单通用样式 ========== */
.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 16px;
}
.form-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--slate);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.form-input,
.form-select,
.form-textarea {
  background: var(--steel);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 10px 12px;
  color: var(--ink);
  font-size: 14px;
  outline: none;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.form-input:focus,
.form-select:focus,
.form-textarea:focus {
  border-color: var(--cobalt);
  box-shadow: 0 0 0 3px var(--cobalt-bg);
}
.form-input::placeholder,
.form-textarea::placeholder {
  color: var(--muted);
}
.form-textarea {
  resize: vertical;
  min-height: 80px;
}

/* ========== 按钮通用样式 ========== */
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 10px 20px;
  border-radius: var(--radius-sm);
  font-size: 14px;
  font-weight: 600;
  transition: background 0.15s, opacity 0.15s, box-shadow 0.15s;
}
.btn:disabled { opacity: 0.45; cursor: not-allowed; }

.btn-primary {
  background: var(--cobalt);
  color: #fff;
}
.btn-primary:hover:not(:disabled) { background: var(--cobalt-dim); }

.btn-danger {
  background: transparent;
  color: var(--crimson);
  border: 1px solid var(--crimson);
}
.btn-danger:hover:not(:disabled) { background: var(--crimson); color: #fff; }

.btn-ghost {
  background: transparent;
  color: var(--slate);
  border: 1px solid var(--border);
}
.btn-ghost:hover:not(:disabled) { background: var(--steel); color: var(--ink); }

.btn-secondary {
  background: var(--steel);
  color: var(--ink);
  border: 1px solid var(--border);
}
.btn-secondary:hover:not(:disabled) { background: var(--border); }

/* ========== 脉冲点（运行态指示器） ========== */
.pulse-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--amber);
  animation: pulse-glow 1.5s ease-in-out infinite;
}
@keyframes pulse-glow {
  0%, 100% { box-shadow: 0 0 0 0 rgba(232,149,10,0.5); }
  50%      { box-shadow: 0 0 0 6px rgba(232,149,10,0); }
}

/* ========== 滚动条 ========== */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--muted); }

/* ========== 可访问性 ========== */
:focus-visible {
  outline: 2px solid var(--cobalt);
  outline-offset: 2px;
  border-radius: 2px;
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
</style>
