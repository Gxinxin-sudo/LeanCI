import { describe, expect, it } from 'vitest'

import {
  MAX_FILE_BYTES,
  MAX_UPLOAD_FILES,
  readTextFiles,
  sanitizeFilename,
  validateSubmission,
} from './input'

describe('client input validation', () => {
  it('normalizes a safe text filename', () => {
    expect(sanitizeFilename(' retry config.py ')).toBe('retry_config.py')
  })

  it.each([
    '../secret.txt',
    '..\\secret.txt',
    'archive.zip',
    'bundle.tar.gz',
    'run.exe',
    'script.ps1',
    'script.sh',
  ])('rejects unsafe filename %s', (name) => {
    expect(() => sanitizeFilename(name)).toThrow()
  })

  it('rejects more than five files', async () => {
    const files = Array.from(
      { length: MAX_UPLOAD_FILES + 1 },
      (_, index) => new File(['text'], `file-${index}.txt`),
    )

    await expect(readTextFiles(files, [])).rejects.toThrow('Upload at most 5 text files.')
  })

  it('rejects a non-UTF-8 file', async () => {
    const file = new File([new Uint8Array([0xff, 0xfe, 0xfd])], 'failure.log')

    await expect(readTextFiles([file], [])).rejects.toThrow('not valid UTF-8 text')
  })

  it('rejects a file over the single-file byte limit', async () => {
    const file = new File(['x'.repeat(MAX_FILE_BYTES + 1)], 'failure.log')

    await expect(readTextFiles([file], [])).rejects.toThrow('256 KiB')
  })

  it('blocks binary control characters before submission', () => {
    expect(() =>
      validateSubmission('failed', [{ name: 'failure.log', content: 'bad\u0000text' }]),
    ).toThrow('binary or unsupported control characters')
  })
})
