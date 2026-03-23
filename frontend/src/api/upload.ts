import request from './request'

export interface UploadResult {
  ok: boolean
  filename: string
  saved_as: string
  size: number
  url: string
}

export function publicUpload(file: File) {
  const form = new FormData()
  form.append('file', file)
  return request.post<UploadResult>('/upload', form)
}
