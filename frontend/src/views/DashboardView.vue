<!-- DashboardView.vue — 总览。Agent 23 项工具清单 + 快捷入口。 -->
<script setup>
import { useRouter } from 'vue-router'

const router = useRouter()

/** 24 项 Agent 工具（22 本地注册 + 2 MCP 协议） */
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
    group: '联网搜索',
    items: [
      { name: 'web_search',            label: '联网搜索',   desc: '传入搜索关键词或自然语言问题，调用博查 API 搜索最新网络信息，返回标题、链接和摘要' },
    ],
  },
  {
    group: '外部服务',
    items: [
      { name: 'query_weather',         label: '天气查询',   desc: 'MCP 协议接入：传入城市名称（如"北京"），通过高德 API 地理编码后查询实时天气和未来几天预报' },
      { name: 'translate',             label: '多语言翻译', desc: '传入文本和目标语言，调用 LLM 翻译，支持中、英、日、韩等各种语言' },
    ],
  },
  {
    group: '多模态',
    items: [
      { name: 'analyze_image',         label: '图片分析',   desc: '传入图片 URL 或本地路径，视觉模型识别场景、物体、人物、氛围、颜色等信息' },
      { name: 'ocr_image',             label: 'OCR 文字提取', desc: '传入图片，提取图中的所有文字，支持截图、扫描件、照片。本地文件自动转 base64 上传' },
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
    group: '工作区文件',
    items: [
      { name: 'write_file',            label: '写入文件',   desc: '在工作区沙箱内写入/覆盖文件（支持自动创建目录），如 scripts/demo.py' },
      { name: 'read_file',             label: '读取文件',   desc: '读取工作区内文本文件内容，仅限自己的沙箱目录' },
      { name: 'list_workspace',        label: '列出目录',   desc: '列出工作区目录内容，含文件大小与修改时间' },
      { name: 'create_directory',      label: '创建目录',   desc: '在工作区内创建目录，支持多级路径' },
      { name: 'delete_file',           label: '删除文件',   desc: '删除工作区内文件或空目录，高危操作需人工确认' },
      { name: 'move_file',             label: '移动/重命名', desc: '移动或重命名工作区内文件，高危操作需人工确认' },
      { name: 'run_command',           label: '执行命令',   desc: '在授权工作区内执行白名单命令（python/pip/git/node/npm 等），需人工确认' },
      { name: 'read_project_file',     label: '读取项目文件', desc: '读取本机任意位置的代码/文档文件（用于分析你的项目），首次访问某目录需你确认授权' },
    ],
  },
  {
    group: '技能系统',
    items: [
      { name: 'install_skill',         label: '安装技能',   desc: '从官方技能仓库（anthropics/skills）下载安装技能到本地 skills/ 目录，如 pptx/docx/pdf/xlsx' },
      { name: 'list_skills',           label: '列出技能',   desc: '列出已安装的所有技能及其说明' },
      { name: 'load_skill',            label: '加载技能',   desc: '读取技能的 SKILL.md 使用说明并按步骤执行任务（如生成 PPT）' },
    ],
  },
  {
    group: '系统',
    items: [
      { name: 'get_current_time',      label: '获取时间',   desc: 'MCP 协议接入：无需参数，返回当前北京时间（年月日、星期、时分秒），用于回答时间相关问题时准确推算日期' },
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
        <span class="qc-desc">Agent 模式 · 24 项工具</span>
      </button>
      <button class="quick-card" @click="router.push('/knowledge')">
        <span class="qc-icon">▣</span>
        <span class="qc-label">知识库</span>
        <span class="qc-desc">文件上传 · 语义搜索</span>
      </button>
      <button class="quick-card" @click="router.push('/chat')">
        <span class="qc-icon">⌘</span>
        <span class="qc-label">Agent 工作区</span>
        <span class="qc-desc">沙箱文件操作 · 命令执行</span>
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
.dashboard { width: 100%; }

/* ========== 快捷入口 ========== */
.quick-row { display: flex; gap: 16px; margin-bottom: 28px; }
.quick-card {
  flex: 1; display: flex; flex-direction: column; align-items: center; gap: 6px;
  padding: 20px 16px; border-radius: var(--radius-md); background: var(--white);
  border: 1px solid var(--border); cursor: pointer;
  transition: border-color 0.15s, box-shadow 0.15s, transform 0.15s;
}
.quick-card:hover { border-color: var(--cobalt); box-shadow: 0 2px 12px rgba(61,91,245,0.14); transform: translateY(-2px); }
.qc-icon { font-size: 28px; color: var(--cobalt); }
.qc-label { font-size: 16px; font-weight: 700; color: var(--ink); }
.qc-desc { font-size: 12.5px; color: var(--slate); }

/* ========== 工具分组 ========== */
.tool-groups { display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; }
.tool-group { padding: 18px 22px; }
.group-title { font-size: 14.5px; font-weight: 700; color: var(--ink); margin-bottom: 14px; padding-bottom: 10px; border-bottom: 1px solid var(--border); font-family: var(--font-mono); letter-spacing: 0.06em; }
.tool-list { display: flex; flex-direction: column; gap: 12px; }
.tool-item { display: flex; align-items: baseline; gap: 10px; }
.tool-name {
  font-family: var(--font-mono);
  font-size: 13px; font-weight: 600; color: var(--cobalt);
  white-space: nowrap; min-width: 96px; flex-shrink: 0;
}
.tool-desc { font-size: 13px; color: var(--slate); line-height: 1.6; }

@media (max-width: 720px) {
  .tool-groups { grid-template-columns: 1fr; }
  .quick-row { flex-direction: column; }
}
</style>
