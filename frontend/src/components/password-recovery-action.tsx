import { Button, Stack, Typography } from '@mui/material'
import { useEffect, useRef, useState } from 'react'

import { PasswordRecoveryError, requestPasswordRecovery } from '../password-recovery'
import { StatusNotice } from './ui'

export function PasswordRecoveryAction({ accessToken, clientId }: { accessToken: string; clientId?: string }) {
  const [pending, setPending] = useState(false)
  const [cooldown, setCooldown] = useState(false)
  const [notice, setNotice] = useState<{ error: boolean; text: string } | null>(null)
  const lock = useRef(false)

  useEffect(() => {
    if (!cooldown) return
    const timer = window.setTimeout(() => setCooldown(false), 60_000)
    return () => window.clearTimeout(timer)
  }, [cooldown])

  async function send() {
    if (lock.current || cooldown) return
    lock.current = true
    setPending(true); setNotice(null)
    try {
      await requestPasswordRecovery(accessToken, clientId)
      setNotice({ error: false, text: 'E-mail de redefinição enviado. Abra o link para criar uma nova senha em até 15 minutos.' })
      setCooldown(true)
    } catch (reason) {
      setNotice({ error: true, text: reason instanceof PasswordRecoveryError ? reason.message : 'Não foi possível confirmar o envio. Verifique o e-mail cadastrado e tente novamente em um minuto.' })
      if (!(reason instanceof PasswordRecoveryError) || [429, 503].includes(reason.status)) setCooldown(true)
    } finally { lock.current = false; setPending(false) }
  }

  return <Stack spacing={1.5}>
    <Typography component="h3" variant="h4">Senha de acesso</Typography>
    <Typography color="text.secondary" variant="body2">Envie um link ao e-mail cadastrado para definir uma nova senha. O link é válido por 15 minutos.</Typography>
    <Button disabled={pending || cooldown} onClick={() => void send()} sx={{ alignSelf: 'flex-start' }} variant="outlined">{pending ? 'Enviando link…' : 'Redefinir senha'}</Button>
    {cooldown && <Typography color="text.secondary" variant="body2">Aguarde um minuto para solicitar outro link.</Typography>}
    <Stack aria-live="polite">{notice && <StatusNotice severity={notice.error ? 'error' : 'success'}>{notice.text}</StatusNotice>}</Stack>
  </Stack>
}
