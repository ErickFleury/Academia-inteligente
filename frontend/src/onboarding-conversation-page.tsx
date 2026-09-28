import { Box, Button, Card, CardContent, Chip, Stack, TextField, Typography } from '@mui/material'
import { useEffect, useState } from 'react'

import { WorkspaceIcon } from './components/workspace-presentation'
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

function answerLabel(name: string, value: string | number | boolean | null): string {
  if (typeof value === 'boolean') return value ? 'Sim' : 'Não'
  if (name === 'training_experience') return ({ none: 'Nenhuma', beginner: 'Iniciante', intermediate: 'Intermediária', advanced: 'Avançada' } as Record<string, string>)[String(value)] ?? String(value)
  if (name === 'height_cm') return `${value} cm`
  if (name === 'weight_kg') return `${new Intl.NumberFormat('pt-BR').format(Number(value))} kg`
  return String(value)
}

function createRequestId(): string {
  return crypto.randomUUID()
}

export function OnboardingConversationPage({ accessToken, onSignOut }: OnboardingConversationPageProps) {
  const [conversation, setConversation] = useState<OnboardingConversation | null>(null)
  const [draft, setDraft] = useState<OnboardingDraft | null>(null)
  const [message, setMessage] = useState('')
  const [directValue, setDirectValue] = useState('')
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
      setDirectValue('')
      setRetry(null)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Não foi possível continuar a conversa.')
      setRetry({ message: nextMessage, requestId })
    } finally {
      setPending(null)
    }
  }

  if (!conversation && error) {
    return <ClientShell onSignOut={onSignOut} showClientNavigation contentMaxWidth="md"><StatusNotice severity="error">{error}</StatusNotice></ClientShell>
  }

  if (!conversation) {
    return <ClientShell onSignOut={onSignOut} showClientNavigation contentMaxWidth="md"><LoadingState label="Carregando conversa de onboarding" /></ClientShell>
  }

  const missing = conversation.missing_required_fields.map((field) => fieldLabels[field] ?? field)
  const known = Object.entries(conversation.known_answers ?? {}).filter(([, value]) => value !== null)
  const clarification = (conversation.clarification_fields ?? []).map((field) => fieldLabels[field] ?? field)
  return (
    <ClientShell onSignOut={onSignOut} showClientNavigation contentMaxWidth="md">
      <Stack spacing={3} sx={{ maxWidth: 880, mx: 'auto', width: '100%' }}>
        <PageHeader
          action={<RouterButtonLink to="/onboarding" variant="outlined">Preencher formulário</RouterButtonLink>}
          description="Converse no seu ritmo. Você pode informar vários dados na mesma mensagem e corrigir apenas o que precisar."
          eyebrow="Onboarding guiado"
          title="Vamos montar seu perfil de treino"
        />
        <Card component="section">
          <CardContent>
            <Stack spacing={1.25}>
              <Typography component="h2" variant="h3">Progresso do onboarding</Typography>
              {conversation.needs_clarification && <StatusNotice severity="info">{clarification.length ? `Precisamos confirmar: ${clarification.join(', ')}. As outras respostas foram mantidas.` : 'Diga qual informação deseja corrigir. As outras respostas foram mantidas.'}</StatusNotice>}
              {conversation.completion_ready
                ? <StatusNotice severity="success">As informações obrigatórias estão prontas para a próxima etapa.</StatusNotice>
                : <><Typography color="text.secondary">{missing.length ? 'Ainda precisamos destas informações:' : 'Confirme os dados indicados para continuar.'}</Typography><Stack direction="row" spacing={1} useFlexGap sx={{ flexWrap: 'wrap', gap: 1 }}>{missing.map((field) => <Chip key={field} label={field} />)}</Stack></>}
            </Stack>
          </CardContent>
        </Card>
        {known.length > 0 && <Card component="section"><CardContent><Stack spacing={1.5}>
          <Typography component="h2" variant="h3">Respostas já coletadas</Typography>
          <Box component="dl" sx={{ m: 0, display: 'grid', gridTemplateColumns: { xs: '1fr', sm: 'minmax(150px, 1fr) 2fr' }, gap: 1 }}>
            {known.map(([name, value]) => <Box key={name} sx={{ display: 'contents' }}>
              <Typography component="dt" color="text.secondary">{fieldLabels[name] ?? name}</Typography>
              <Typography component="dd" sx={{ m: 0, overflowWrap: 'anywhere' }}>{answerLabel(name, value)}</Typography>
            </Box>)}
          </Box>
          <Typography color="text.secondary" variant="body2">Para corrigir, diga por exemplo: “Na verdade, meu peso é 82 kg”. A conversa é mantida por cinco dias; revise o formulário para concluir.</Typography>
        </Stack></CardContent></Card>}
        {conversation.fallback_field && <Card component="section"><CardContent><Stack spacing={1.5}>
          <Typography component="h2" variant="h3">Vamos preencher este dado diretamente</Typography>
          <Typography color="text.secondary">Suas outras respostas continuam salvas na conversa.</Typography>
          {['height_cm', 'weight_kg'].includes(conversation.fallback_field) && <Box component="form" onSubmit={(event) => {
            event.preventDefault()
            const value = directValue.trim().replace(',', '.')
            if (!/^\d+(?:\.\d+)?$/.test(value) || Number(value) <= 0) return
            const isWeight = conversation.fallback_field === 'weight_kg'
            void submit(`Na verdade, ${isWeight ? 'meu peso é' : 'minha altura é'} ${value} ${isWeight ? 'kg' : 'cm'}`)
          }}><Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5}>
            <TextField label={conversation.fallback_field === 'weight_kg' ? 'Peso em kg' : 'Altura em cm'} value={directValue} onChange={(event) => setDirectValue(event.target.value)} disabled={pending !== null} slotProps={{ htmlInput: { inputMode: 'decimal', maxLength: 10 } }} />
            <Button type="submit" variant="contained" disabled={pending !== null || !/^\d+(?:[.,]\d+)?$/.test(directValue.trim()) || Number(directValue.replace(',', '.')) <= 0}>Confirmar medida</Button>
          </Stack></Box>}
          <Box><RouterButtonLink to="/onboarding" variant="outlined">Usar formulário de onboarding</RouterButtonLink></Box>
        </Stack></CardContent></Card>}
        {error && <Stack spacing={1}><StatusNotice severity="error">{error}</StatusNotice>{retry && <Box><Button onClick={() => void submit(retry.message, retry.requestId)} variant="outlined">Tentar novamente</Button></Box>}</Stack>}
        <Stack aria-live="polite" spacing={1.5} sx={{ minHeight: 240, p: { xs: 1, sm: 2 }, borderRadius: 3, bgcolor: 'rgba(16,24,27,0.35)' }}>
          {conversation.messages.length === 0
            ? <EmptyState description="Você pode responder por mensagem ou usar o formulário quando preferir." title="Comece quando estiver pronto" />
            : conversation.messages.map((item, index) => <ChatMessage key={`${item.created_at}-${index}`} role={item.role}>{item.content}</ChatMessage>)}
        </Stack>
        <Box aria-hidden="true" ref={chatEndRef} sx={{ height: 1, scrollMarginBottom: { xs: 184, sm: 132 } }} />
        {conversation.messages.length === 0 && <Box><Button disabled={pending !== null} onClick={() => void submit('Quero começar meu onboarding.')} variant="contained">Começar conversa</Button></Box>}
        {draft?.status !== 'completed' && conversation.completion_ready && <Card component="section"><CardContent><Stack spacing={1.5}><Typography component="h2" variant="h3">Revise suas informações</Typography><Typography color="text.secondary">Confira os dados no formulário antes de concluir o onboarding.</Typography><Box><RouterButtonLink to="/onboarding" variant="contained">Revisar e confirmar informações</RouterButtonLink></Box></Stack></CardContent></Card>
        }
        {draft?.status !== 'completed' && <Card aria-busy={pending !== null} component="form" onSubmit={(event) => { event.preventDefault(); void submit(message) }} sx={{ position: 'sticky', bottom: 16, zIndex: 1, borderColor: 'rgba(255,133,100,0.35)', boxShadow: '0 12px 40px rgba(0,0,0,0.25)' }}>
            <CardContent>
              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5}>
                <TextField
                  autoComplete="off"
                  fullWidth
                  label="Escreva sua resposta"
                  multiline
                  onChange={(event) => setMessage(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key !== 'Enter' || event.shiftKey || event.nativeEvent.isComposing) return
                    event.preventDefault()
                    void submit(message)
                  }}
                  helperText="Enter para enviar · Shift + Enter para uma nova linha"
                  disabled={pending !== null}
                  placeholder="Ex.: Tenho 1,80 m e peso 80 kg."
                  value={message}
                />
                <Button disabled={!message.trim() || pending !== null} type="submit" variant="contained" startIcon={<WorkspaceIcon name="send" />}>{pending ? 'Enviando…' : 'Enviar'}</Button>
              </Stack>
            </CardContent>
          </Card>}
      </Stack>
    </ClientShell>
  )
}
