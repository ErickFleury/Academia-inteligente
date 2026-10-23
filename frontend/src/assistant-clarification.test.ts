import { afterEach, expect, test, vi } from 'vitest'
import { createInitialTrainingProposal } from './training-plan'
import { createAdaptation } from './training-adaptation'
import { clarificationMessage } from './assistant-clarification'

afterEach(() => vi.unstubAllGlobals())

test.each(['initial', 'adaptation'])('shows the specific %s clarification from the API', async (kind) => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 422, json: async () => ({
    detail: 'assistant_clarification_required',
    clarification: { reason: 'missing_client_information', stage: 'specialist', explanation: 'Preciso confirmar a faixa etária.', next_step: 'Qual é sua idade?' },
  }) }))
  const request = kind === 'initial' ? createInitialTrainingProposal('token') : createAdaptation('token', 'razão', 'source', 'request')
  await expect(request).rejects.toThrow('Preciso confirmar a faixa etária. Qual é sua idade?')
})

test.each([null, {}, { explanation: 42, next_step: 'Pergunta?' }, { explanation: ' ', next_step: 'Pergunta?' }])('keeps a controlled fallback for malformed clarification metadata', (value) => {
  expect(clarificationMessage(value, 'Consulte o instrutor.')).toBe('Consulte o instrutor.')
})
