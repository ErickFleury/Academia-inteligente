import { Box, Button, Card, CardContent, Stack, TextField, Typography } from '@mui/material'
import { useEffect, useState } from 'react'

import { ClientShell } from './components/application-shell'
import { ChatMessage, EmptyState, LoadingState, PageHeader, StatusNotice } from './components/ui'
import { getOwnTrainingChat, sendTrainingChatMessage, type TrainingChat } from './training-chat'
import { createAdaptation, decideAdaptation, getOwnAdaptations, type TrainingAdaptation } from './training-adaptation'
import { getCurrentTrainingPlan } from './training-plan'

type TrainingChatPageProps = { accessToken: string; onSignOut: () => void }

function requestId(): string { return crypto.randomUUID() }

export function TrainingChatPage({ accessToken, onSignOut }: TrainingChatPageProps) {
  const [chat, setChat] = useState<TrainingChat | null>(null)
  const [message, setMessage] = useState('')
  const [pending, setPending] = useState<{ message: string; id: string } | null>(null)
  const [retry, setRetry] = useState<{ message: string; id: string } | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [adaptations, setAdaptations] = useState<TrainingAdaptation[]>([])
  const [hasCurrentPlan, setHasCurrentPlan] = useState<boolean | null>(null)
  const [creatingProposal, setCreatingProposal] = useState(false)

  useEffect(() => {
    let active = true
    void Promise.all([getOwnTrainingChat(accessToken), getOwnAdaptations(accessToken), getCurrentTrainingPlan(accessToken)])
      .then(([state, proposals, plan]) => { if (active) { setChat(state); setAdaptations(proposals); setHasCurrentPlan(plan !== null) } })
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

  async function requestProposal(sourceRequestId: string, reason: string) {
    if (creatingProposal) return
    setCreatingProposal(true); setError(null)
    try {
      const proposal = await createAdaptation(accessToken, reason, sourceRequestId, crypto.randomUUID())
      setAdaptations((items) => [proposal, ...items])
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Não foi possível gerar a proposta.') }
    finally { setCreatingProposal(false) }
  }

  async function reviewProposal(id: string, accept: boolean) {
    try { const proposal = await decideAdaptation(accessToken, id, accept); setAdaptations((items) => items.map((item) => item.id === id ? proposal : item)) }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Não foi possível revisar a proposta.') }
  }

  if (!chat || hasCurrentPlan === null) return <ClientShell onSignOut={onSignOut}><LoadingState label="Carregando assistente de treino" /></ClientShell>

  const suggestions = chat.messages.filter((item) => item.role === 'assistant' && item.adaptation_suggested && item.reply_to_client_request_id && item.adaptation_reason)

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
        {hasCurrentPlan && suggestions.filter((suggestion) => !adaptations.some((proposal) => proposal.source_client_request_id === suggestion.reply_to_client_request_id)).map((suggestion, index) => <Card component="section" key={`${suggestion.created_at}-${index}`}>
          <CardContent>
            <Stack spacing={1.5}>
              <Typography component="h2" variant="h3">Sugestão de alteração</Typography>
              <Typography color="text.secondary">O assistente identificou uma possível melhoria: {suggestion.adaptation_reason}</Typography>
              <Box><Button disabled={creatingProposal} onClick={() => void requestProposal(suggestion.reply_to_client_request_id!, suggestion.adaptation_reason!)} variant="outlined">{creatingProposal ? 'Preparando rascunho…' : 'Enviar rascunho para minha revisão'}</Button></Box>
            </Stack>
          </CardContent>
        </Card>)}
        {adaptations.map((proposal) => <Card component="section" key={proposal.id}><CardContent><Stack spacing={1}>
          <Typography component="h2" variant="h3">Proposta de alteração</Typography>
          <Typography>{proposal.explanation}</Typography>
          <Typography color="text.secondary" variant="body2">Status: {proposal.status === 'proposed' ? 'Aguardando sua revisão' : proposal.status === 'pending_instructor_review' ? 'Aguardando revisão do instrutor' : proposal.status === 'client_rejected' ? 'Você recusou esta proposta' : proposal.status}</Typography>
          {proposal.status === 'proposed' && <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}><Button onClick={() => void reviewProposal(proposal.id, true)} variant="contained">Aceitar para revisão profissional</Button><Button onClick={() => void reviewProposal(proposal.id, false)} variant="outlined">Recusar</Button></Stack>}
        </Stack></CardContent></Card>)}
        <Box><StatusNotice severity="info">O assistente explica seu treino, mas não altera o seu plano.</StatusNotice></Box>
      </Stack>
    </ClientShell>
  )
}
