export const IDS_ALERT_FOCUS_EVENT = 'ids-focus-event-request'
export const IDS_ALERT_SOUND_SETTINGS_UPDATED_EVENT = 'ids-alert-sound-settings-updated'

const IDS_ALERT_SOUND_SETTINGS_KEY = 'ids-admin-alert-sound-v1'
const IDS_ALERT_SOUND_DB_NAME = 'campus-supply-chain-security-platform'
const IDS_ALERT_SOUND_DB_VERSION = 1
const IDS_ALERT_SOUND_STORE = 'ids_alert_assets'
const IDS_ALERT_SOUND_RECORD_ID = 'admin-warning-audio'

type IDBTransactionModeSafe = 'readonly' | 'readwrite'

type IDSAlertSoundAssetRecord = {
  id: string
  blob: Blob
  name: string
  type: string
  updatedAt: string
}

export type IDSFocusEventDetail = {
  eventId: number
  report?: boolean
}

export type IDSAlertSoundSettings = {
  enabled: boolean
  volume: number
  custom_audio_name: string
  custom_audio_updated_at: string | null
}

export type IDSAlertSoundAssetInfo = {
  name: string
  type: string
  size: number
  updatedAt: string
}

let sharedAudioContext: AudioContext | null = null

function clampVolume(value: unknown) {
  const normalized = Number(value)
  if (!Number.isFinite(normalized)) return 0.85
  return Math.min(1, Math.max(0, normalized))
}

function defaultIdsAlertSoundSettings(): IDSAlertSoundSettings {
  return {
    enabled: true,
    volume: 0.85,
    custom_audio_name: '',
    custom_audio_updated_at: null,
  }
}

function dispatchIdsAlertSettingsUpdated() {
  if (typeof window === 'undefined') return
  window.dispatchEvent(new CustomEvent(IDS_ALERT_SOUND_SETTINGS_UPDATED_EVENT))
}

function getAudioContextCtor(): (typeof AudioContext) | null {
  if (typeof window === 'undefined') return null
  const maybeWindow = window as typeof window & { webkitAudioContext?: typeof AudioContext }
  return maybeWindow.AudioContext || maybeWindow.webkitAudioContext || null
}

async function ensureAudioContext() {
  const AudioCtor = getAudioContextCtor()
  if (!AudioCtor) return null
  if (!sharedAudioContext) {
    sharedAudioContext = new AudioCtor()
  }
  if (sharedAudioContext.state === 'suspended') {
    try {
      await sharedAudioContext.resume()
    } catch {
      return sharedAudioContext
    }
  }
  return sharedAudioContext
}

function openIdsAlertSoundDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    if (typeof indexedDB === 'undefined') {
      reject(new Error('当前浏览器不支持本地音频存储'))
      return
    }
    const request = indexedDB.open(IDS_ALERT_SOUND_DB_NAME, IDS_ALERT_SOUND_DB_VERSION)
    request.onupgradeneeded = () => {
      const db = request.result
      if (!db.objectStoreNames.contains(IDS_ALERT_SOUND_STORE)) {
        db.createObjectStore(IDS_ALERT_SOUND_STORE, { keyPath: 'id' })
      }
    }
    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(request.error || new Error('无法打开音频存储'))
  })
}

function withSoundStore<T>(
  mode: IDBTransactionModeSafe,
  handler: (store: IDBObjectStore) => Promise<T> | T,
): Promise<T> {
  return new Promise((resolve, reject) => {
    openIdsAlertSoundDB()
      .then((db) => {
        const transaction = db.transaction(IDS_ALERT_SOUND_STORE, mode)
        const store = transaction.objectStore(IDS_ALERT_SOUND_STORE)
        let result: T
        let settled = false

        const finalizeReject = (error: unknown) => {
          if (settled) return
          settled = true
          db.close()
          reject(error)
        }

        transaction.oncomplete = () => {
          if (settled) return
          settled = true
          db.close()
          resolve(result)
        }
        transaction.onerror = () => {
          finalizeReject(transaction.error || new Error('音频存储事务失败'))
        }
        transaction.onabort = () => {
          finalizeReject(transaction.error || new Error('音频存储事务已中止'))
        }

        Promise.resolve(handler(store))
          .then((value) => {
            result = value
          })
          .catch((error) => {
            try {
              transaction.abort()
            } catch {
              finalizeReject(error)
            }
          })
      })
      .catch(reject)
  })
}

function requestToPromise<T = unknown>(request: IDBRequest<T>): Promise<T> {
  return new Promise((resolve, reject) => {
    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(request.error || new Error('数据库请求失败'))
  })
}

async function getStoredSoundRecord(): Promise<IDSAlertSoundAssetRecord | null> {
  return withSoundStore('readonly', async (store) => {
    const result = await requestToPromise<IDSAlertSoundAssetRecord | undefined>(
      store.get(IDS_ALERT_SOUND_RECORD_ID),
    )
    return result || null
  })
}

async function playDefaultIdsAlertSound(volume: number) {
  const ctx = await ensureAudioContext()
  if (!ctx) return
  const startAt = ctx.currentTime + 0.01
  const master = ctx.createGain()
  master.gain.setValueAtTime(Math.max(0.04, volume * 0.28), startAt)
  master.connect(ctx.destination)

  const tones = [
    { frequency: 880, start: 0, duration: 0.12 },
    { frequency: 740, start: 0.15, duration: 0.14 },
    { frequency: 988, start: 0.34, duration: 0.18 },
  ]

  tones.forEach((tone) => {
    const osc = ctx.createOscillator()
    const gain = ctx.createGain()
    const toneStart = startAt + tone.start
    const toneEnd = toneStart + tone.duration
    osc.type = 'square'
    osc.frequency.setValueAtTime(tone.frequency, toneStart)
    gain.gain.setValueAtTime(0.0001, toneStart)
    gain.gain.exponentialRampToValueAtTime(0.7, toneStart + 0.02)
    gain.gain.exponentialRampToValueAtTime(0.0001, toneEnd)
    osc.connect(gain)
    gain.connect(master)
    osc.start(toneStart)
    osc.stop(toneEnd + 0.03)
  })

  await new Promise((resolve) => window.setTimeout(resolve, 700))
}

function writeRawIdsAlertSoundSettings(settings: IDSAlertSoundSettings) {
  if (typeof localStorage === 'undefined') return settings
  localStorage.setItem(IDS_ALERT_SOUND_SETTINGS_KEY, JSON.stringify(settings))
  dispatchIdsAlertSettingsUpdated()
  return settings
}

export function readIdsAlertSoundSettings(): IDSAlertSoundSettings {
  if (typeof localStorage === 'undefined') return defaultIdsAlertSoundSettings()
  try {
    const raw = localStorage.getItem(IDS_ALERT_SOUND_SETTINGS_KEY)
    if (!raw) return defaultIdsAlertSoundSettings()
    const parsed = JSON.parse(raw) as Partial<IDSAlertSoundSettings> | null
    return {
      enabled: parsed?.enabled !== false,
      volume: clampVolume(parsed?.volume),
      custom_audio_name: String(parsed?.custom_audio_name || '').trim(),
      custom_audio_updated_at: parsed?.custom_audio_updated_at || null,
    }
  } catch {
    return defaultIdsAlertSoundSettings()
  }
}

export function writeIdsAlertSoundSettings(
  next: Partial<IDSAlertSoundSettings> | IDSAlertSoundSettings,
) {
  const current = readIdsAlertSoundSettings()
  return writeRawIdsAlertSoundSettings({
    ...current,
    ...next,
    enabled: next.enabled ?? current.enabled,
    volume: clampVolume(next.volume ?? current.volume),
    custom_audio_name: String(next.custom_audio_name ?? current.custom_audio_name ?? '').trim(),
    custom_audio_updated_at:
      typeof next.custom_audio_updated_at === 'undefined'
        ? current.custom_audio_updated_at
        : next.custom_audio_updated_at,
  })
}

export async function primeIdsAlertSound() {
  await ensureAudioContext()
}

export async function getIdsAlertCustomSoundInfo(): Promise<IDSAlertSoundAssetInfo | null> {
  const record = await getStoredSoundRecord()
  if (!record) return null
  return {
    name: record.name,
    type: record.type,
    size: record.blob.size,
    updatedAt: record.updatedAt,
  }
}

export async function saveIdsAlertCustomSound(file: File) {
  const updatedAt = new Date().toISOString()
  const record: IDSAlertSoundAssetRecord = {
    id: IDS_ALERT_SOUND_RECORD_ID,
    blob: file,
    name: file.name,
    type: file.type,
    updatedAt,
  }
  await withSoundStore('readwrite', async (store) => {
    await requestToPromise(store.put(record))
  })
  writeIdsAlertSoundSettings({
    custom_audio_name: file.name,
    custom_audio_updated_at: updatedAt,
  })
  return {
    name: file.name,
    type: file.type,
    size: file.size,
    updatedAt,
  } satisfies IDSAlertSoundAssetInfo
}

export async function clearIdsAlertCustomSound() {
  await withSoundStore('readwrite', async (store) => {
    await requestToPromise(store.delete(IDS_ALERT_SOUND_RECORD_ID))
  })
  writeIdsAlertSoundSettings({
    custom_audio_name: '',
    custom_audio_updated_at: null,
  })
}

export function dispatchIDSFocusEvent(detail: IDSFocusEventDetail) {
  if (typeof window === 'undefined') return
  window.dispatchEvent(new CustomEvent<IDSFocusEventDetail>(IDS_ALERT_FOCUS_EVENT, { detail }))
}

export async function playIdsAlertSound(options?: { force?: boolean }) {
  const settings = readIdsAlertSoundSettings()
  if (!options?.force && !settings.enabled) return 'disabled'

  const customRecord = await getStoredSoundRecord()
  if (customRecord?.blob) {
    const objectUrl = URL.createObjectURL(customRecord.blob)
    const audio = new Audio(objectUrl)
    audio.volume = clampVolume(settings.volume)
    try {
      await audio.play()
      const cleanup = () => URL.revokeObjectURL(objectUrl)
      audio.addEventListener('ended', cleanup, { once: true })
      window.setTimeout(cleanup, 60_000)
      return 'custom'
    } catch {
      URL.revokeObjectURL(objectUrl)
    }
  }

  await playDefaultIdsAlertSound(settings.volume)
  return 'default'
}
