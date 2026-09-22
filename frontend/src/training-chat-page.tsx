import { Box, Button, Card, CardContent, Stack, TextField } from '@mui/material'
import { useEffect, useState } from 'react'

import { ClientShell } from './components/application-shell'
import { ChatMessage, EmptyState, LoadingState, PageHeader, StatusNotice } from './components/ui'
import { getOwnTrainingChat, sendTrainingChatMessage, type TrainingChat } from './training-chat'

type TrainingChatPageProps = { accessToken: string; onSignOut: () => void }

function requestId(): string { return crypto.randomUUID() }

export function TrainingChatPage({ accessToken, onSignOut }: TrainingChatPageProps) {
  const [chat, setChat] = useState<TrainingChat | null>(null)
  const [message, setMessage] = useState('')
  const [pending, setPending] = useState<{ message: string; id: string } | null>(null)
  const [retry, setRetry] = useState<{ message: string; id: string } | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    void getOwnTrainingChat(accessToken)
      .then((state) => { if (active) setChat(state) })
      .catch((reason: unknown) => active && setError(reason instanceof Error ? reason.message : 'Não foi possível carregar sua conversa.'))
    return () => { active = false }
  }, [accessToken])

  async function submit(nextMessage: string, id = requestId()) {
    if (!nextMessage.trim() || pending) return
    setPending({ message: nextMessage, id })
    setError(null)
    try {
      setChat(await sendTrainingChatMessage(accessToken, nextMessage, id))
      setMessage('')
      setRetry(null)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Não foi possível enviar sua mensagem.')
      setRetry({ message: nextMessage, id })
    } finally { setPending(null) }
  }

  if (!chat) return <ClientShell onSignOut={onSignOut}><LoadingState label="Carregando assistente de treino" /></ClientShell>

  return (
    <ClientShell onSignOut={onSignOut}>
      <Stack spacing={3} sx={{ maxWidth: 880, minWidth: 0 }}>
        <PageHeader
          action={<Button component="a" href="/treino" variant="outlined">Ver meu treino</Button>}
          description="Tire dúvidas sobre o seu plano atual e seus exercícios. Mudanças no treino precisam de revisão profissional."
          eyebrow="Assistente de treino"
          title="Como posso ajudar hoje?"
        />
        {error && <Stack spacing={1} sx={{ alignItems: 'flex-start' }}><StatusNotice severity="error">{error}</StatusNotice>{retry && <Button onClick={() => void submit(retry.message, retry.id)} variant="outlined">Tentar novamente</Button>}</Stack>}
        <Stack aria-live="polite" spacing={1.5} sx={{ minHeight: 280 }}>
          {chat.messages.length === 0
            ? <EmptyState description="Pergunte sobre os exercícios, séries, repetições ou orientações do seu treino atual." title="Seu espaço para tirar dúvidas" />
            : chat.messages.map((item, index) => <ChatMessage key={`${item.created_at}-${index}`} role={item.role}>{item.content}</ChatMessage>)}
        </Stack>
        <Card component="form" onSubmit={(event) => { event.preventDefault(); void submit(message) }} sx={{ position: 'sticky', bottom: 16 }}>
          <CardContent>
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5}>
              <TextField autoComplete="off" fullWidth label="Escreva sua pergunta" multiline onChange={(event) => setMessage(event.target.value)} placeholder="Ex.: Como devo fazer este exercício?" value={message} />
              <Button disabled={!message.trim() || pending !== null} type="submit" variant="contained">{pending ? 'Enviando…' : 'Enviar'}</Button>
            </Stack>
          </CardContent>
        </Card>
        <Box><StatusNotice severity="info">O assistente explica seu treino, mas não altera o seu plano.</StatusNotice></Box>
      </Stack>
    </ClientShell>
  )
}
