import { afterEach, expect, test, vi } from 'vitest'

import { sendTrainingChatMessage } from './training-chat'

afterEach(() => vi.unstubAllGlobals())

test('memory capacity directs the client to review memory instead of retrying a conflict', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 409, json: async () => ({ detail: 'memory_capacity' }) }))
  await expect(sendTrainingChatMessage('token', 'Prefiro treinar cedo.', 'request')).rejects.toThrow('Sua memória está cheia. Abra Memória do assistente')
})

test('a transport timeout explains unconfirmed status in Portuguese', async () => {
  const fetchMock = vi.fn().mockRejectedValue(new DOMException('Request timed out', 'TimeoutError'))
  vi.stubGlobal('fetch', fetchMock)
  await expect(sendTrainingChatMessage('token', 'Olá', 'request')).rejects.toThrow('Não foi possível confirmar o andamento')
  expect(fetchMock.mock.calls[0][1].keepalive).toBe(true)
})
