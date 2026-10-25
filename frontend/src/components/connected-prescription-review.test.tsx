import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { useLayoutEffect } from 'react'
import { afterEach, expect, test, vi } from 'vitest'

import { developmentAccepted, developmentSaved as developmentSavedDraft } from '../prescription-development-fixtures'
import { ConnectedPrescriptionReview } from './connected-prescription-review'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

test('loads owned review and submits the exact revision through authenticated APIs', async () => {
  if (developmentAccepted.status !== 'accepted') throw new Error('Expected accepted fixture')
  const versionId = developmentAccepted.version_id
  const onSubmitted = vi.fn()
  const fetchMock = vi.fn().mockImplementation(async (url: string) => ({
    ok: true, status: 200,
    json: async () => url.endsWith('/submit') ? { id: versionId, revision: 2 }
      : { outcome: developmentAccepted },
  }))
  vi.stubGlobal('fetch', fetchMock)
  render(<ConnectedPrescriptionReview accessToken="test-token" role="client"
    versionId={versionId} revision={1} onSubmitted={onSubmitted} />)
  fireEvent.click(await screen.findByRole('button', { name: 'Enviar proposta para revisão do instrutor' }))
  await waitFor(() => expect(onSubmitted).toHaveBeenCalledWith({ id: versionId, revision: 2 }))
  const call = fetchMock.mock.calls.find(([url]) => url.endsWith('/submit'))
  expect(call?.[1].headers.Authorization).toBe('Bearer test-token')
  expect(JSON.parse(call?.[1].body)).toEqual({ expected_revision: 1 })
})

test('instructor manual assumption sends a reason and revision without changing the origin locally', async () => {
  const onChanged = vi.fn().mockResolvedValue(undefined)
  const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200,
    json: async () => ({ saved_draft: developmentSavedDraft }) })
  vi.stubGlobal('fetch', fetchMock)
  render(<ConnectedPrescriptionReview accessToken="test-token" role="instructor"
    versionId={developmentSavedDraft.id} revision={developmentSavedDraft.revision} onChanged={onChanged} />)
  fireEvent.change(await screen.findByRole('textbox', { name: 'Motivo da responsabilidade manual' }), {
    target: { value: 'Revisão profissional registrada para este teste.' },
  })
  fireEvent.click(screen.getByRole('button', { name: 'Assumir responsabilidade manual' }))
  await waitFor(() => expect(onChanged).toHaveBeenCalledTimes(1))
  const call = fetchMock.mock.calls.find(([url]) => url.endsWith('/assume-manual'))
  expect(call?.[1].headers.Authorization).toBe('Bearer test-token')
  expect(JSON.parse(call?.[1].body)).toEqual({ expected_revision: developmentSavedDraft.revision,
    reason: 'Revisão profissional registrada para este teste.' })
})

test('expired authorization shows a controlled error and no qualified proposal', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 401 }))
  render(<ConnectedPrescriptionReview accessToken="expired" role="client" versionId="owned" revision={1} />)
  expect(await screen.findByRole('alert')).toHaveTextContent('Sua sessão expirou.')
  expect(screen.queryByText(/Critérios verificados/)).not.toBeInTheDocument()
})

test('session changes hide the previous review before paint and clear private manual input', async () => {
  let releaseNext: (value: unknown) => void = () => undefined
  const nextReview = new Promise((resolve) => { releaseNext = resolve })
  vi.stubGlobal('fetch', vi.fn()
    .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ saved_draft: developmentSavedDraft }) })
    .mockImplementationOnce(() => nextReview))
  const beforePaint: string[] = []
  function SessionReview({ token }: { token: string }) {
    useLayoutEffect(() => { beforePaint.push(document.body.textContent ?? '') }, [token])
    return <ConnectedPrescriptionReview accessToken={token} role="instructor"
      versionId={developmentSavedDraft.id} revision={developmentSavedDraft.revision} />
  }
  const view = render(<SessionReview token="first-session" />)
  const reason = await screen.findByRole('textbox', { name: 'Motivo da responsabilidade manual' })
  fireEvent.change(reason, { target: { value: 'Private note from the previous session' } })
  view.rerender(<SessionReview token="second-session" />)
  expect(beforePaint.at(-1)).not.toContain('Rascunho salvo anterior')
  expect(screen.queryByRole('textbox', { name: 'Motivo da responsabilidade manual' })).not.toBeInTheDocument()
  releaseNext({ ok: true, status: 200, json: async () => ({ saved_draft: developmentSavedDraft }) })
  expect(await screen.findByRole('textbox', { name: 'Motivo da responsabilidade manual' })).toHaveValue('')
})
