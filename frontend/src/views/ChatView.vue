<!-- ChatView.vue — AI 对话页。集成 WebSocket 流式聊天。 -->
<script setup>
import ChatPanel from '../components/ChatPanel.vue'
</script>

<template>
  <div class="chat-page">
    <div class="page-header">
      <h1 class="page-title">AI 对话</h1>
      <p class="page-subtitle">与智能助手对话，Agent 模式可自动调用工具完成任务</p>
    </div>
    <ChatPanel />
  </div>
</template>

<style scoped>
.chat-page { max-width: 900px; flex: 1; display: flex; flex-direction: column; min-height: 0; }
.page-header { flex-shrink: 0; }
</style>
