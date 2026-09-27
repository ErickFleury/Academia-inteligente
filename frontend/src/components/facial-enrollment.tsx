import { Box, Button, Chip, Stack, Typography } from '@mui/material'
import { useEffect, useRef, useState } from 'react'

import { ApiRequestError } from '../clients'
import { biometricMessage, biometricRequest, captureEnrollment, personBinding, type EnrollmentProof, type EnrollmentSession, type EnrollmentStatus } from '../biometrics'
import { StatusNotice } from './ui'
import { WebcamCapture } from './webcam-capture'

type Props = {
  token: string; email: string; cpf: string; role: 'client' | 'employee'; personId?: string;
  onReady?: (proof: EnrollmentProof | null) => void; onUnauthenticated: () => void;
}

export function FacialEnrollment({ token, email, cpf, role, personId, onReady, onUnauthenticated }: Props) {
  const [status, setStatus] = useState<EnrollmentStatus | null>(null)
  const [session, setSession] = useState<EnrollmentSession | null>(null)
  const [open, setOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const controller = useRef<AbortController | null>(null)
  const inFlight = useRef(false)
  const lifecycleCommand = useRef<{ key: string; id: string } | null>(null)
  const binding = personBinding(email, cpf)

  useEffect(() => () => { controller.current?.abort() }, [])
  useEffect(() => {
    controller.current?.abort(); setStatus(null); setSession(null); setNotice(null); setError(null); setOpen(false); onReady?.(null)
  }, [binding, personId, onReady])

  function failure(reason: unknown) {
    if (reason instanceof ApiRequestError && reason.status === 401) onUnauthenticated()
    setError(biometricMessage(reason))
  }
  async function operation(action: (signal: AbortSignal) => Promise<void>) {
    if (inFlight.current) return
    inFlight.current = true; setBusy(true); setError(null)
    const abort = new AbortController(); controller.current = abort
    try { await action(abort.signal) } catch (reason) { if (!abort.signal.aborted) failure(reason) }
    finally { inFlight.current = false; setBusy(false) }
  }
  async function readStatus(signal?: AbortSignal) {
    const result = personId
      ? await biometricRequest<EnrollmentStatus>(token, `/people/${personId}/enrollment`, undefined, signal)
      : await biometricRequest<EnrollmentStatus>(token, '/enrollment-readiness', { email, cpf }, signal)
    setStatus(result)
    if (!personId && result.status === 'enabled') {
      onReady?.({ binding, sessionId: null, expiresAt: null })
      setNotice('Cadastro facial existente encontrado. Ele será reutilizado para este vínculo.')
    }
    return result
  }
  async function begin(signal: AbortSignal) {
    const current = await readStatus(signal)
    if (!personId && current.status === 'enabled') return
    const stage = await biometricRequest<EnrollmentSession>(token, '/enrollment-sessions', {
      command_id: crypto.randomUUID(), email, cpf, role: personId ? 'replacement' : role,
      person_id: current.person_id, expected_revision: current.revision,
    }, signal)
    setSession(stage); setOpen(true)
  }
  async function accept(result: EnrollmentSession, signal?: AbortSignal) {
    setSession(result)
    if (result.status !== 'ready') throw new Error(result.result_code)
    if (personId) {
      const key = `replace:${result.session_id}`
      if (lifecycleCommand.current?.key !== key) lifecycleCommand.current = { key, id: crypto.randomUUID() }
      const next = await biometricRequest<EnrollmentStatus>(token, `/people/${personId}/enrollment/replacement`, {
        command_id: lifecycleCommand.current.id, session_id: result.session_id, expected_revision: status?.revision ?? 0,
      }, signal)
      setStatus(next); setNotice('Cadastro facial atualizado. A limpeza do material anterior é acompanhada pelo sistema.')
      setSession(null)
    } else {
      onReady?.({ binding, sessionId: result.session_id, expiresAt: result.expires_at })
      setNotice('Captura validada. Você já pode concluir o cadastro.')
    }
  }
  async function capture(image: Blob) {
    if (!session || inFlight.current) throw new Error('capture_in_progress')
    inFlight.current = true; setBusy(true); setError(null)
    const abort = new AbortController(); controller.current = abort
    try {
      const result = await captureEnrollment(token, session.session_id, image, crypto.randomUUID(), abort.signal)
      await accept(result, abort.signal)
    } catch (reason) {
      if (reason instanceof ApiRequestError && reason.status === 401) onUnauthenticated()
      throw reason
    } finally { inFlight.current = false; setBusy(false) }
  }
  async function recover(signal: AbortSignal) {
    if (!session) return
    const result = await biometricRequest<EnrollmentSession>(token, `/enrollment-sessions/${session.session_id}`, undefined, signal)
    setSession(result)
    if (result.status === 'ready') await accept(result, signal)
    else if (result.status === 'consumed' && personId) { await readStatus(signal); setNotice('Cadastro facial atualizado.'); setSession(null) }
    else if (result.status === 'capturing') setNotice('A captura ainda está em andamento. Aguarde antes de consultar novamente.')
    else if (result.status === 'rejected' || result.status === 'expired') setError(biometricMessage(new Error(result.result_code)))
  }
  async function revoke(signal: AbortSignal) {
    if (!personId || !status || !window.confirm('Revogar este cadastro facial? O acesso pelo rosto será bloqueado. O login continuará disponível.')) return
    const key = `revoke:${personId}:${status.revision}`
    if (lifecycleCommand.current?.key !== key) lifecycleCommand.current = { key, id: crypto.randomUUID() }
    const result = await biometricRequest<EnrollmentStatus>(token, `/people/${personId}/enrollment/revocation`, { command_id: lifecycleCommand.current.id, expected_revision: status.revision }, signal)
    setStatus(result); setSession(null); setNotice('Cadastro facial revogado. A limpeza será retomada automaticamente se o serviço estiver indisponível.')
  }
  return <Box component="section" aria-label="Cadastro facial" sx={{ border: 1, borderColor: 'divider', borderRadius: 2, p: 2 }}><Stack spacing={2}>
    <Box><Typography component="h3" variant="h6">Cadastro facial{personId ? '' : ' obrigatório'}</Typography><Typography color="text.secondary" variant="body2">{personId ? 'Consulte o estado, substitua ou revogue o rosto cadastrado.' : 'Verifique se a pessoa já possui um rosto cadastrado. Caso contrário, faça uma captura com a webcam.'}</Typography></Box>
    {status && <Chip sx={{ alignSelf: 'flex-start' }} color={status.status === 'enabled' ? 'success' : 'default'} label={status.status === 'enabled' ? 'Rosto cadastrado' : 'Captura necessária'} />}
    <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} sx={{ flexWrap: 'wrap' }} useFlexGap>
      <Button disabled={busy || !email.trim() || cpf.replace(/\D/g, '').length !== 11} variant="outlined" onClick={() => void operation(personId ? async (signal) => { await readStatus(signal) } : begin)}>{busy ? 'Verificando...' : 'Verificar cadastro facial'}</Button>
      {personId && status && <Button disabled={busy} variant="outlined" onClick={() => void operation(begin)}>{status.status === 'enabled' ? 'Substituir rosto' : 'Cadastrar rosto'}</Button>}
      {session && !['consumed', 'expired'].includes(session.status) && <Button disabled={busy} onClick={() => void operation(recover)}>Consultar resultado da captura</Button>}
      {session?.status === 'rejected' && <Button disabled={busy} onClick={() => setOpen(true)}>Tentar nova captura</Button>}
      {personId && status?.status === 'enabled' && <Button disabled={busy} color="error" onClick={() => void operation(revoke)}>Revogar rosto</Button>}
    </Stack>
    <Stack aria-live="polite" spacing={1}>{notice && <StatusNotice severity="success">{notice}</StatusNotice>}{error && <StatusNotice severity="error">{error}</StatusNotice>}{status?.cleanup_pending && <StatusNotice severity="info">Há material facial aguardando limpeza no serviço local.</StatusNotice>}</Stack>
    <WebcamCapture open={open} onClose={() => setOpen(false)} onCapture={capture} />
  </Stack></Box>
}
