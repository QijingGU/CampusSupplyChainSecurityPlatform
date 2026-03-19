import request from './request'

export interface ReactStep {
  step: number
  text: string
}

export interface ChatAction {
  type: string
  label: string
  payload?: Record<string, unknown>
}

export interface ChatResponse {
  reply: string
  react: ReactStep[]
  actions: ChatAction[]
}

export interface ExecuteResponse {
  success: boolean
  orderNo?: string
  trace?: { action: string; executedAt: string; items?: unknown[] }
  memorySaved?: boolean
}

export function chat(message: string, sessionId?: string | null) {
  return request.post<{ code: number; data: ChatResponse & { session_id?: string } }>(
    '/ai/chat',
    { message, session_id: sessionId || undefined },
    { timeout: 60000 }
  )
}

export function executeAction(type: string, payload?: Record<string, unknown>) {
  return request.post<{ code: number; data: ExecuteResponse }>('/ai/execute', { type, payload })
}
