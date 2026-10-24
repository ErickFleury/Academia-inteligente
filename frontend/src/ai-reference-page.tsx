import { Alert, Button, Card, Chip, Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle, LinearProgress, Stack, TextField, Typography } from '@mui/material'
import { useEffect, useRef, useState } from 'react'
import { AdminShell } from './components/application-shell'
import { EmptyState, LoadingState, PageHeader } from './components/ui'
import { deleteReference, listReferences, previewReference, referenceAction, uploadReference, type ReferencePreview, type ReferenceVersion } from './ai-references'

const statuses: Record<string, string> = { pending: 'Na fila', processing: 'Processando', ready: 'Pronta para ativar', active: 'Ativa', withdrawn: 'Retirada', failed: 'Falha no processamento' }
const extractionErrors: Record<string, string> = {
  document_text_limit: 'O texto extraído excede o limite configurado de caracteres. Divida o documento em arquivos menores e envie novamente.',
  document_extraction_timeout: 'A leitura do documento excedeu o tempo permitido. Divida o PDF em arquivos menores e envie novamente.',
  document_page_limit: 'O PDF excede o limite de páginas configurado. Divida o documento em arquivos menores; o limite máximo é de 1.000 páginas por PDF.',
  document_no_text: 'Nenhum texto legível encontrado. Envie um PDF com texto selecionável ou um arquivo TXT/Markdown.',
  document_extraction_failed: 'Não foi possível ler este documento. Confira se não está protegido, digitalizado ou acima dos limites.',
  timeout_or_network: 'O serviço de processamento está indisponível. Você pode tentar novamente.',
}
export function AiReferencePage({ accessToken, onSignOut }: { accessToken: string; onSignOut: () => void }) {
  const [items, setItems] = useState<ReferenceVersion[]>([])
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [title, setTitle] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [replacement, setReplacement] = useState<ReferenceVersion | null>(null)
  const [preview, setPreview] = useState<{ item: ReferenceVersion; passages: ReferencePreview[]; offset: number } | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)
  const [confirmation, setConfirmation] = useState<ReferenceVersion | null>(null)
  const [deletion, setDeletion] = useState<ReferenceVersion | null>(null)
  const requestId = useRef(0)
  const previewId = useRef(0)
  const working = useRef(false)
  async function refresh() {
    const id = ++requestId.current
    try { const data = await listReferences(accessToken); if (id === requestId.current) setItems(data) }
    catch (reason) { if (id === requestId.current) setError(reason instanceof Error ? reason.message : 'Não foi possível carregar as referências.') }
    finally { if (id === requestId.current) setLoading(false) }
  }
  useEffect(() => {
    void refresh()
    const timer = window.setInterval(() => { void refresh() }, 5000)
    return () => { window.clearInterval(timer); requestId.current++; previewId.current++ }
  }, [accessToken])
  async function perform(action: () => Promise<void>) {
    if (working.current) return
    working.current = true; setBusy(true); setError(null); setNotice(null)
    try { await action(); await refresh() }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Não foi possível concluir a ação.'); await refresh() }
    finally { working.current = false; setBusy(false) }
  }
  async function openPreview(item: ReferenceVersion, offset = 0) {
    const id = ++previewId.current
    setPreviewLoading(true); setPreview({ item, passages: [], offset })
    try { const passages = await previewReference(accessToken, item.id, offset); if (id === previewId.current) setPreview({ item, passages, offset }) }
    catch (reason) { if (id === previewId.current) setError(reason instanceof Error ? reason.message : 'Não foi possível abrir a prévia.') }
    finally { if (id === previewId.current) setPreviewLoading(false) }
  }
  return <AdminShell onSignOut={onSignOut}>
    <PageHeader eyebrow="Assistente" title="Referências do assistente" description="Envie materiais de fontes confiáveis e confira o texto antes de ativá-los." />
    <Stack spacing={2}>
      {error && !deletion && <Alert severity="error">{error}</Alert>}
      {notice && <Alert severity="success">{notice}</Alert>}
      <Card variant="outlined" sx={{ p: 2 }}><Stack spacing={2}>
        <Typography variant="h6">{replacement ? `Nova versão: ${replacement.title}` : 'Adicionar referência'}</Typography>
        <TextField label="Título da referência" value={title} onChange={(e) => setTitle(e.target.value)} disabled={busy || Boolean(replacement)} slotProps={{ htmlInput: { maxLength: 200 } }} />
        <Button component="label" variant="outlined" disabled={busy}>Escolher documento<input hidden type="file" accept=".pdf,.md,.txt" onChange={(e) => setFile(e.target.files?.[0] || null)} /></Button>
        <Typography variant="body2">{file?.name || 'PDF com texto selecionável, Markdown ou TXT. Até 150 MB e 1.000 páginas.'}</Typography>
        <Stack direction="row" spacing={1}>
          <Button disabled={busy || !title.trim() || !file} onClick={() => void perform(async () => {
            await uploadReference(accessToken, title.trim(), file!, replacement?.source_id)
            setTitle(''); setFile(null); setReplacement(null); setNotice('Documento enviado. Acompanhe o processamento abaixo.')
          })}>Enviar para processamento</Button>
          {replacement && <Button disabled={busy} onClick={() => { setReplacement(null); setTitle(''); setFile(null) }}>Cancelar substituição</Button>}
        </Stack>
      </Stack></Card>
      {loading ? <LoadingState label="Carregando referências" /> : items.length === 0 ? <EmptyState title="Nenhuma referência cadastrada" description="Adicione o primeiro material para apoiar as respostas do assistente." /> : items.map((item) => <Card key={item.id} variant="outlined" sx={{ p: 2 }}><Stack spacing={1}>
        <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap' }}><Typography variant="h6">{item.title} · versão {item.number}</Typography><Chip label={statuses[item.status] || 'Aguardando atualização'} color={item.active ? 'success' : 'default'} /></Stack>
        {item.status === 'processing' && <LinearProgress variant="determinate" value={item.progress} aria-label={`Processamento de ${item.title}`} />}
        {item.status === 'failed' && <Alert severity="warning">{extractionErrors[item.error_code || ''] || 'O processamento falhou. Confira o arquivo e a disponibilidade do serviço antes de tentar novamente.'}</Alert>}
        <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap' }}>
          {['ready', 'active', 'withdrawn'].includes(item.status) && <Button disabled={busy} onClick={() => void openPreview(item)}>Conferir texto</Button>}
          {item.active && <Button color="warning" disabled={busy} onClick={() => setConfirmation(item)}>Retirar referência</Button>}
          <Button disabled={busy} onClick={() => { setReplacement(item); setTitle(item.title); setFile(null) }}>Enviar nova versão</Button>
          {item.status === 'failed' && <Button disabled={busy} onClick={() => void perform(async () => { await referenceAction(accessToken, item, 'retry') })}>Tentar processamento novamente</Button>}
          <Button color="error" disabled={busy} onClick={() => { setError(null); setDeletion(item) }}>Excluir referência</Button>
        </Stack>
      </Stack></Card>)}
    </Stack>
    <Dialog open={Boolean(preview)} onClose={() => { previewId.current++; setPreview(null) }} fullWidth maxWidth="md">
      <DialogTitle>Texto extraído: {preview?.item.title}</DialogTitle>
      <DialogContent>{previewLoading ? <LoadingState label="Abrindo prévia" /> : <Stack spacing={2}>{preview?.passages.map((p) => <Typography key={p.position} sx={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{p.content}</Typography>)}</Stack>}</DialogContent>
      <DialogActions>
        <Button disabled={!preview || preview.offset === 0 || previewLoading} onClick={() => preview && void openPreview(preview.item, Math.max(0, preview.offset - 20))}>Anterior</Button>
        <Button disabled={!preview || preview.passages.length < 20 || previewLoading} onClick={() => preview && void openPreview(preview.item, preview.offset + 20)}>Próximos trechos</Button>
        {preview?.item.status === 'ready' && <Button disabled={busy || previewLoading || preview.passages.length === 0} onClick={() => void perform(async () => {
          const current = items.find((v) => v.id === preview.item.id) || preview.item
          await referenceAction(accessToken, current, 'activate'); setPreview(null); setNotice('Referência ativada.')
        })}>Ativar esta versão</Button>}
        <Button onClick={() => { previewId.current++; setPreview(null) }}>Fechar</Button>
      </DialogActions>
    </Dialog>
    <Dialog open={Boolean(confirmation)} onClose={() => !busy && setConfirmation(null)}>
      <DialogTitle>Retirar referência?</DialogTitle><DialogContent>Este material deixará de apoiar novas respostas do assistente.</DialogContent>
      <DialogActions><Button disabled={busy} onClick={() => setConfirmation(null)}>Cancelar</Button><Button disabled={busy} color="warning" onClick={() => void perform(async () => {
        await referenceAction(accessToken, confirmation!, 'withdraw'); setConfirmation(null); setNotice('Referência retirada.')
      })}>Retirar</Button></DialogActions>
    </Dialog>
    <Dialog open={Boolean(deletion)} onClose={() => !busy && setDeletion(null)} fullWidth maxWidth="sm" aria-labelledby="excluir-referencia-titulo" aria-describedby="excluir-referencia-descricao">
      <DialogTitle id="excluir-referencia-titulo">Excluir referência permanentemente?</DialogTitle>
      <DialogContent><Stack spacing={2}>
        <DialogContentText id="excluir-referencia-descricao" sx={{ overflowWrap: 'anywhere' }}>
          Excluir “{deletion?.title}” e todas as versões? Os arquivos enviados, o texto extraído e os dados de busca do assistente serão removidos permanentemente. Esta ação não pode ser desfeita.
        </DialogContentText>
        {busy && <LinearProgress aria-label="Excluindo referência" />}
        {error && <Alert severity="error">{error}</Alert>}
      </Stack></DialogContent>
      <DialogActions sx={{ flexWrap: 'wrap' }}>
        <Button autoFocus disabled={busy} onClick={() => setDeletion(null)}>Cancelar</Button>
        <Button color="error" disabled={busy} onClick={() => void perform(async () => {
          const sourceId = deletion!.source_id
          await deleteReference(accessToken, deletion!)
          requestId.current++
          setItems((current) => current.filter((item) => item.source_id !== sourceId))
          if (preview?.item.source_id === sourceId) { previewId.current++; setPreview(null) }
          if (replacement?.source_id === sourceId) { setReplacement(null); setTitle(''); setFile(null) }
          setDeletion(null); setNotice('Referência e todas as versões excluídas permanentemente.')
        })}>{busy ? 'Excluindo…' : 'Excluir permanentemente'}</Button>
      </DialogActions>
    </Dialog>
  </AdminShell>
}
