/**
 * api/chat.js — WebSocket 聊天客户端。
 * 提供流式对话：connect → send → 接收分块 → done 回调。
 * 内置断线重连和状态通知。
 */

export class ChatClient {
  constructor() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    this.url = `${protocol}//${window.location.host}/api/chat/ws`
    this.ws = null
    this._onChunk = null       // 收到流式分片回调
    this._onStatus = null      // 连接状态变更回调
    this._onError = null       // 错误回调
    this._pendingSend = null   // 连接建立前暂存的消息
    this._reconnectTimer = null
    this._reconnectCount = 0
    this._maxReconnect = 3
    this._intentionalClose = false
  }

  /** 建立 WebSocket 连接 */
  connect() {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this._notifyStatus('connected')
      return
    }
    if (this.ws && this.ws.readyState === WebSocket.CONNECTING) {
      this._notifyStatus('connecting')
      return
    }

    this._intentionalClose = false
    this._notifyStatus('connecting')

    try {
      this.ws = new WebSocket(this.url)
    } catch (e) {
      this._notifyStatus('error')
      this._onError?.('无法创建 WebSocket 连接，请确认后端已启动')
      return
    }

    this.ws.onopen = () => {
      this._reconnectCount = 0
      this._notifyStatus('connected')
      // 如果有暂存消息，连接建立后立即发送
      if (this._pendingSend) {
        this.ws.send(JSON.stringify(this._pendingSend))
        this._pendingSend = null
      }
    }

    this.ws.onmessage = (event) => {
      try {
        const chunk = JSON.parse(event.data)
        this._onChunk?.(chunk)
      } catch {
        // 非 JSON 消息静默丢弃
      }
    }

    this.ws.onerror = () => {
      this._notifyStatus('error')
      this._onError?.('WebSocket 连接出错，请检查后端是否运行')
    }

    this.ws.onclose = () => {
      if (this._intentionalClose) return
      this._notifyStatus('disconnected')
      // 自动重连
      if (this._reconnectCount < this._maxReconnect) {
        this._reconnectCount++
        this._reconnectTimer = setTimeout(() => {
          this.connect()
        }, 2000 * this._reconnectCount)   // 逐渐加长间隔
      } else {
        this._onError?.('WebSocket 连接已断开，请刷新页面重试')
      }
    }
  }

  /** 发送消息 */
  send(payload) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      // 连接未就绪，暂存消息，触发连接
      this._pendingSend = payload
      this.connect()
      return
    }
    this.ws.send(JSON.stringify(payload))
  }

  /** 注册分块回调 */
  onMessage(handler) {
    this._onChunk = handler
  }

  /** 注册状态回调：connecting | connected | disconnected | error */
  onStatus(handler) {
    this._onStatus = handler
  }

  /** 注册错误回调 */
  onError(handler) {
    this._onError = handler
  }

  /** 关闭连接 */
  disconnect() {
    this._intentionalClose = true
    clearTimeout(this._reconnectTimer)
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
  }

  /** 内部：通知状态变更 */
  _notifyStatus(status) {
    this._onStatus?.(status)
  }
}
