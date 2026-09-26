import { Box, Button, Card, CardContent, Chip, Stack, TextField, Typography } from '@mui/material'
import { useEffect, useState } from 'react'

import { ClientShell } from './components/application-shell'
import { RouterButtonLink } from './components/router-button-link'
import { ChatMessage, EmptyState, LoadingState, PageHeader, StatusNotice } from './components/ui'
import { useChatAutoScroll } from './use-chat-auto-scroll'
import {
  getOwnOnboardingConversation,
  sendOnboardingConversationMessage,
  type OnboardingConversation,
} from './onboarding-conversation'
import { getOwnOnboardingDraft, type OnboardingDraft } from './onboarding-draft'

type OnboardingConversationPageProps = {
  accessToken: string
  onSignOut: () => void
}

const fieldLabels: Record<string, string> = {
  training_goal: 'objetivo de treino',
  training_experience: 'experiência de treino',
  height_cm: 'altura',
  weight_kg: 'peso',
  has_limitations_or_complaints: 'resposta sobre limitações ou queixas',
  limitations_or_complaints: 'detalhes de limitações ou queixas',
  uses_medications: 'resposta sobre medicações',
  medications: 'detalhes de medicações',
  has_health_conditions: 'resposta sobre condições de saúde',
  health_conditions: 'detalhes de condições de saúde',
}

function createRequestId(): string {
  return crypto.randomUUID()
}

export function OnboardingConversationPage({ accessToken, onSignOut }: OnboardingConversationPageProps) {
  const [conversation, setConversation] = useState<OnboardingConversation | null>(null)
  const [draft, setDraft] = useState<OnboardingDraft | null>(null)
  const [message, setMessage] = useState('')
  const [pending, setPending] = useState<{ message: string; requestId: string } | null>(null)
  const [retry, setRetry] = useState<{ message: string; requestId: string } | null>(null)
  const [error, setError] = useState<string | null>(null)
  const chatEndRef = useChatAutoScroll(conversation?.messages.length ?? 0, pending !== null)

  useEffect(() => {
    let active = true
    void Promise.all([getOwnOnboardingConversation(accessToken), getOwnOnboardingDraft(accessToken)])
      .then(([state, loadedDraft]) => {
        if (active) {
          setConversation(state)
          setDraft(loadedDraft)
        }
      })
      .catch((reason: unknown) => active && setError(reason instanceof Error ? reason.message : 'Não foi possível carregar a conversa.'))
    return () => { active = false }
  }, [accessToken])

  async function submit(nextMessage: string, requestId = createRequestId()) {
    if (!nextMessage.trim() || pending) return
    setPending({ message: nextMessage, requestId })
    setError(null)
    try {
      setConversation(await sendOnboardingConversationMessage(accessToken, nextMessage, requestId))
      setMessage('')
      setRetry(null)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Não foi possível continuar a conversa.')
      setRetry({ message: nextMessage, requestId })
    } finally {
      setPending(null)
    }
  }

  if (!conversation) {
    return <ClientShell onSignOut={onSignOut} showClientNavigation><LoadingState label="Carregando conversa de onboarding" /></ClientShell>
  }

  const missing = conversation.missing_required_fields.map((field) => fieldLabels[field] ?? field)
  return (
    <ClientShell onSignOut={onSignOut} showClientNavigation>
      <Stack spacing={3} sx={{ maxWidth: 880 }}>
        <PageHeader
          action={<RouterButtonLink to="/onboarding" variant="outlined">Preencher formulário</RouterButtonLink>}
          description="Converse no seu ritmo. Quando a entrevista estiver pronta, as informações são validadas antes de entrar no seu onboarding."
          eyebrow="Onboarding guiado"
          title="Vamos montar seu perfil de treino"
        />
        <Card component="section">
          <CardContent>
            <Stack spacing={1.25}>
              <Typography component="h2" variant="h3">Progresso do onboarding</Typography>
              {conversation.completion_ready
                ? <StatusNotice severity="success">As informações obrigatórias estão prontas para a próxima etapa.</StatusNotice>
                : <><Typography color="text.secondary">Ainda precisamos destas informações:</Typography><Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap', gap: 1 }}>{missing.map((field) => <Chip key={field} label={field} />)}</Stack></>}
            </Stack>
          </CardContent>
        </Card>
        {error && <Stack spacing={1}><StatusNotice severity="error">{error}</StatusNotice>{retry && <Box><Button onClick={() => void submit(retry.message, retry.requestId)} variant="outlined">Tentar novamente</Button></Box>}</Stack>}
        <Stack aria-live="polite" spacing={1.5} sx={{ minHeight: 240 }}>
          {conversation.messages.length === 0
            ? <EmptyState description="Você pode responder por mensagem ou usar o formulário quando preferir." title="Comece quando estiver pronto" />
            : conversation.messages.map((item, index) => <ChatMessage key={`${item.created_at}-${index}`} role={item.role}>{item.content}</ChatMessage>)}
        </Stack>
        <Box aria-hidden="true" ref={chatEndRef} sx={{ height: 1, scrollMarginBottom: { xs: 184, sm: 132 } }} />
        {conversation.messages.length === 0 && <Box><Button disabled={pending !== null} onClick={() => void submit('Quero começar meu onboarding.')} variant="contained">Começar conversa</Button></Box>}
        {draft?.status !== 'completed' && (conversation.completion_ready
          ? <Card component="section"><CardContent><Stack spacing={1.5}><Typography component="h2" variant="h3">Revise suas informações</Typography><Typography color="text.secondary">Confira os dados no formulário antes de concluir o onboarding.</Typography><Box><RouterButtonLink to="/onboarding" variant="contained">Revisar e confirmar informações</RouterButtonLink></Box></Stack></CardContent></Card>
          : <Card component="form" onSubmit={(event) => { event.preventDefault(); void submit(message) }} sx={{ position: 'sticky', bottom: 16 }}>
            <CardContent>
              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5}>
                <TextField
                  autoComplete="off"
                  fullWidth
                  label="Escreva sua resposta"
                  multiline
                  onChange={(event) => setMessage(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key !== 'Enter') return
                    event.preventDefault()
                    void submit(message)
                  }}
                  placeholder="Conte com suas palavras o que você quer alcançar."
                  value={message}
                />
                <Button disabled={!message.trim() || pending !== null} type="submit" variant="contained">{pending ? 'Enviando…' : 'Enviar'}</Button>
              </Stack>
            </CardContent>
          </Card>)}
      </Stack>
    </ClientShell>
  )
}
