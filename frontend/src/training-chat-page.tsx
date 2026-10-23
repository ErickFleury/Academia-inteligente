import { Box, Button, Card, CardContent, Stack, TextField, Typography } from '@mui/material'
import { useEffect, useRef, useState } from 'react'

import { WorkspaceIcon } from './components/workspace-presentation'
import { ClientShell } from './components/application-shell'
import { RouterButtonLink } from './components/router-button-link'
import { ChatMessage, EmptyState, LoadingState, PageHeader, StatusNotice } from './components/ui'
import { getOwnTrainingChat, sendTrainingChatMessage, type TrainingChat } from './training-chat'
import { createAdaptation, decideAdaptation, getOwnAdaptations, type TrainingAdaptation } from './training-adaptation'
import { getCurrentTrainingPlan } from './training-plan'
import { useChatAutoScroll } from './use-chat-auto-scroll'

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
  const [pollError, setPollError] = useState(false)
  const submittingRef = useRef<string | null>(null)
  const completedRef = useRef(new Set<string>())
  const scopeRef = useRef(0)
  const processing = chat?.pending_request?.status === 'processing'
  const busy = pending !== null || processing
  const trackedRequestId = pending?.id ?? (processing ? chat?.pending_request?.client_request_id : null)
  const chatEndRef = useChatAutoScroll(chat?.messages.length ?? 0, busy)

  useEffect(() => {
    let active = true
    scopeRef.current += 1
    completedRef.current.clear()
    submittingRef.current = null
    setChat(null); setHasCurrentPlan(null); setPending(null); setRetry(null); setError(null); setMessage('')
    void Promise.all([getOwnTrainingChat(accessToken), getOwnAdaptations(accessToken), getCurrentTrainingPlan(accessToken)])
      .then(([state, proposals, plan]) => { if (active) { setChat(state); setAdaptations(proposals); setHasCurrentPlan(plan !== null) } })
      .catch((reason: unknown) => active && setError(reason instanceof Error ? reason.message : 'Não foi possível carregar sua conversa.'))
    return () => { active = false; scopeRef.current += 1 }
  }, [accessToken])

  useEffect(() => {
    if (!trackedRequestId) return
    let active = true
    let timer: ReturnType<typeof setTimeout>
    async function poll() {
      try {
        const state = await getOwnTrainingChat(accessToken)
        if (!active) return
        setPollError(false)
        const answered = state.messages.some((item) => item.reply_to_client_request_id === trackedRequestId)
        if (answered) completedRef.current.add(trackedRequestId!)
        // A GET started before completion must not overwrite its newer POST reply.
        if (!answered && completedRef.current.has(trackedRequestId!)) return
        setChat(state)
        if (answered || state.pending_request?.client_request_id === trackedRequestId) {
          setPending((item) => item?.id === trackedRequestId ? null : item)
          if (submittingRef.current === trackedRequestId) submittingRef.current = null
        }
        if (answered) { setRetry(null); setError(null); setMessage(''); return }
        if (state.pending_request?.status === 'failed') return
      } catch {
        if (active) setPollError(true)
      }
      if (active) timer = setTimeout(() => void poll(), 1500)
    }
    timer = setTimeout(() => void poll(), 1000)
    return () => { active = false; clearTimeout(timer) }
  }, [accessToken, trackedRequestId])

  async function submit(nextMessage: string, id = requestId()) {
    if (!nextMessage.trim() || busy || submittingRef.current) return
    submittingRef.current = id
    const scope = scopeRef.current
    setPending({ message: nextMessage, id })
    setMessage('')
    setError(null)
    setRetry(null)
    setPollError(false)
    try {
      const state = await sendTrainingChatMessage(accessToken, nextMessage, id)
      if (scope !== scopeRef.current || completedRef.current.has(id)) return
      for (const item of state.messages) {
        if (item.reply_to_client_request_id) completedRef.current.add(item.reply_to_client_request_id)
      }
      setChat(state)
      setMessage('')
      setRetry(null)
    } catch (reason) {
      if (scope !== scopeRef.current || completedRef.current.has(id)) return
      setMessage(nextMessage)
      setError(reason instanceof Error ? reason.message : 'Não foi possível enviar sua mensagem.')
      setRetry({ message: nextMessage, id })
    } finally {
      if (scope === scopeRef.current) {
        setPending((item) => item?.id === id ? null : item)
        if (submittingRef.current === id) submittingRef.current = null
      }
    }
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

  if ((!chat || hasCurrentPlan === null) && error) return <ClientShell onSignOut={onSignOut} showClientNavigation contentMaxWidth="md"><StatusNotice severity="error">{error}</StatusNotice></ClientShell>

  if (!chat || hasCurrentPlan === null) return <ClientShell onSignOut={onSignOut} showClientNavigation contentMaxWidth="md"><LoadingState label="Carregando assistente de treino" /></ClientShell>

  const suggestions = chat.messages.filter((item) => item.role === 'assistant' && item.adaptation_suggested && item.reply_to_client_request_id && item.adaptation_reason)
  const unsaved = pending ?? retry
  const failedRequest = chat.pending_request?.status === 'failed' ? chat.pending_request : null
  const failedMessage = failedRequest && chat.messages.find((item) => item.client_request_id === failedRequest.client_request_id)
  const retryMessage = retry ?? (failedMessage?.client_request_id ? { id: failedMessage.client_request_id, message: failedMessage.content } : null)
  const failureText = failedRequest?.failure_code === 'deadline_exceeded'
    ? 'O assistente não concluiu a resposta no tempo disponível. Sua mensagem foi salva. Você pode tentar novamente.'
    : failedRequest?.failure_code === 'assistant_clarification_required'
      ? 'Confirme as informações relevantes ou consulte seu instrutor antes de gerar a proposta.'
      : failedRequest?.failure_code === 'memory_capacity'
        ? 'Sua memória está cheia. Abra Memória do assistente para revisar as informações antes de continuar.'
        : 'A solicitação não foi concluída. Sua mensagem foi salva. Você pode tentar novamente ou enviar outra mensagem.'

  return (
    <ClientShell onSignOut={onSignOut} showClientNavigation contentMaxWidth="md">
      <Stack spacing={3} sx={{ maxWidth: 880, mx: 'auto', width: '100%', minWidth: 0 }}>
        <PageHeader
          action={<RouterButtonLink to="/treino" variant="outlined">Ver meu treino</RouterButtonLink>}
          description="Tire dúvidas sobre o seu plano atual e seus exercícios. Mudanças no treino precisam de revisão profissional."
          eyebrow="Assistente de treino"
          title="Como posso ajudar hoje?"
        />
        {(error || failedRequest) && !busy && <Stack spacing={1} sx={{ alignItems: 'flex-start' }}><StatusNotice severity="error">{failedRequest ? failureText : error}</StatusNotice>{retryMessage && <Button onClick={() => void submit(retryMessage.message, retryMessage.id)} variant="outlined">Tentar novamente</Button>}</Stack>}
        <Stack aria-live="polite" aria-relevant="additions" spacing={1.5} sx={{ minHeight: 280, p: { xs: 1, sm: 2 }, borderRadius: 3, bgcolor: 'rgba(16,24,27,0.35)' }}>
          {chat.messages.length === 0 && !unsaved
            ? <EmptyState description="Pergunte sobre os exercícios, séries, repetições ou orientações do seu treino atual." title="Seu espaço para tirar dúvidas" />
            : chat.messages.map((item, index) => <ChatMessage key={`${item.created_at}-${index}`} role={item.role}>{item.content}</ChatMessage>)}
          {unsaved && !chat.messages.some((item) => item.client_request_id === unsaved.id) && <ChatMessage role="user">{unsaved.message}</ChatMessage>}
          {busy && <Box role="status" aria-label="Status da solicitação"><StatusNotice severity="info">{pollError ? 'Não foi possível verificar o andamento. Tentando reconectar…' : processing ? 'O assistente está processando sua solicitação. Você pode atualizar a página; a resposta aparecerá aqui.' : 'Enviando sua mensagem… Aguardando confirmação do recebimento.'}</StatusNotice></Box>}
        </Stack>
        <Box aria-hidden="true" ref={chatEndRef} sx={{ height: 1, scrollMarginBottom: { xs: 184, sm: 132 } }} />
        <Card aria-busy={busy} component="form" onSubmit={(event) => { event.preventDefault(); void submit(message) }} sx={{ bottom: 16, position: 'sticky', zIndex: 1, borderColor: 'rgba(255,133,100,0.35)', boxShadow: '0 12px 40px rgba(0,0,0,0.25)' }}>
          <CardContent>
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5}>
              <TextField autoComplete="off" fullWidth label="Escreva sua pergunta" multiline onChange={(event) => setMessage(event.target.value)} onKeyDown={(event) => { if (event.key !== 'Enter' || event.shiftKey || event.nativeEvent.isComposing) return; event.preventDefault(); void submit(message) }} disabled={busy} helperText="Enter para enviar · Shift + Enter para uma nova linha" placeholder="Conte o que precisa; você pode reunir dúvidas e corrigir informações." value={message} />
              <Button disabled={!message.trim() || busy} type="submit" variant="contained" startIcon={<WorkspaceIcon name="send" />}>{busy ? (processing ? 'Processando…' : 'Enviando…') : 'Enviar'}</Button>
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
        <Box><StatusNotice severity="info">O assistente pode atualizar o rascunho em edição quando você pedir. Você pode reunir informações e corrigir apenas um dado, sem recomeçar a conversa. Seu plano atual só muda após revisão profissional. A conversa é mantida por 30 dias.</StatusNotice></Box>
      </Stack>
    </ClientShell>
  )
}
