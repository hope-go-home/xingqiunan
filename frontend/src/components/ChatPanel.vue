<!-- ChatPanel.vue — 聊天面板（DeepSeek 风格：左侧会话列表 + 右侧聊天区）-->
<script setup>
import { ref, nextTick, onMounted, onUnmounted } from 'vue'
import { ChatClient } from '../api/chat'
import { useUserStore } from '../stores/user'
import api from '../api/index'

const userStore = useUserStore()

const messages = ref([])
const input = ref('')
const useAgent = ref(false)
const sending = ref(false)
const chatEl = ref(null)
const showMenu = ref(false)
const uploading = ref('')
const loadingHistory = ref(false)

const connStatus = ref('idle')
const connError = ref('')
const currentSessionId = ref('')

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
  // Agent 工具调用事件
  if (chunk.type === 'tool_call') {
    messages.value.push({ role: 'tool', content: `📡 调用 ${chunk.name}(${fmtArgs(chunk.args)})` })
    scrollBottom()
    return
  }
  if (chunk.type === 'tool_result') {
    messages.value.push({ role: 'tool', content: `✓ ${chunk.name} 返回：${String(chunk.result || '').slice(0, 120)}` })
    scrollBottom()
    return
  }
  const last = messages.value[messages.value.length - 1]
  if (!last || last.role !== 'assistant') return
  if (chunk.content) { last.content += chunk.content; scrollBottom() }
  if (chunk.done) { last.streaming = false; sending.value = false; loadSessions() }
}

function send(text) {
  const msg = (text || input.value).trim()
  if (!msg || sending.value) return

  if (!currentSessionId.value) currentSessionId.value = genSessionId()
  messages.value.push({ role: 'user', content: msg })
  messages.value.push({ role: 'assistant', content: '', streaming: true })
  if (!text) input.value = ''
  sending.value = true; showMenu.value = false

  getClient().send({ message: msg, use_agent: useAgent.value, session_id: currentSessionId.value, user_id: userStore.user?.id || 0 })
  scrollBottom()
}

function scrollBottom() { nextTick(() => { if (chatEl.value) chatEl.value.scrollTop = chatEl.value.scrollHeight }) }
function onKeydown(e) { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }
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
  messages.value = []; currentSessionId.value = ''
  loadSessions()
}
function stopReply() {
  // 断开当前 WebSocket → 重建连接 → 停止流式输出
  if (client) { client.disconnect(); client = null }
  const last = messages.value[messages.value.length - 1]
  if (last && last.streaming) {
    last.streaming = false
    if (!last.content) last.content = '（已停止）'
  }
  sending.value = false
  getClient()
}

function onClickOutside(e) { if (!e.target.closest('.plus-area')) showMenu.value = false }

onMounted(() => { getClient(); loadSessions(); document.addEventListener('click', onClickOutside) })
onUnmounted(() => { client?.disconnect(); document.removeEventListener('click', onClickOutside) })
</script>

<template>
  <div class="chat-layout">
    <!-- 左侧会话列表 -->
    <aside class="session-sidebar">
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

    <!-- 右侧聊天区 -->
    <div class="chat-panel card">
      <div class="chat-toolbar">
        <div class="mode-toggle">
          <button :class="['mode-btn', { active: !useAgent }]" @click="useAgent = false">普通</button>
          <button :class="['mode-btn', { active: useAgent }]" @click="useAgent = true">Agent</button>
        </div>
        <span v-if="useAgent" class="agent-indicator"><span class="pulse-dot"></span> Agent</span>
        <span class="conn-status" :class="'conn-' + connStatus">
          <span class="conn-dot"></span>{{ statusText[connStatus] }}
        </span>
        <button v-if="connStatus === 'disconnected' || connStatus === 'error'" class="btn btn-ghost btn-xs" @click="reconnect">重连</button>
      </div>

      <div v-if="connError" class="conn-banner">{{ connError }}</div>
      <div v-if="uploading" class="upload-banner">{{ uploading }}</div>

      <div ref="chatEl" class="chat-messages">
        <div v-if="messages.length === 0" class="chat-empty">
          <div class="empty-title">TaskBench AI</div>
          <div class="empty-hint">普通模式自由对话 · Agent 模式 AI 自主调用 12 种工具<br/>点击 + 上传图片、音频、文档</div>
        </div>
        <div v-for="(msg, i) in messages" :key="i" :class="['msg-row', 'msg-' + msg.role]">
          <div class="msg-bubble">
            <span class="msg-text">{{ msg.content }}</span>
            <span v-if="msg.streaming" class="typing-cursor">▌</span>
          </div>
        </div>
        <div v-if="sending && messages.length > 0 && messages[messages.length - 1].content === ''" class="msg-row msg-assistant">
          <div class="msg-bubble loading-bubble"><span class="loading-dots"><span>.</span><span>.</span><span>.</span></span></div>
        </div>
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

/* ===== 聊天区 ===== */
.chat-panel { display: flex; flex-direction: column; flex: 1; min-height: 400px; overflow: hidden; border-radius: 0 var(--radius-md) var(--radius-md) 0; }
.btn-xs { padding: 3px 10px; font-size: 11px; }
.chat-toolbar { display: flex; align-items: center; gap: 10px; padding-bottom: 14px; border-bottom: 1px solid var(--border); margin-bottom: 4px; flex-shrink: 0; flex-wrap: wrap; }
.mode-toggle { display: flex; background: var(--steel); border-radius: var(--radius-sm); overflow: hidden; }
.mode-btn { padding: 5px 12px; font-size: 11px; font-weight: 600; background: transparent; color: var(--slate); transition: all 0.15s; }
.mode-btn.active { background: var(--cobalt); color: #fff; }
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

.chat-messages { flex: 1; overflow-y: auto; padding: 16px 0; display: flex; flex-direction: column; gap: 12px; min-height: 0; }
.chat-empty { text-align: center; padding: 64px 16px; color: var(--slate); }
.empty-title { font-size: 20px; font-weight: 700; color: var(--ink); margin-bottom: 10px; }
.empty-hint { font-size: 12px; line-height: 1.8; color: var(--slate); }
.msg-row { display: flex; }
.msg-user { justify-content: flex-end; }
.msg-bubble { max-width: 78%; padding: 10px 16px; border-radius: var(--radius-md); font-size: 14px; line-height: 1.65; white-space: pre-wrap; word-break: break-word; }
.msg-user .msg-bubble { background: var(--cobalt); color: #fff; border-bottom-right-radius: 4px; }
.msg-assistant .msg-bubble { background: var(--steel); color: var(--ink); border-bottom-left-radius: 4px; }
.msg-tool { justify-content: flex-start; }
.msg-tool .msg-bubble {
  background: var(--cobalt-bg); color: var(--cobalt);
  font-size: 12px; font-family: ui-monospace, Consolas, monospace;
  padding: 6px 12px; border-radius: var(--radius-sm);
  border: 1px dashed var(--cobalt); max-width: 92%;
}
.loading-bubble { padding: 14px 24px; }
.loading-dots span { display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: var(--muted); margin: 0 2px; animation: dot-bounce 1.2s ease-in-out infinite; }
.loading-dots span:nth-child(2) { animation-delay: 0.2s; }
.loading-dots span:nth-child(3) { animation-delay: 0.4s; }
@keyframes dot-bounce { 0%, 100% { transform: translateY(0); opacity: 0.3; } 50% { transform: translateY(-6px); opacity: 1; } }
.typing-cursor { animation: blink 0.8s step-end infinite; color: var(--cobalt); }
@keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }

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
