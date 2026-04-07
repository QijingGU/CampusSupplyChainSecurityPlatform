import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

const USER_INFO_STORAGE_KEY = 'user-info'

type StoredUserInfo = {
  id: number
  username: string
  real_name: string
  role: string
  department?: string
  phone?: string
}

function readStoredUserInfo(): StoredUserInfo | null {
  try {
    const raw = localStorage.getItem(USER_INFO_STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as Partial<StoredUserInfo> | null
    if (!parsed || typeof parsed !== 'object') return null
    const id = Number(parsed.id || 0)
    const username = String(parsed.username || '').trim()
    const realName = String(parsed.real_name || '').trim()
    const role = String(parsed.role || '').trim()
    if (!id || !username || !role) return null
    return {
      id,
      username,
      real_name: realName || username,
      role,
      department: parsed.department ? String(parsed.department) : '',
      phone: parsed.phone ? String(parsed.phone) : '',
    }
  } catch {
    return null
  }
}

function writeStoredUserInfo(info: StoredUserInfo | null) {
  if (!info) {
    localStorage.removeItem(USER_INFO_STORAGE_KEY)
    return
  }
  localStorage.setItem(USER_INFO_STORAGE_KEY, JSON.stringify(info))
}

export const useUserStore = defineStore('user', () => {
  const token = ref<string>(localStorage.getItem('token') || '')
  const userInfo = ref<{
    id: number
    username: string
    real_name: string
    role: string
    department?: string
  } | null>(readStoredUserInfo())

  const isLoggedIn = computed(() => !!token.value)
  const isAdmin = computed(() => userInfo.value?.role === 'system_admin')
  const role = computed(() => userInfo.value?.role || '')

  function setToken(t: string) {
    token.value = t
    if (t) {
      localStorage.setItem('token', t)
    } else {
      localStorage.removeItem('token')
      writeStoredUserInfo(null)
    }
  }

  function setUserInfo(info: typeof userInfo.value) {
    userInfo.value = info
    writeStoredUserInfo(info)
  }

  function logout() {
    token.value = ''
    userInfo.value = null
    localStorage.removeItem('token')
    localStorage.removeItem(USER_INFO_STORAGE_KEY)
  }

  return {
    token,
    userInfo,
    isLoggedIn,
    isAdmin,
    role,
    setToken,
    setUserInfo,
    logout,
  }
})
