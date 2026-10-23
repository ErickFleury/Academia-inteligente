import { afterEach, describe, expect, it, vi } from 'vitest'
import { uploadReference } from './ai-references'

afterEach(() => { vi.unstubAllGlobals() })

describe('reference upload size', () => {
  it('sends a file of exactly 35 MB unchanged', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ id: 'version' }) })
    vi.stubGlobal('fetch', fetchMock)
    const file = new File([new Uint8Array(35 * 1024 * 1024)], 'manual.pdf', { type: 'application/pdf' })
    await uploadReference('test-token', 'Manual', file)
    expect(fetchMock).toHaveBeenCalledOnce()
    expect(fetchMock.mock.calls[0][1].body).toBe(file)
  })

  it('rejects a file one byte over 35 MB before sending', () => {
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)
    const file = new File([new Uint8Array(35 * 1024 * 1024 + 1)], 'manual.pdf', { type: 'application/pdf' })
    expect(() => uploadReference('test-token', 'Manual', file)).toThrow('até 35 MB')
    expect(fetchMock).not.toHaveBeenCalled()
  })
})
