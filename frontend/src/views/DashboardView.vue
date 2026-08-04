<!-- DashboardView.vue — 总览。Agent 12 项工具清单 + 快捷入口。 -->
<script setup>
import { useRouter } from 'vue-router'

const router = useRouter()

/** 12 项 Agent 工具 */
const tools = [
  {
    group: '文档',
    items: [
      { name: 'parse_document',        label: '文档解析',   desc: '传入文件路径，解析 PDF、Word、TXT、Markdown、JSON、CSV 等格式，返回文本内容' },
      { name: 'list_directory',        label: '目录浏览',   desc: '传入目录路径，列出该目录下所有文件和文件夹名称' },
    ],
  },
  {
    group: '知识库',
    items: [
      { name: 'search_knowledge',      label: '知识库搜索', desc: '传入查询文本，在 Chroma 向量库中语义检索最相关的文档片段，返回匹配内容和相似度' },
      { name: 'add_knowledge',         label: '知识库添加', desc: '传入文本内容，自动向量化后存入 Chroma 知识库，返回文档 ID' },
    ],
  },
  {
    group: '外部服务',
    items: [
      { name: 'query_weather',         label: '天气查询',   desc: '传入城市名称（如"北京"），通过高德 API 地理编码后查询实时天气和未来几天预报' },
      { name: 'translate',             label: '多语言翻译', desc: '传入文本和目标语言，调用 LLM 翻译，支持中、英、日、韩等各种语言' },
    ],
  },
  {
    group: '多模态',
    items: [
      { name: 'analyze_image',         label: '图片分析',   desc: '传入图片 URL 或本地路径，视觉模型识别场景、物体、人物、氛围、颜色等信息' },
      { name: 'ocr_image',             label: 'OCR 文字提取', desc: '传入图片，提取图中的所有文字，支持截图、扫描件、照片。本地文件自动转 base64 上传' },
      { name: 'speech_to_text',        label: '语音转文字', desc: '传入音频 URL 或本地路径，Paraformer 模型异步识别并返回文字。本地文件自动 multipart 上传' },
    ],
  },
  {
    group: '任务管理',
    items: [
      { name: 'create_task',           label: '创建任务',   desc: '传入任务名称和类型（document_process / data_calc / file_convert），创建任务并提交 Celery 后台执行' },
      { name: 'list_tasks',            label: '查询任务',   desc: '可选传入状态（pending/running/completed/failed）筛选，不传则返回全部任务及状态' },
    ],
  },
  {
    group: '系统',
    items: [
      { name: 'get_current_time',      label: '获取时间',   desc: '无需参数，返回当前北京时间（年月日、星期、时分秒），用于回答时间相关问题时准确推算日期' },
    ],
  },
]
</script>

<template>
  <div class="dashboard">
    <div class="page-header">
      <h1 class="page-title">总览</h1>
      <p class="page-subtitle">在对话页切换到 Agent 模式，AI 会自主分析需求并调用以下工具完成任务</p>
    </div>

    <!-- 快捷入口 -->
    <div class="quick-row">
      <button class="quick-card" @click="router.push('/chat')">
        <span class="qc-icon">◈</span>
        <span class="qc-label">AI 对话</span>
        <span class="qc-desc">Agent 模式 · 12 项工具</span>
      </button>
      <button class="quick-card" @click="router.push('/knowledge')">
        <span class="qc-icon">▣</span>
        <span class="qc-label">知识库</span>
        <span class="qc-desc">语义搜索 · 向量存储</span>
      </button>
      <button class="quick-card" @click="router.push('/chat')">
        <span class="qc-icon">↗</span>
        <span class="qc-label">文件上传</span>
        <span class="qc-desc">对话页 + 按钮上传</span>
      </button>
    </div>

    <!-- 工具清单 -->
    <div class="tool-groups">
      <section v-for="group in tools" :key="group.group" class="card tool-group">
        <h2 class="group-title">{{ group.group }}</h2>
        <div class="tool-list">
          <div v-for="t in group.items" :key="t.name" class="tool-item">
            <span class="tool-name">{{ t.label }}</span>
            <span class="tool-desc">{{ t.desc }}</span>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.dashboard { max-width: 1000px; }

/* ========== 快捷入口 ========== */
.quick-row { display: flex; gap: 16px; margin-bottom: 28px; }
.quick-card {
  flex: 1; display: flex; flex-direction: column; align-items: center; gap: 6px;
  padding: 20px 16px; border-radius: var(--radius-md); background: var(--white);
  border: 1px solid var(--border); cursor: pointer; transition: border-color 0.15s, box-shadow 0.15s;
}
.quick-card:hover { border-color: var(--cobalt); box-shadow: 0 2px 12px rgba(79,110,247,0.12); }
.qc-icon { font-size: 28px; color: var(--cobalt); }
.qc-label { font-size: 15px; font-weight: 700; color: var(--ink); }
.qc-desc { font-size: 11px; color: var(--slate); }

/* ========== 工具分组 ========== */
.tool-groups { display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; }
.tool-group { padding: 18px 20px; }
.group-title { font-size: 14px; font-weight: 700; color: var(--ink); margin-bottom: 12px; padding-bottom: 10px; border-bottom: 1px solid var(--border); }
.tool-list { display: flex; flex-direction: column; gap: 10px; }
.tool-item { display: flex; align-items: baseline; gap: 10px; }
.tool-name {
  font-size: 13px; font-weight: 600; color: var(--cobalt);
  white-space: nowrap; min-width: 78px; flex-shrink: 0;
}
.tool-desc { font-size: 12px; color: var(--slate); line-height: 1.5; }

@media (max-width: 720px) {
  .tool-groups { grid-template-columns: 1fr; }
  .quick-row { flex-direction: column; }
}
</style>
