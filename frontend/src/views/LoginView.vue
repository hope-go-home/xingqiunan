<!-- LoginView.vue — 登录 / 注册页。同一页面切换模式。 -->
<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'

const router = useRouter()
const userStore = useUserStore()

const mode = ref(0)        // 0=登录, 1=注册
const form = reactive({ username: '', password: '' })
const error = ref('')
const submitting = ref(false)

async function submit() {
  error.value = ''
  submitting.value = true
  try {
    if (mode.value === 0) {
      await userStore.loginAction({ username: form.username, password: form.password })
      router.push('/dashboard')
    } else {
      await userStore.registerAction({ username: form.username, password: form.password })
      mode.value = 0
      form.password = ''
    }
  } catch (e) {
    error.value = e?.response?.data?.detail || e?.message || '操作失败'
  } finally {
    submitting.value = false
  }
}

function toggleMode() {
  mode.value = mode.value === 0 ? 1 : 0
  error.value = ''
  form.password = ''
}
</script>

<template>
  <div class="login-page">
    <!-- 左侧品牌区 -->
    <div class="login-hero">
      <div class="hero-content">
        <div class="hero-logo">◆</div>
        <h1 class="hero-title">TaskBench</h1>
        <p class="hero-desc">智能任务自动化工作台<br/>AI 驱动的任务编排与知识管理</p>
      </div>
      <div class="hero-pulses">
        <span class="hero-pulse" style="--delay: 0s"></span>
        <span class="hero-pulse" style="--delay: 0.6s"></span>
        <span class="hero-pulse" style="--delay: 1.2s"></span>
      </div>
    </div>

    <!-- 右侧表单区 -->
    <div class="login-panel">
      <div class="login-card">
        <h2 class="card-heading">{{ mode === 0 ? '登录' : '注册' }}</h2>

        <div v-if="error" class="alert" :class="mode === 0 ? 'alert-error' : 'alert-success'">
          {{ error }}
        </div>

        <form @submit.prevent="submit" class="login-form">
          <div class="form-group">
            <label class="form-label">用户名</label>
            <input v-model="form.username" class="form-input" type="text"
              placeholder="输入用户名" autocomplete="username" required />
          </div>

          <div class="form-group">
            <label class="form-label">密码</label>
            <input v-model="form.password" class="form-input" type="password"
              placeholder="至少 6 位" autocomplete="current-password" required minlength="6" />
          </div>

          <button class="btn btn-primary login-submit" :disabled="submitting">
            {{ submitting ? '处理中…' : (mode === 0 ? '登录' : '注册') }}
          </button>
        </form>

        <p class="login-switch">
          {{ mode === 0 ? '没有账号？' : '已有账号？' }}
          <button class="link-btn" @click="toggleMode">
            {{ mode === 0 ? '立即注册' : '去登录' }}
          </button>
        </p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-page { display: flex; height: 100%; background: var(--paper); }

/* 左侧品牌区 */
.login-hero {
  flex: 1; display: flex; flex-direction: column; align-items: center;
  justify-content: center; background: linear-gradient(135deg, #EEF1FE 0%, #F8F9FB 100%);
  position: relative; overflow: hidden;
}
.hero-content { text-align: center; z-index: 1; }
.hero-logo { font-size: 48px; color: var(--cobalt); margin-bottom: 16px; }
.hero-title { font-size: 32px; font-weight: 800; letter-spacing: -0.03em; color: var(--ink); margin-bottom: 12px; }
.hero-desc { color: var(--slate); font-size: 14px; line-height: 1.8; }

.hero-pulses { position: absolute; bottom: 60px; display: flex; gap: 24px; }
.hero-pulse {
  display: block; width: 12px; height: 12px; border-radius: 50%;
  background: var(--cobalt); animation: hero-anim 2s ease-in-out infinite;
  animation-delay: var(--delay); opacity: 0.25;
}
@keyframes hero-anim {
  0%, 100% { transform: scale(1); opacity: 0.25; }
  50%      { transform: scale(2.5); opacity: 0; }
}

/* 右侧表单区 */
.login-panel { width: 440px; min-width: 440px; display: flex; align-items: center; justify-content: center; padding: 40px; background: var(--white); }
.login-card { width: 100%; max-width: 360px; }
.card-heading { font-size: 24px; font-weight: 700; letter-spacing: -0.02em; color: var(--ink); margin-bottom: 24px; }

.alert { padding: 10px 14px; border-radius: var(--radius-sm); font-size: 13px; margin-bottom: 20px; }
.alert-error   { background: var(--crimson-bg); color: var(--crimson); border: 1px solid rgba(239,68,68,0.2); }
.alert-success { background: var(--verdant-bg); color: var(--verdant); border: 1px solid rgba(16,185,129,0.2); }

.login-form { display: flex; flex-direction: column; }
.login-submit { width: 100%; margin-top: 8px; padding: 12px; font-size: 15px; }

.login-switch { margin-top: 20px; text-align: center; font-size: 13px; color: var(--slate); }
.link-btn { background: none; color: var(--cobalt); font-size: 13px; font-weight: 600; padding: 0; margin-left: 4px; }
.link-btn:hover { text-decoration: underline; }

@media (max-width: 720px) {
  .login-hero { display: none; }
  .login-panel { width: 100%; min-width: unset; }
}
</style>
