import { Alert, Button, Card, Chip, Dialog, DialogActions, DialogContent, DialogTitle, Stack, TextField, Typography } from '@mui/material'
import { useEffect, useRef, useState } from 'react'
import { ClientShell } from './components/application-shell'
import { EmptyState, LoadingState, PageHeader } from './components/ui'
import { correctMemory, forgetMemory, getMemory, type MemoryFact, type MemorySnapshot } from './assistant-memory'

const categories = { health_report: 'Relato de saúde', preference: 'Preferência', training_goal: 'Objetivo de treino' }
export function AssistantMemoryPage({ accessToken, onSignOut }: { accessToken: string; onSignOut: () => void }) {
  const [snapshot, setSnapshot] = useState<MemorySnapshot | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [selection, setSelection] = useState<{ fact: MemoryFact; revision: number; action: 'edit' | 'forget' } | null>(null)
  const [text, setText] = useState('')
  const requestId = useRef(0)
  const working = useRef(false)
  async function refresh() {
    const id = ++requestId.current
    setLoading(true)
    try { const data = await getMemory(accessToken); if (id === requestId.current) { setSnapshot(data); setError(null) } }
    catch (reason) { if (id === requestId.current) setError(reason instanceof Error ? reason.message : 'Não foi possível carregar sua memória.') }
    finally { if (id === requestId.current) setLoading(false) }
  }
  useEffect(() => { setSnapshot(null); setSelection(null); setBusy(false); working.current = false; void refresh(); return () => { requestId.current++ } }, [accessToken])
  async function save() {
    if (!selection || working.current) return
    working.current = true; setBusy(true); setError(null); setNotice(null)
    const id = ++requestId.current
    try {
      const result = selection.action === 'edit'
        ? await correctMemory(accessToken, selection.fact.id, selection.revision, text.trim())
        : await forgetMemory(accessToken, selection.fact.id, selection.revision)
      if (id === requestId.current) { setSnapshot(result); setSelection(null); setNotice('Memória atualizada.') }
    } catch (reason) {
      if (id === requestId.current) { setError(reason instanceof Error ? reason.message : 'Não foi possível atualizar sua memória.'); setSelection(null) }
    } finally { if (id === requestId.current) { working.current = false; setBusy(false) } }
  }
  return <ClientShell onSignOut={onSignOut} showClientNavigation>
    <PageHeader eyebrow="Assistente" title="Memória do assistente" description="Confira os relatos e preferências que ajudam o assistente a dar continuidade às suas conversas." />
    <Stack spacing={2}>
      <Alert severity="info">Estas informações são relatos seus, guardados até você removê-los ou sua conta de cliente ser excluída. Corrigir ou esquecer uma memória não altera seu formulário de saúde nem um treino aprovado.</Alert>
      {error && <Alert severity="error" action={<Button color="inherit" disabled={busy} onClick={() => void refresh()}>Atualizar lista</Button>}>{error}</Alert>}
      {notice && <Alert severity="success">{notice}</Alert>}
      {loading ? <LoadingState label="Carregando sua memória" /> : snapshot && snapshot.facts.length === 0
        ? <EmptyState title="Nenhuma memória guardada" description="Informações claras que você compartilhar em novas conversas poderão aparecer aqui. Você poderá conferir, corrigir ou remover cada uma." />
        : snapshot?.facts.map((fact) => <Card variant="outlined" sx={{ p: 2 }} key={fact.id}><Stack spacing={1}>
          <Chip sx={{ alignSelf: 'flex-start' }} label={categories[fact.category]} />
          <Typography sx={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{fact.text}</Typography>
          <Typography variant="body2" color="text.secondary">{fact.attribution === 'client_edit' ? 'Corrigido por você' : 'Relatado por você'} em {new Date(fact.reported_at).toLocaleDateString('pt-BR')}.</Typography>
          {fact.category === 'health_report' && <Typography variant="body2">O assistente pode pedir que você confirme se este relato continua atual.</Typography>}
          <Stack direction="row" spacing={1}>
            <Button disabled={busy} aria-label={`Corrigir: ${fact.text}`} onClick={() => { setSelection({ fact, revision: snapshot.revision, action: 'edit' }); setText(fact.text) }}>Corrigir</Button>
            <Button disabled={busy} color="warning" aria-label={`Esquecer: ${fact.text}`} onClick={() => setSelection({ fact, revision: snapshot.revision, action: 'forget' })}>Esquecer</Button>
          </Stack>
        </Stack></Card>)}
    </Stack>
    <Dialog open={Boolean(selection)} onClose={() => { if (!busy) setSelection(null) }} fullWidth maxWidth="sm">
      <DialogTitle>{selection?.action === 'edit' ? 'Corrigir memória' : 'Esquecer esta memória?'}</DialogTitle>
      <DialogContent>{selection?.action === 'edit'
        ? <TextField autoFocus fullWidth multiline minRows={3} margin="dense" label="Seu relato ou preferência" value={text} disabled={busy} onChange={(e) => setText(e.target.value)} slotProps={{ htmlInput: { maxLength: 400 } }} helperText={`${text.length}/400 caracteres`} />
        : <Typography>A informação será removida da memória. Mensagens antigas não poderão recriá-la. Seu formulário de saúde e treino aprovado seguem seus próprios processos de atualização.</Typography>}</DialogContent>
      <DialogActions><Button disabled={busy} onClick={() => setSelection(null)}>Cancelar</Button><Button disabled={busy || (selection?.action === 'edit' && !text.trim())} onClick={() => void save()} color={selection?.action === 'forget' ? 'warning' : 'primary'}>{selection?.action === 'edit' ? 'Salvar correção' : 'Confirmar esquecimento'}</Button></DialogActions>
    </Dialog>
  </ClientShell>
}
