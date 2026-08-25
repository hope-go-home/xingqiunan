<!-- KnowledgeView.vue — 知识库管理页。添加 / 搜索 / 列表 / 删除。 -->
<script setup>
import { ref, onMounted } from 'vue'
import api from '../api/index'

// 添加文档（粘贴文本）
const addText = ref('')
const adding = ref(false)
const addMsg = ref('')

async function handleAdd() {
  if (!addText.value.trim()) return
  adding.value = true; addMsg.value = ''
  try {
    const { data } = await api.post('/knowledge/add', null, { params: { text: addText.value.trim() } })
    addMsg.value = '已添加 (ID: ' + data.doc_id + ')'
    addText.value = ''
    fetchList()
  } catch (e) {
    addMsg.value = e?.response?.data?.detail || '添加失败'
  } finally { adding.value = false }
}

// 上传本地文件到知识库
const uploadFile = ref(null)
const uploading = ref(false)
const uploadMsg = ref('')

function onFileChange(e) {
  uploadFile.value = e.target.files[0] || null
  uploadMsg.value = ''
}

async function handleUpload() {
  if (!uploadFile.value) return
  uploading.value = true; uploadMsg.value = ''
  try {
    const fd = new FormData()
    fd.append('file', uploadFile.value)
    const { data } = await api.post('/knowledge/upload', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    uploadMsg.value = '已上传：' + data.filename + '（' + data.doc_ids.length + ' 个分块）'
    uploadFile.value = null
    document.getElementById('kb-file-input').value = ''
    fetchList()
  } catch (e) {
    uploadMsg.value = e?.response?.data?.detail || '上传失败'
  } finally { uploading.value = false }
}

// 搜索
const query = ref('')
const topK = ref(5)
const searching = ref(false)
const searchResults = ref([])

async function handleSearch() {
  if (!query.value.trim()) return
  searching.value = true
  try {
    const { data } = await api.get('/knowledge/search', { params: { query: query.value.trim(), top_k: topK.value } })
    searchResults.value = data.results || []
  } finally { searching.value = false }
}

// 中文输入法组合状态下的回车不触发搜索
function onSearchEnter(e) { if (e.isComposing) return; handleSearch() }

// 文档列表
const documents = ref([])
const listLoading = ref(false)

async function fetchList() {
  listLoading.value = true
  try {
    const { data } = await api.get('/knowledge/list')
    documents.value = data.documents || []
  } finally { listLoading.value = false }
}

async function handleDelete(docId) {
  try {
    await api.delete('/knowledge/' + docId)
    documents.value = documents.value.filter(d => d.id !== docId)
  } catch { /* ignore */ }
}

onMounted(fetchList)
</script>

<template>
  <div class="knowledge-page">
    <div class="page-header">
      <h1 class="page-title">知识库</h1>
      <p class="page-subtitle">管理文档知识，支持语义检索</p>
    </div>

    <div class="kb-layout">
      <aside class="kb-sidebar">
        <!-- 添加文档 -->
        <div class="card">
          <h2 class="section-title">添加文档</h2>
          <div class="form-group">
            <textarea v-model="addText" class="form-textarea" placeholder="粘贴文档内容…" rows="5"></textarea>
          </div>
          <button class="btn btn-primary" style="width:100%" :disabled="adding" @click="handleAdd">
            {{ adding ? '添加中…' : '添加到知识库' }}
          </button>
          <p v-if="addMsg" class="kb-msg" :class="{ 'msg-ok': addMsg.includes('已添加') }">{{ addMsg }}</p>

          <div class="upload-divider"><span>或上传本地文件</span></div>
          <div class="form-group">
            <input id="kb-file-input" type="file" class="form-file" @change="onFileChange"
                   accept=".txt,.md,.pdf,.docx,.json,.csv,.xml,.html,.py,.yaml,.yml,.ini,.cfg,.log" />
          </div>
          <button class="btn btn-secondary" style="width:100%" :disabled="uploading || !uploadFile" @click="handleUpload">
            {{ uploading ? '上传中…' : '上传文件到知识库' }}
          </button>
          <p v-if="uploadMsg" class="kb-msg" :class="{ 'msg-ok': uploadMsg.includes('已上传') }">{{ uploadMsg }}</p>
        </div>

        <!-- 语义搜索 -->
        <div class="card">
          <h2 class="section-title">语义搜索</h2>
          <div class="form-group">
            <input v-model="query" class="form-input" placeholder="输入搜索关键词…" @keyup.enter="onSearchEnter" />
          </div>
          <div class="form-group">
            <label class="form-label">返回数量</label>
            <select v-model.number="topK" class="form-select">
              <option :value="3">3</option>
              <option :value="5">5</option>
              <option :value="10">10</option>
            </select>
          </div>
          <button class="btn btn-primary" style="width:100%" :disabled="searching" @click="handleSearch">
            {{ searching ? '搜索中…' : '搜索' }}
          </button>
          <div v-if="searchResults.length > 0" class="search-results">
            <div v-for="(item, i) in searchResults" :key="i" class="search-item">
              <div class="search-score">相关度 {{ (1 - item.score).toFixed(3) }}</div>
              <p class="search-content">{{ item.content }}</p>
            </div>
          </div>
        </div>
      </aside>

      <section class="kb-main card">
        <div class="section-head">
          <h2 class="section-title">全部文档</h2>
          <span class="doc-count">{{ documents.length }} 篇</span>
        </div>
        <div v-if="listLoading" class="empty-hint">加载中…</div>
        <div v-else-if="documents.length === 0" class="empty-state">
          <div class="empty-icon">▣</div>
          <p>知识库为空，添加第一篇文档吧</p>
        </div>
        <div v-else class="doc-list">
          <div v-for="doc in documents" :key="doc.id" class="doc-row">
            <div class="doc-body">
              <span class="doc-id">{{ doc.id.slice(0, 8) }}…</span>
              <p class="doc-content">{{ doc.content }}</p>
            </div>
            <button class="btn btn-danger btn-sm" @click="handleDelete(doc.id)">删除</button>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.knowledge-page { max-width: 1100px; }
.kb-layout { display: grid; grid-template-columns: 340px 1fr; gap: 24px; align-items: start; }
.section-title { font-size: 16px; font-weight: 700; color: var(--ink); margin-bottom: 14px; }
.section-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
.doc-count { font-size: 12px; color: var(--slate); }
.kb-sidebar { display: flex; flex-direction: column; gap: 20px; }

.kb-msg { margin-top: 10px; font-size: 12px; color: var(--slate); }
.msg-ok { color: var(--verdant); }

.upload-divider { display: flex; align-items: center; gap: 10px; margin: 18px 0 12px; color: var(--muted); font-size: 11px; }
.upload-divider::before, .upload-divider::after { content: ''; flex: 1; height: 1px; background: var(--border); }
.form-file { width: 100%; font-size: 12px; color: var(--slate); }

.search-results { margin-top: 16px; display: flex; flex-direction: column; gap: 10px; }
.search-item { padding: 10px 12px; background: var(--steel); border-radius: var(--radius-sm); }
.search-score { font-size: 11px; color: var(--cobalt); margin-bottom: 4px; }
.search-content { font-size: 12px; color: var(--ink); line-height: 1.5; white-space: pre-wrap; }

.empty-state { text-align: center; padding: 40px 16px; color: var(--slate); }
.empty-icon { font-size: 32px; margin-bottom: 10px; color: var(--muted); }
.empty-hint { text-align: center; padding: 20px; color: var(--slate); }

.doc-list { display: flex; flex-direction: column; gap: 10px; }
.doc-row { display: flex; align-items: flex-start; gap: 12px; padding: 12px; background: var(--steel); border-radius: var(--radius-sm); }
.doc-body { flex: 1; min-width: 0; }
.doc-id { font-size: 10px; font-family: var(--font-mono); color: var(--muted); }
.doc-content { font-size: 13px; color: var(--ink); margin-top: 4px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.btn-sm { padding: 5px 10px; font-size: 11px; }

@media (max-width: 760px) {
  .kb-layout { grid-template-columns: 1fr; }
}
</style>
