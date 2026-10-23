import { afterEach, describe, expect, it, vi } from 'vitest'
import { deleteReference, uploadReference } from './ai-references'

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

it('deletes the whole source with its revision and accepts an empty 204 response', async () => {
  const json = vi.fn().mockRejectedValue(new Error('empty response'))
  const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 204, json })
  vi.stubGlobal('fetch', fetchMock)
  await deleteReference('test-token', { source_id: 'source-id', revision: 3 })
  expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining('/ai/references/sources/source-id'), expect.objectContaining({
    method: 'DELETE', body: JSON.stringify({ revision: 3 }),
    headers: expect.objectContaining({ Authorization: 'Bearer test-token' }),
  }))
  expect(json).not.toHaveBeenCalled()
})
