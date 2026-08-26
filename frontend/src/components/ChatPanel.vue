<!-- ChatPanel.vue — 聊天面板（DeepSeek 风格：左侧会话列表 + 右侧聊天区）-->
<script setup>
import { ref, nextTick, onMounted, onUnmounted } from 'vue'
import { ChatClient } from '../api/chat'
import { useUserStore } from '../stores/user'
import api from '../api/index'

const userStore = useUserStore()

const messages = ref([])
const toolLog = ref([])      // Agent 工具调用日志（独立于消息流，避免挤掉流式回答）
const input = ref('')
const useAgent = ref(false)
const useWebSearch = ref(false)
const usePlanning = ref(false)
const sidebarCollapsed = ref(false)
const sending = ref(false)
const webSearchUsed = ref(false)
const chatEl = ref(null)
const showMenu = ref(false)
const uploading = ref('')
const loadingHistory = ref(false)

const connStatus = ref('idle')
const connError = ref('')
const currentSessionId = ref('')
const pendingConfirm = ref(null)
const allowForSession = ref(false)
const pendingPlan = ref(null)
const planAutoAllow = ref(false)
const showSkills = ref(false)
const skills = ref([])
const loadingSkills = ref(false)

// 会话列表
const sessions = ref([])
const loadingSessions = ref(false)

const statusText = { idle: '未连接', connecting: '连接中…', connected: '已连接', disconnected: '已断开', error: '连接失败' }

let client = null

function getClient() {
  if (!client) {
    client = new ChatClient()
    client.onMessage(handleChunk)
    client.onStatus((s) => { connStatus.value = s; if (s === 'connected') connError.value = '' })
    client.onError((msg) => { connError.value = msg })
    client.connect()
  }
  return client
}

function fmtArgs(args) {
  try {
    const s = JSON.stringify(args || {})
    return s.length > 60 ? s.slice(0, 60) + '…' : s
  } catch { return '' }
}

function handleChunk(chunk) {
  // 长程规划：展示整体计划与当前步骤
  if (chunk.type === 'plan') {
    toolLog.value.push(`🧭 长程规划：${(chunk.steps || []).map((s, i) => `${i + 1}. ${s}`).join('  |  ')}`)
    scrollBottom()
    return
  }
  if (chunk.type === 'plan_step') {
    toolLog.value.push(`⏳ 正在执行第 ${chunk.index}/${chunk.total} 步：${chunk.name}`)
    scrollBottom()
    return
  }
  // Agent 工具调用事件 → 独立日志区（不进 messages，否则会挤掉流式回答）
  if (chunk.type === 'tool_call') {
    toolLog.value.push(`📡 调用 ${chunk.name}(${fmtArgs(chunk.args)})`)
    scrollBottom()
    return
  }
  if (chunk.type === 'tool_result') {
    // run_command 的执行输出完整展示（可滚动），其他工具保持简短
    const result = String(chunk.result || '')
    const preview = chunk.name === 'run_command' ? result : result.slice(0, 120)
    toolLog.value.push(`✓ ${chunk.name} 返回：${preview}`)
    scrollBottom()
    return
  }
  if (chunk.type === 'web_search_used') {
    webSearchUsed.value = !!chunk.used
    return
  }
  if (chunk.type === 'confirm_request') {
    pendingConfirm.value = { id: chunk.id, prompt: chunk.prompt }
    return
  }
  if (chunk.type === 'plan_confirm_request') {
    pendingPlan.value = { id: chunk.id, steps: chunk.steps || [] }
    return
  }
  if (chunk.type === 'agent_stopped') {
    const last = messages.value[messages.value.length - 1]
    if (last && last.streaming) {
      last.streaming = false
      if (!last.content) last.content = '⏹ 已停止'
    }
    sending.value = false
    return
  }
  const last = messages.value[messages.value.length - 1]
  // 流式分片：只追加到最后一条 assistant 消息
  if (chunk.content && last && last.role === 'assistant') {
    last.content += chunk.content
    scrollBottom()
  }
  // 结束标记：无论当前最后一条消息是什么，都必须复位发送状态
  if (chunk.done) {
    if (last && last.role === 'assistant') {
      last.streaming = false
      last.webSearch = webSearchUsed.value
    }
    sending.value = false
    webSearchUsed.value = false
    loadSessions()
  }
}

function send(text) {
  const msg = (text || input.value).trim()
  if (!msg || sending.value) return

  if (!currentSessionId.value) currentSessionId.value = genSessionId()
  messages.value.push({ role: 'user', content: msg })
  messages.value.push({ role: 'assistant', content: '', streaming: true })
  toolLog.value = []
  webSearchUsed.value = false
  if (!text) input.value = ''
  sending.value = true; showMenu.value = false

  // user_id 不再传给后端：服务端从 WS 握手时的 JWT 解析
  getClient().send({ message: msg, use_agent: useAgent.value, web_search: useWebSearch.value, use_planning: usePlanning.value, session_id: currentSessionId.value })
  scrollBottom()
}

function scrollBottom() { nextTick(() => { if (chatEl.value) chatEl.value.scrollTop = chatEl.value.scrollHeight }) }
function onKeydown(e) { if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); send() } }
function reconnect() { connError.value = ''; if (client) { client.disconnect(); client = null }; getClient() }
function genSessionId() { return Date.now().toString(36) + Math.random().toString(36).slice(2, 8) }

// 文件上传
async function handleFileUpload(file, promptTemplate) {
  if (!file) return
  uploading.value = `正在上传 ${file.name}…`
  try {
    const formData = new FormData(); formData.append('file', file)
    const { data } = await api.post('/files/upload', formData, { headers: { 'Content-Type': 'multipart/form-data' } })
    uploading.value = ''
    const path = data.file_path || data.filename
    send(promptTemplate.replace('{path}', path))
  } catch (e) { uploading.value = ''; connError.value = '上传失败: ' + (e?.response?.data?.detail || e.message) }
}
function onPickImage(e) { handleFileUpload(e.target.files[0], '用 analyze_image 分析服务器文件: {path}，描述内容'); e.target.value = '' }
function onPickAudio(e) { handleFileUpload(e.target.files[0], '用 speech_to_text 转写音频文件: {path}，把文字提取出来'); e.target.value = '' }
function onPickDoc(e)   { handleFileUpload(e.target.files[0], '用 parse_document 解析文件: {path}，提取并总结内容'); e.target.value = '' }

// 会话
async function loadSessions() {
  loadingSessions.value = true
  try { sessions.value = (await api.get('/chat/sessions')).data || [] }
  catch { sessions.value = [] }
  finally { loadingSessions.value = false }
}
async function selectSession(sid) {
  if (sending.value) return
  loadingHistory.value = true
  currentSessionId.value = sid
  toolLog.value = []
  try {
    const { data } = await api.get('/chat/history', { params: { session_id: sid } })
    messages.value = (data || []).map(m => ({ role: m.role, content: m.content, streaming: false }))
    scrollBottom()
  } catch { messages.value = [] }
  finally { loadingHistory.value = false }
}
async function deleteSession(sid) {
  await api.delete(`/chat/sessions/${sid}`)
  if (currentSessionId.value === sid) { newChat() }
  loadSessions()
}
function newChat() {
  messages.value = []; toolLog.value = []; currentSessionId.value = ''; webSearchUsed.value = false
  loadSessions()
}
function stopReply() {
  // Agent 模式：发 stop 消息让后端取消 Agent 任务（否则断开 WS 后后台还在跑工具）
  if (useAgent.value && client?.ws?.readyState === WebSocket.OPEN) {
    client.send({ type: 'stop' })
    return
  }
  // 普通流式：断开当前 WebSocket → 重建连接 → 停止流式输出
  if (client) { client.disconnect(); client = null }
  const last = messages.value[messages.value.length - 1]
  if (last && last.streaming) {
    last.streaming = false
    if (!last.content) last.content = '（已停止）'
  }
  sending.value = false
  getClient()
}

async function loadSkills() {
  loadingSkills.value = true
  try { skills.value = (await api.get('/chat/skills')).data || [] } catch { skills.value = [] }
  finally { loadingSkills.value = false }
}
function openSkills() {
  showSkills.value = true
  loadSkills()
}
function closeSkills() {
  showSkills.value = false
}
function selectSkill(s) {
  showSkills.value = false
  // 选择技能：前缀标记走 Agent 执行（load_skill → 按 SKILL.md 操作）
  // 不再强制关闭规划：保留用户的规划开关，重任务（如做PPT）可先出计划经确认再执行
  useAgent.value = true
  const prefix = `[技能 ${s.name}] `
  input.value = input.value ? prefix + input.value : prefix
  nextTick(() => { document.querySelector('.chat-input')?.focus() })
}

function respondConfirm(allow) {
  if (!pendingConfirm.value) return
  getClient().send({ type: 'confirm_response', id: pendingConfirm.value.id, allow, allow_for_session: allowForSession.value })
  pendingConfirm.value = null
  allowForSession.value = false
}
function respondPlan(allow) {
  if (!pendingPlan.value) return
  getClient().send({
    type: 'plan_confirm_response',
    id: pendingPlan.value.id,
    allow,
    auto_allow: allow && planAutoAllow.value,
  })
  pendingPlan.value = null
  planAutoAllow.value = false
}

function onClickOutside(e) { if (!e.target.closest('.plus-area')) showMenu.value = false }

onMounted(() => { getClient(); loadSessions(); document.addEventListener('click', onClickOutside) })
onUnmounted(() => { client?.disconnect(); document.removeEventListener('click', onClickOutside) })
</script>

<template>
  <div class="chat-layout">
    <!-- 左侧会话列表 -->
    <aside v-show="!sidebarCollapsed" class="session-sidebar">
      <button class="new-chat-btn" @click="newChat">+ 新对话</button>
      <div class="session-list">
        <div v-if="loadingSessions" class="session-empty">加载中…</div>
        <div v-else-if="sessions.length === 0" class="session-empty">暂无对话</div>
        <div
          v-for="s in sessions" :key="s.session_id"
          :class="['session-item', { active: currentSessionId === s.session_id }]"
          @click="selectSession(s.session_id)"
        >
          <span class="session-title">{{ s.title }}</span>
          <span class="session-time">{{ s.time }}</span>
          <button class="session-del" @click.stop="deleteSession(s.session_id)" title="删除">×</button>
        </div>
      </div>
    </aside>

    <!-- 侧边栏折叠按钮 -->
    <button class="sidebar-toggle" :title="sidebarCollapsed ? '展开会话列表' : '收起会话列表'" @click="sidebarCollapsed = !sidebarCollapsed">
      {{ sidebarCollapsed ? '»' : '«' }}
    </button>

    <!-- 右侧聊天区 -->
    <div class="chat-panel card">
      <div class="chat-toolbar">
        <div class="mode-toggle">
          <button :class="['mode-btn', { active: !useAgent }]" @click="useAgent = false">普通</button>
          <button :class="['mode-btn', { active: useAgent }]" @click="useAgent = true">Agent</button>
        </div>
        <button
          :class="['web-search-btn', { active: useWebSearch }]"
          :title="useWebSearch ? '已开启联网搜索，回答前会先搜索最新信息' : '开启联网搜索（自动切换 Agent 模式）'"
          @click="useWebSearch = !useWebSearch"
        >
          🌐 联网
        </button>
        <button
          :class="['plan-btn', { active: usePlanning }]"
          :title="usePlanning ? '已开启长程规划，复杂任务自动拆解执行' : '开启长程规划：复杂任务自动拆解成多步执行'"
          @click="usePlanning = !usePlanning; if (usePlanning) useAgent = true"
        >
          🧭 规划
        </button>
        <button class="plan-btn skills-btn" title="查看已安装技能" @mouseenter="openSkills">
          🧩 技能 <span class="skills-caret">▾</span>
        </button>
        <div v-if="showSkills" class="skills-dropdown" @mouseleave="showSkills = false">
          <div class="skills-dd-head">
            <span>🧩 已安装技能</span>
            <span class="skills-dd-count">{{ skills.length }}</span>
          </div>
          <div v-if="loadingSkills" class="skills-empty">加载中…</div>
          <div v-else-if="skills.length === 0" class="skills-empty">
            尚未安装技能<br/><span class="skills-hint">对话中让 Agent 执行 install_skill 安装（如 pptx/docx/pdf/xlsx）</span>
          </div>
          <div v-else class="skills-dd-list">
            <div v-for="s in skills" :key="s.name" class="skill-dd-item" @click="selectSkill(s)">
              <div class="skill-name">{{ s.name }}</div>
              <div class="skill-desc">{{ s.description }}</div>
            </div>
          </div>
        </div>
        <span v-if="useAgent" class="agent-indicator"><span class="pulse-dot"></span> Agent</span>
        <span class="conn-status" :class="'conn-' + connStatus">
          <span class="conn-dot"></span>{{ statusText[connStatus] }}
        </span>
        <button v-if="connStatus === 'disconnected' || connStatus === 'error'" class="btn btn-ghost btn-xs" @click="reconnect">重连</button>
      </div>

      <div v-if="connError" class="conn-banner">{{ connError }}</div>
      <div v-if="uploading" class="upload-banner">{{ uploading }}</div>

      <!-- 长程规划确认弹窗 -->
      <div v-if="pendingPlan" class="confirm-overlay">
        <div class="confirm-modal plan-modal">
          <div class="confirm-icon">🧭</div>
          <div class="confirm-title">执行计划确认</div>
          <div class="plan-steps">
            <div v-for="(s, i) in pendingPlan.steps" :key="i" class="plan-step">
              <span class="plan-step-no">{{ i + 1 }}</span>
              <div class="plan-step-body">
                <div class="plan-step-name">{{ s.name }}</div>
                <div class="plan-step-action">{{ s.action }}</div>
              </div>
            </div>
          </div>
          <label class="confirm-checkbox">
            <input type="checkbox" v-model="planAutoAllow" />
            <span>自动允许本计划内的后续操作（执行中不再逐个询问）</span>
          </label>
          <div class="confirm-actions">
            <button class="btn btn-ghost confirm-btn" @click="respondPlan(false)">取消</button>
            <button class="btn btn-primary confirm-btn" @click="respondPlan(true)">开始执行</button>
          </div>
        </div>
      </div>

      <!-- 高危命令人工确认弹窗 -->
      <div v-if="pendingConfirm" class="confirm-overlay">
        <div class="confirm-modal">
          <div class="confirm-icon">⚠️</div>
          <div class="confirm-title">需要人工确认</div>
          <div class="confirm-prompt">{{ pendingConfirm.prompt }}</div>
          <label class="confirm-checkbox">
            <input type="checkbox" v-model="allowForSession" />
            <span>本次会话不再询问同类操作</span>
          </label>
          <div class="confirm-actions">
            <button class="btn btn-ghost confirm-btn" @click="respondConfirm(false)">拒绝</button>
            <button class="btn btn-danger confirm-btn" @click="respondConfirm(true)">允许执行</button>
          </div>
        </div>
      </div>

      <div ref="chatEl" class="chat-messages">
        <div v-if="messages.length === 0" class="chat-empty">
          <div class="empty-title">TaskBench AI</div>
          <div class="empty-hint">普通模式自由对话 · Agent 模式 AI 自主调用 24 种工具<br/>点击 + 上传图片、音频、文档</div>
        </div>
        <div v-for="(msg, i) in messages" :key="i" :class="['msg-row', 'msg-' + msg.role]">
          <div class="msg-bubble">
            <span v-if="msg.webSearch" class="search-badge">🌐 已联网搜索</span>
            <span class="msg-text">{{ msg.content }}</span>
            <span v-if="msg.streaming" class="typing-cursor">▌</span>
          </div>
        </div>
        <div v-if="sending && messages.length > 0 && messages[messages.length - 1].content === ''" class="msg-row msg-assistant">
          <div class="msg-bubble loading-bubble"><span class="loading-dots"><span>.</span><span>.</span><span>.</span></span></div>
        </div>
      </div>
      <div v-if="toolLog.length > 0" class="tool-log">
        <div class="tool-log-head">🛠 Agent 工具调用 <span class="tool-log-count">{{ toolLog.length }}</span></div>
        <div v-for="(line, i) in toolLog" :key="i" class="tool-log-line">{{ line }}</div>
      </div>

      <div class="chat-input-area">
        <div class="plus-area">
          <button class="plus-btn" @click.stop="showMenu = !showMenu">+</button>
          <div v-if="showMenu" class="plus-menu">
            <label class="plus-item"><span class="plus-icon">◰</span>上传图片<input type="file" accept="image/*" hidden @change="onPickImage" /></label>
            <label class="plus-item"><span class="plus-icon">◷</span>上传音频<input type="file" accept="audio/*" hidden @change="onPickAudio" /></label>
            <label class="plus-item"><span class="plus-icon">▣</span>上传文档<input type="file" accept=".pdf,.docx,.doc,.txt,.md,.json,.csv" hidden @change="onPickDoc" /></label>
          </div>
        </div>
        <textarea v-model="input" class="chat-input" placeholder="输入消息… Enter 发送" rows="1" @keydown="onKeydown"></textarea>
        <button v-if="sending" class="btn btn-danger stop-btn" @click="stopReply">停止</button>
        <button v-else class="btn btn-primary send-btn" :disabled="!input.trim()" @click="send()">发送</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.chat-layout { display: flex; flex: 1; min-height: 0; gap: 0; }

/* ===== 左侧会话列表 ===== */
.session-sidebar {
  width: 220px; min-width: 220px; background: var(--white);
  border-right: 1px solid var(--border); display: flex; flex-direction: column;
  border-radius: var(--radius-md) 0 0 var(--radius-md); overflow: hidden;
}
.new-chat-btn {
  margin: 12px; padding: 8px; border-radius: var(--radius-sm);
  background: var(--cobalt); color: #fff; font-size: 13px; font-weight: 600; transition: opacity 0.15s;
}
.new-chat-btn:hover { opacity: 0.85; }
.session-list { flex: 1; overflow-y: auto; padding: 0 8px 8px; display: flex; flex-direction: column; gap: 2px; }
.session-empty { text-align: center; padding: 24px 12px; color: var(--muted); font-size: 12px; }
.session-item {
  display: flex; align-items: center; gap: 6px; padding: 8px 10px;
  border-radius: var(--radius-sm); cursor: pointer; transition: background 0.1s; position: relative;
}
.session-item:hover { background: var(--steel); }
.session-item.active { background: var(--cobalt-bg); }
.session-title { flex: 1; font-size: 12px; color: var(--ink); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.session-time { font-size: 10px; color: var(--muted); flex-shrink: 0; }
.session-del { background: none; color: var(--muted); font-size: 14px; padding: 0 2px; opacity: 0; transition: opacity 0.1s; }
.session-item:hover .session-del { opacity: 1; }
.session-del:hover { color: var(--crimson); }

/* ===== 侧边栏折叠按钮 ===== */
.sidebar-toggle {
  width: 18px; min-width: 18px; align-self: center; padding: 10px 0;
  background: var(--steel); color: var(--slate); border-radius: 0 4px 4px 0;
  font-size: 12px; font-weight: 700; transition: all 0.15s; cursor: pointer;
}
.sidebar-toggle:hover { background: var(--border); color: var(--ink); }

/* ===== 聊天区 ===== */
.chat-panel { display: flex; flex-direction: column; flex: 1; min-height: 400px; overflow: hidden; border-radius: 0 var(--radius-md) var(--radius-md) 0; position: relative; }
.btn-xs { padding: 3px 10px; font-size: 11px; }
.chat-toolbar { display: flex; align-items: center; gap: 10px; padding-bottom: 14px; border-bottom: 1px solid var(--border); margin-bottom: 4px; flex-shrink: 0; flex-wrap: wrap; }
.mode-toggle { display: flex; background: var(--steel); border-radius: var(--radius-sm); overflow: hidden; }
.mode-btn { padding: 5px 12px; font-size: 11px; font-weight: 600; background: transparent; color: var(--slate); transition: all 0.15s; }
.mode-btn.active { background: var(--cobalt); color: #fff; }
.web-search-btn,
.plan-btn {
  padding: 5px 12px; font-size: 11px; font-weight: 600; border-radius: var(--radius-sm);
  background: var(--steel); color: var(--slate); border: 1px solid var(--border);
  transition: all 0.15s; cursor: pointer;
}
.web-search-btn:hover, .plan-btn:hover { background: var(--border); color: var(--ink); }
.web-search-btn.active { background: var(--verdant); border-color: var(--verdant); color: #fff; }
.plan-btn.active { background: var(--amber); border-color: var(--amber); color: #fff; }
.agent-indicator { font-size: 11px; color: var(--amber); display: flex; align-items: center; gap: 5px; }
.conn-status { font-size: 11px; display: flex; align-items: center; gap: 5px; margin-left: auto; }
.conn-dot { width: 6px; height: 6px; border-radius: 50%; }
.conn-idle .conn-dot, .conn-disconnected .conn-dot { background: var(--muted); }
.conn-connecting .conn-dot { background: var(--amber); animation: pulse-glow 1s ease-in-out infinite; }
.conn-connected .conn-dot { background: var(--verdant); }
.conn-error .conn-dot { background: var(--crimson); }
.conn-banner, .upload-banner { padding: 8px 14px; margin-bottom: 8px; border-radius: var(--radius-sm); font-size: 12px; flex-shrink: 0; }
.conn-banner { background: var(--crimson-bg); color: var(--crimson); }
.upload-banner { background: var(--cobalt-bg); color: var(--cobalt); }

/* ===== 高危命令确认弹窗 ===== */
.confirm-overlay {
  position: absolute; inset: 0; z-index: 50;
  background: rgba(15, 23, 42, 0.45); display: flex;
  align-items: center; justify-content: center;
}
.confirm-modal {
  width: 420px; max-width: 90%; background: var(--white);
  border: 1px solid var(--border); border-radius: var(--radius-md);
  padding: 20px; box-shadow: 0 12px 40px rgba(0, 0, 0, 0.18);
}
.confirm-icon { font-size: 28px; margin-bottom: 8px; }
.confirm-title { font-size: 15px; font-weight: 700; color: var(--crimson); margin-bottom: 8px; }
.confirm-prompt {
  font-size: 13px; color: var(--ink); line-height: 1.6;
  background: var(--steel); border-radius: var(--radius-sm);
  padding: 10px 12px; margin-bottom: 16px; white-space: pre-wrap;
  word-break: break-all; font-family: var(--font-mono);
}
.confirm-actions { display: flex; gap: 10px; justify-content: flex-end; }
.confirm-btn { padding: 8px 18px; }
.confirm-checkbox { display: flex; align-items: center; gap: 6px; margin: 8px 0 4px; font-size: 13px; color: var(--text-muted); cursor: pointer; }
.confirm-checkbox input { width: 16px; height: 16px; accent-color: var(--crimson); cursor: pointer; }

/* 规划确认弹窗：步骤列表 */
.plan-modal { width: 520px; }
.plan-steps { max-height: 280px; overflow-y: auto; margin-bottom: 16px; display: flex; flex-direction: column; gap: 8px; }
.plan-step {
  display: flex; gap: 10px; padding: 10px 12px; background: var(--steel);
  border-radius: var(--radius-sm); border-left: 3px solid var(--amber);
}
.plan-step-no {
  flex-shrink: 0; width: 22px; height: 22px; border-radius: 50%;
  background: var(--cobalt); color: #fff; font-size: 12px; font-weight: 700;
  display: flex; align-items: center; justify-content: center;
}
.plan-step-body { flex: 1; min-width: 0; }
.plan-step-name { font-size: 13px; font-weight: 700; color: var(--ink); }
.plan-step-action { font-size: 12px; color: var(--slate); margin-top: 2px; line-height: 1.5; word-break: break-all; }

.chat-messages { flex: 1; overflow-y: auto; padding: 16px 0; display: flex; flex-direction: column; gap: 12px; min-height: 0; }
.chat-empty { text-align: center; padding: 64px 16px; color: var(--slate); }
.empty-title { font-size: 20px; font-weight: 700; color: var(--ink); margin-bottom: 10px; }
.empty-hint { font-size: 12px; line-height: 1.8; color: var(--slate); }
.msg-row { display: flex; }
.msg-user { justify-content: flex-end; }
.msg-bubble { max-width: 78%; padding: 10px 16px; border-radius: var(--radius-md); font-size: 14px; line-height: 1.65; white-space: pre-wrap; word-break: break-word; }
.msg-user .msg-bubble { background: var(--cobalt); color: #fff; border-bottom-right-radius: 4px; }
.msg-assistant .msg-bubble { background: var(--steel); color: var(--ink); border-bottom-left-radius: 4px; }
.search-badge {
  display: inline-block; margin-bottom: 6px; padding: 2px 8px;
  background: var(--verdant-bg, #e3f4ec); color: var(--verdant);
  border-radius: 999px; font-size: 10px; font-weight: 600;
}
.loading-bubble { padding: 14px 24px; }
.loading-dots span { display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: var(--muted); margin: 0 2px; animation: dot-bounce 1.2s ease-in-out infinite; }
.loading-dots span:nth-child(2) { animation-delay: 0.2s; }
.loading-dots span:nth-child(3) { animation-delay: 0.4s; }
@keyframes dot-bounce { 0%, 100% { transform: translateY(0); opacity: 0.3; } 50% { transform: translateY(-6px); opacity: 1; } }
.typing-cursor { animation: blink 0.8s step-end infinite; color: var(--cobalt); }
@keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }

/* ===== 技能下拉菜单 ===== */
.skills-btn { position: relative; }
.skills-caret { font-size: 9px; margin-left: 3px; }
.skills-dropdown {
  position: absolute; top: 38px; left: 0; z-index: 60;
  width: 320px; background: var(--white); border: 1px solid var(--border);
  border-radius: var(--radius-md); box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
  overflow: hidden;
}
.skills-dd-head {
  display: flex; align-items: center; justify-content: space-between;
  padding: 8px 12px; font-size: 12px; font-weight: 700; color: var(--ink);
  border-bottom: 1px solid var(--border); background: var(--steel);
}
.skills-dd-count { font-size: 11px; color: var(--muted); font-weight: 400; }
.skills-empty { padding: 16px; text-align: center; font-size: 12px; color: var(--slate); line-height: 1.8; }
.skills-hint { font-size: 11px; color: var(--muted); }
.skills-dd-list { max-height: 260px; overflow-y: auto; padding: 6px; display: flex; flex-direction: column; gap: 4px; }
.skill-dd-item {
  padding: 8px 10px; border-radius: var(--radius-sm); cursor: pointer;
  background: var(--steel); border-left: 3px solid var(--amber);
  transition: background 0.1s;
}
.skill-dd-item:hover { background: var(--cobalt-bg); border-left-color: var(--cobalt); }
.skill-name { font-size: 12px; font-weight: 700; color: var(--ink); font-family: var(--font-mono); }
.skill-desc { font-size: 11px; color: var(--slate); margin-top: 2px; line-height: 1.5; }

/* Agent 工具调用日志 */
.tool-log {
  max-height: 140px; overflow-y: auto; margin-top: 10px; padding: 10px 12px;
  background: var(--cobalt-bg); border: 1px dashed var(--cobalt); border-radius: var(--radius-sm);
  font-size: 12px; font-family: var(--font-mono); flex-shrink: 0;
}
.tool-log-head { font-weight: 700; color: var(--cobalt); margin-bottom: 6px; }
.tool-log-count { font-weight: 400; color: var(--slate); margin-left: 4px; }
.tool-log-line { color: var(--ink); line-height: 1.7; word-break: break-all; }

.chat-input-area { display: flex; gap: 8px; padding-top: 14px; border-top: 1px solid var(--border); flex-shrink: 0; align-items: flex-end; }
.plus-area { position: relative; flex-shrink: 0; }
.plus-btn { width: 42px; height: 42px; border-radius: var(--radius-sm); background: var(--steel); color: var(--slate); font-size: 22px; display: flex; align-items: center; justify-content: center; transition: all 0.15s; }
.plus-btn:hover { background: var(--border); color: var(--ink); }
.plus-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.plus-menu { position: absolute; bottom: 50px; left: 0; background: var(--white); border: 1px solid var(--border); border-radius: var(--radius-md); box-shadow: 0 4px 16px rgba(0,0,0,0.1); overflow: hidden; z-index: 10; min-width: 130px; }
.plus-item { display: flex; align-items: center; gap: 8px; padding: 10px 14px; font-size: 13px; color: var(--ink); cursor: pointer; transition: background 0.1s; }
.plus-item:hover { background: var(--steel); }
.plus-icon { font-size: 15px; width: 20px; text-align: center; }
.chat-input { flex: 1; background: var(--steel); border: 1px solid var(--border); border-radius: var(--radius-sm); padding: 0 14px; color: var(--ink); font-size: 14px; font-family: inherit; resize: none; outline: none; height: 42px; line-height: 42px; overflow: hidden; transition: border-color 0.15s; }
.chat-input:focus { border-color: var(--cobalt); }
.chat-input::placeholder { color: var(--muted); }
.send-btn { height: 42px; padding: 0 22px; flex-shrink: 0; }
.stop-btn { height: 42px; padding: 0 16px; flex-shrink: 0; font-size: 13px; }
</style>
