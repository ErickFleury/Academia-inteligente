import { afterEach, expect, test, vi } from 'vitest'

import { sendTrainingChatMessage } from './training-chat'

afterEach(() => vi.unstubAllGlobals())

test('memory capacity directs the client to review memory instead of retrying a conflict', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 409, json: async () => ({ detail: 'memory_capacity' }) }))
  await expect(sendTrainingChatMessage('token', 'Prefiro treinar cedo.', 'request')).rejects.toThrow('Sua memória está cheia. Abra Memória do assistente')
})
