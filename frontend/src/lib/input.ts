import type { UploadedTextFile } from '../types/api'

export const MAX_LOG_BYTES = 2 * 1024 * 1024
export const MAX_LOG_CHARACTERS = MAX_LOG_BYTES
export const MAX_UPLOAD_FILES = 5
export const MAX_FILE_BYTES = 256 * 1024
export const MAX_TOTAL_FILE_BYTES = 1024 * 1024

const ALLOWED_SUFFIXES = [
  '.cfg',
  '.conf',
  '.css',
  '.csv',
  '.dockerignore',
  '.env.example',
  '.gitignore',
  '.html',
  '.ini',
  '.js',
  '.json',
  '.jsx',
  '.log',
  '.md',
  '.properties',
  '.py',
  '.toml',
  '.ts',
  '.tsx',
  '.txt',
  '.xml',
  '.yaml',
  '.yml',
] as const
const EXACT_FILENAMES = new Set(['Dockerfile', 'Makefile'])
const WINDOWS_RESERVED = /^(aux|clock\$|con|nul|prn|com[1-9]|lpt[1-9])$/i
const encoder = new TextEncoder()

export const FILE_ACCEPT = ALLOWED_SUFFIXES.join(',')

export function utf8Bytes(value: string): number {
  return encoder.encode(value).byteLength
}

export function sanitizeFilename(value: string): string {
  const normalized = value.normalize('NFKC').trim()
  if (!normalized || normalized === '.' || normalized === '..') {
    throw new Error('Choose a file with a valid name.')
  }
  if (normalized.includes('/') || normalized.includes('\\') || normalized.includes(':')) {
    throw new Error(`${value}: paths and drive names are not accepted.`)
  }

  const sanitized = normalized.replace(/[^A-Za-z0-9._@()+-]/g, '_').trim()
  if (!sanitized || sanitized.length > 120 || sanitized.endsWith('.')) {
    throw new Error(`${value}: the file name cannot be safely normalized.`)
  }
  const [stem = ''] = sanitized.split('.')
  if (WINDOWS_RESERVED.test(stem)) {
    throw new Error(`${value}: the file name is reserved by the operating system.`)
  }

  const lower = sanitized.toLowerCase()
  if (
    !EXACT_FILENAMES.has(sanitized) &&
    !ALLOWED_SUFFIXES.some((suffix) => lower.endsWith(suffix))
  ) {
    throw new Error(
      `${value}: only allowlisted source, config, log, and documentation text files are accepted.`,
    )
  }
  return sanitized
}

export function validateText(value: string, label: string, byteLimit: number): void {
  if (utf8Bytes(value) > byteLimit) {
    throw new Error(`${label} exceeds ${formatBytes(byteLimit)}.`)
  }
  if (
    Array.from(value).some((character) => {
      const code = character.charCodeAt(0)
      return code < 32 && character !== '\n' && character !== '\r' && character !== '\t'
    })
  ) {
    throw new Error(`${label} contains binary or unsupported control characters.`)
  }
}

export async function readTextFiles(
  selected: FileList | File[],
  existing: UploadedTextFile[],
): Promise<UploadedTextFile[]> {
  const incoming = Array.from(selected)
  if (existing.length + incoming.length > MAX_UPLOAD_FILES) {
    throw new Error(`Upload at most ${MAX_UPLOAD_FILES} text files.`)
  }

  const decoder = new TextDecoder('utf-8', { fatal: true })
  const next = [...existing]
  for (const file of incoming) {
    const name = sanitizeFilename(file.name)
    if (file.size > MAX_FILE_BYTES) {
      throw new Error(`${name} exceeds the 256 KiB single-file limit.`)
    }
    if (next.some((item) => item.name.toLowerCase() === name.toLowerCase())) {
      throw new Error(`${name} has already been added.`)
    }

    let content: string
    try {
      content = decoder.decode(await file.arrayBuffer())
    } catch {
      throw new Error(`${name} is not valid UTF-8 text.`)
    }
    validateText(content, name, MAX_FILE_BYTES)
    next.push({ name, content })
  }

  const totalBytes = next.reduce((total, file) => total + utf8Bytes(file.content), 0)
  if (totalBytes > MAX_TOTAL_FILE_BYTES) {
    throw new Error('Uploaded files exceed the 1 MiB combined limit.')
  }
  return next
}

export function validateSubmission(logText: string, files: UploadedTextFile[]): void {
  if (!logText.trim()) {
    throw new Error('Paste a CI log or load one of the three samples before analyzing.')
  }
  validateText(logText, 'CI log', MAX_LOG_BYTES)
  if (files.length > MAX_UPLOAD_FILES) {
    throw new Error(`Upload at most ${MAX_UPLOAD_FILES} text files.`)
  }
  const totalBytes = files.reduce((total, file) => {
    sanitizeFilename(file.name)
    validateText(file.content, file.name, MAX_FILE_BYTES)
    return total + utf8Bytes(file.content)
  }, 0)
  if (totalBytes > MAX_TOTAL_FILE_BYTES) {
    throw new Error('Uploaded files exceed the 1 MiB combined limit.')
  }
}

export function formatBytes(bytes: number): string {
  if (bytes >= 1024 * 1024) {
    return `${(bytes / (1024 * 1024)).toFixed(bytes % (1024 * 1024) === 0 ? 0 : 1)} MiB`
  }
  if (bytes >= 1024) {
    return `${Math.ceil(bytes / 1024)} KiB`
  }
  return `${bytes} B`
}
