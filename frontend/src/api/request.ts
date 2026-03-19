import axios from 'axios'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'
import router from '@/router'

const directBaseURL = import.meta.env.VITE_API_BASE
const devBaseCandidates = [
  'http://127.0.0.1:8166/api',
  'http://127.0.0.1:8167/api',
]

// 内网穿透：非本机访问时强制用 /api，避免请求发到访问者的 127.0.0.1
function isLocalAccess(): boolean {
  if (typeof window === 'undefined') return true
  const host = window.location.hostname
  return host === 'localhost' || host === '127.0.0.1'
}

let resolvedBaseURL: string | null = directBaseURL || (import.meta.env.DEV ? null : '/api')
let resolvingBaseURL: Promise<string> | null = null

async function pickDevBaseURL() {
  for (const candidate of devBaseCandidates) {
    try {
      const res = await axios.get(`${candidate}/health`, { timeout: 2000 })
      if (res.status === 200) {
        return candidate
      }
    } catch {
      // ignore and try next candidate
    }
  }

  return devBaseCandidates[0]
}

async function resolveBaseURL() {
  // 远程访问（内网穿透）：强制用 /api，否则会请求到访问者的 127.0.0.1
  if (!isLocalAccess()) return '/api'
  if (resolvedBaseURL) return resolvedBaseURL
  if (!import.meta.env.DEV) return '/api'

  if (!resolvingBaseURL) {
    resolvingBaseURL = pickDevBaseURL().then((baseURL) => {
      resolvedBaseURL = baseURL
      return baseURL
    })
  }

  return resolvingBaseURL
}

const request = axios.create({
  baseURL: resolvedBaseURL || '/api',
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
})

request.interceptors.request.use(
  async (config) => {
    config.baseURL = await resolveBaseURL()
    const userStore = useUserStore()
    if (userStore.token) {
      config.headers.Authorization = `Bearer ${userStore.token}`
    }
    return config
  },
  (err) => Promise.reject(err)
)

request.interceptors.response.use(
  (res) => {
    const { code, message } = res.data as { code?: number; message?: string }
    if (code !== undefined && code !== 200) {
      ElMessage.error(message || '请求失败')
      return Promise.reject(new Error(message as string))
    }
    return res.data
  },
  (err) => {
    if (err.response?.status === 401) {
      useUserStore().logout()
      router.push('/login')
    }
    const msg = err.code === 'ERR_NETWORK'
      ? '无法连接服务器，请确认后端已启动（uvicorn 8166）'
      : (err.response?.data?.detail || err.response?.data?.message || err.message || '网络错误')
    ElMessage.error(typeof msg === 'string' ? msg : JSON.stringify(msg))
    return Promise.reject(err)
  }
)

export default request
