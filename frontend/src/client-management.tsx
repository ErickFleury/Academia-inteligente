import { Box, Button, Card, CardContent, Chip, Divider, FormControlLabel, Stack, Switch, TextField, Typography } from '@mui/material'
import { FormEvent, useEffect, useRef, useState } from 'react'

import { ManagementDialog } from './components/management-dialog'
import { WorkspaceIcon } from './components/workspace-presentation'
import { EmptyState, LoadingState, StatusNotice } from './components/ui'
import { FacialEnrollment } from './components/facial-enrollment'
import { biometricMessage, isBiometricError, personBinding, validProof, type EnrollmentProof } from './biometrics'
import { ApiRequestError, type Client, type ClientInput, createClient, eraseClient, getClient, listClients, lookupPostalCode, provisionClientIdentity, sendOnboardingInvitation, updateClient } from './clients'

type Props = { accessToken: string; onUnauthenticated: () => void }
type Form = ClientInput
const blank: Form = { first_name: '', surname: '', email: '', cpf: '', phone: '', postal_code: '', street: '', number: '', complement: '', neighborhood: '', city: '', state: '' }
const statusText = (client: Client) => client.client_active ? 'Ativo' : 'Inativo'
const fromClient = (client: Client): Form => ({ ...client, complement: client.complement ?? '' })

function Details({ form, id, change, lookup, pending }: { form: Form; id: string; change: (field: keyof Form, value: string) => void; lookup: () => void; pending: boolean }) {
  const input = (key: keyof Form, label: string, required = true, type = 'text') => <TextField autoComplete="off" fullWidth id={`${id}-${key}`} label={label} onChange={(event) => change(key, event.target.value)} required={required} type={type} value={form[key] ?? ''} />
  return <Stack spacing={2}>
    <Typography component="h3" variant="h4">Identificação e contato</Typography>
    <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>{input('first_name', 'Nome')} {input('surname', 'Sobrenome')}</Stack>
    <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>{input('email', 'E-mail', true, 'email')} {input('cpf', 'CPF')}</Stack>
    <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>{input('phone', 'Telefone')}<Stack direction="row" spacing={1} sx={{ width: '100%' }}>{input('postal_code', 'CEP')}<Button disabled={pending || !form.postal_code.trim()} onClick={lookup} sx={{ flexShrink: 0 }} variant="outlined">{pending ? 'Consultando...' : 'Buscar CEP'}</Button></Stack></Stack>
    <Typography component="h3" variant="h4" sx={{ pt: 1 }}>Endereço</Typography>
    <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>{input('street', 'Logradouro')} {input('number', 'Número')}</Stack>
    <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>{input('complement', 'Complemento', false)} {input('neighborhood', 'Bairro')}</Stack>
    <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>{input('city', 'Cidade')} {input('state', 'UF')}</Stack>
  </Stack>
}

export function ClientManagement({ accessToken, onUnauthenticated }: Props) {
  const [createOpen, setCreateOpen] = useState(false)
  const [writing, setWriting] = useState(false)
  const writeLock = useRef(false)
  async function write(operation: () => Promise<void>) {
    if (writeLock.current) return
    writeLock.current = true; setWriting(true)
    try { await operation() } finally { writeLock.current = false; setWriting(false) }
  }
  const [createForm, setCreateForm] = useState<Form>(blank)
  const [enrollmentProof, setEnrollmentProof] = useState<EnrollmentProof | null>(null)
  const registrationCommand = useRef<{ key: string; id: string } | null>(null)
  const [editForm, setEditForm] = useState<Form>(blank)
  const [clientActive, setClientActive] = useState(true)
  const [query, setQuery] = useState('')
  const [clients, setClients] = useState<Client[]>([])
  const [selected, setSelected] = useState<Client | null>(null)
  const [lookupPending, setLookupPending] = useState<'create' | 'edit' | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const message = (reason: unknown, fallback: string) => {
    if (isBiometricError(reason)) return biometricMessage(reason)
    if (reason instanceof ApiRequestError && reason.status === 401) { onUnauthenticated(); return 'Sua sessão expirou. Entre novamente.' }
    if (reason instanceof ApiRequestError && reason.status === 404) return 'CEP não encontrado. Preencha o endereço manualmente.'
    if (reason instanceof ApiRequestError && reason.status === 503) return fallback
    if (reason instanceof ApiRequestError && reason.status === 409) return 'Já existe uma conta com este e-mail ou CPF.'
    if (reason instanceof ApiRequestError && reason.status === 422) {
      const validationMessages: Record<string, string> = {
        'A valid CPF is required': 'Informe um CPF válido.',
        'A valid phone number is required': 'Informe um telefone válido com DDD.',
        'A valid CEP is required': 'Informe um CEP válido.',
        'A valid e-mail address is required': 'Informe um e-mail válido.',
        'A valid state is required': 'Informe uma UF válida.',
      }
      return validationMessages[reason.message] ?? 'Revise os dados obrigatórios do cliente.'
    }
    return reason instanceof ApiRequestError ? fallback : reason instanceof Error ? reason.message : fallback
  }
  const load = async (search = '') => { setLoading(true); setError(null); try { setClients(await listClients(accessToken, search)) } catch (reason) { setError(message(reason, 'Não foi possível carregar clientes.')) } finally { setLoading(false) } }
  useEffect(() => { void load() }, [accessToken])
  const select = (client: Client) => { setSelected(client); setEditForm(fromClient(client)); setClientActive(client.client_active) }
  const change = (kind: 'create' | 'edit', field: keyof Form, value: string) => (kind === 'create' ? setCreateForm : setEditForm)((form) => ({ ...form, [field]: value }))
  async function address(kind: 'create' | 'edit') {
    const form = kind === 'create' ? createForm : editForm; setLookupPending(kind); setError(null)
    try { const result = await lookupPostalCode(accessToken, form.postal_code); (kind === 'create' ? setCreateForm : setEditForm)((current) => ({ ...current, ...Object.fromEntries(Object.entries(result).filter(([, value]) => value)) })) } catch (reason) { setError(message(reason, 'Não foi possível consultar o CEP. Preencha o endereço manualmente.')) } finally { setLookupPending(null) }
  }
  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(null)
    if (!validProof(enrollmentProof, createForm.email, createForm.cpf)) { setError('Conclua a verificação facial antes de cadastrar o cliente.'); return }
    const key = JSON.stringify([createForm, enrollmentProof])
    if (registrationCommand.current?.key !== key) registrationCommand.current = { key, id: crypto.randomUUID() }
    try {
      const client = await createClient(accessToken, createForm, { command_id: registrationCommand.current.id, enrollment_session_id: enrollmentProof?.sessionId ?? null })
      setCreateForm(blank); setEnrollmentProof(null); registrationCommand.current = null
      setSuccess(client.identity_provisioned ? 'Cliente cadastrado com sucesso.' : 'Cliente cadastrado. Provisionamento de acesso pendente.')
      await load(query); setCreateOpen(false); select(client)
    } catch (reason) { setError(message(reason, 'Não foi possível cadastrar o cliente.')) }
  }
  async function update(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!selected) return
    setError(null)
    setSuccess(null)
    try {
      const updated = await updateClient(accessToken, selected.id, { ...editForm, client_active: clientActive })
      setClients((items) => items.map((item) => item.id === updated.id ? updated : item))
      select(updated)
      setSuccess(updated.identity_provisioned ? 'Cliente atualizado com sucesso.' : 'Dados salvos. Sincronização de acesso pendente. Use Provisionar acesso para tentar novamente.')
    } catch (reason) {
      if (reason instanceof ApiRequestError && [409, 503].includes(reason.status)) {
        try { select(await getClient(accessToken, selected.id)); await load(query) } catch { /* Keep the original error visible. */ }
      }
      setError(message(reason, 'Não foi possível concluir a atualização. Consulte os dados salvos e use Provisionar acesso se houver sincronização pendente.'))
    }
  }
  async function provision() { if (!selected) return; setError(null); setSuccess(null); try { const updated = await provisionClientIdentity(accessToken, selected.id); setClients((items) => items.map((item) => item.id === updated.id ? updated : item)); select(updated); setSuccess('Acesso do cliente sincronizado.') } catch (reason) { setError(message(reason, 'Não foi possível provisionar o acesso do cliente.')) } }
  async function invite() { if (!selected) return; try { await sendOnboardingInvitation(accessToken, selected.id); setSuccess('Convite de onboarding enviado. Expira em 24 horas.') } catch (reason) { setError(message(reason, 'Não foi possível enviar o convite de onboarding.')) } }
  async function erase() {
    if (!selected || !window.confirm(`Excluir permanentemente o cadastro de cliente de ${selected.name} e seus dados de cliente? Se houver vínculo como instrutor, ele e o acesso correspondente serão preservados. Esta ação não pode ser desfeita.`)) return
    setError(null)
    setSuccess(null)
    try {
      await eraseClient(accessToken, selected.id)
      setClients((items) => items.filter((item) => item.id !== selected.id))
      setSelected(null)
      setSuccess('Cadastro e dados do cliente excluídos. Um eventual vínculo como instrutor foi preservado.')
    } catch (reason) {
      if (reason instanceof ApiRequestError && reason.message === 'Client data erased; shared identity reconciliation is pending') {
        setSelected(null)
        await load(query)
        setError('Dados do cliente excluídos. O vínculo como instrutor foi preservado, mas a sincronização de acesso está pendente. Use Provisionar acesso no cadastro do instrutor.')
      } else {
        setError(message(reason, 'Não foi possível excluir o cadastro do cliente.'))
      }
    }
  }
  const feedback = <Stack aria-live="polite" spacing={1}>{error && <StatusNotice severity="error">{error}</StatusNotice>}{success && <StatusNotice severity="success">{success}</StatusNotice>}</Stack>
  return <Stack spacing={3} sx={{ width: '100%', minWidth: 0 }}>
    <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} sx={{ justifyContent: 'space-between', alignItems: { sm: 'center' } }}>
      <Box><Typography component="h2" variant="h3">Clientes cadastrados</Typography><Typography color="text.secondary" variant="body2">Encontre um cadastro para consultar dados, acesso e identificação facial.</Typography></Box>
      <Button variant="contained" startIcon={<WorkspaceIcon name="profile" />} onClick={() => { setError(null); setSuccess(null); setCreateOpen(true) }}>Novo cliente</Button>
    </Stack>
    {!createOpen && !selected && feedback}
    <Card component="section"><CardContent><Stack component="form" direction={{ xs: 'column', sm: 'row' }} spacing={2} onSubmit={(event) => { event.preventDefault(); setSelected(null); void load(query) }}><TextField fullWidth label="Pesquisar por nome ou e-mail" onChange={(event) => setQuery(event.target.value)} value={query} /><Button type="submit" variant="outlined">Pesquisar</Button></Stack></CardContent></Card>
    <Stack aria-busy={loading} component="section" spacing={1.5} aria-label="Resultados de clientes">
      {loading ? <LoadingState label="Carregando clientes" /> : <Stack component="ul" spacing={1.25} sx={{ listStyle: 'none', m: 0, p: 0 }}>
        {clients.map((client) => <Box component="li" key={client.id}><Card variant="outlined">
          <Button aria-label={`${client.name} — ${client.email} (${statusText(client)})`} color="inherit" onClick={() => void getClient(accessToken, client.id).then(select).catch((reason) => setError(message(reason, 'Não foi possível carregar o cliente.')))} sx={{ alignItems: 'center', gap: 2, justifyContent: 'space-between', px: 2.5, py: 2, textAlign: 'left', width: '100%' }} variant="text">
            <Stack component="span" spacing={0.5} sx={{ minWidth: 0 }}><Typography component="span" sx={{ color: 'text.primary', fontWeight: 750, overflowWrap: 'anywhere' }}>{client.name}</Typography><Typography component="span" variant="body2" color="text.secondary" sx={{ overflowWrap: 'anywhere' }}>{client.email}</Typography></Stack>
            <Chip component="span" color={client.client_active ? 'success' : 'default'} label={statusText(client)} size="small" variant="outlined" sx={{ flexShrink: 0 }} />
          </Button>
        </Card></Box>)}
        {!clients.length && <EmptyState description="Ajuste a busca ou cadastre o primeiro cliente." title="Nenhum cliente encontrado." />}
      </Stack>}
    </Stack>
    <ManagementDialog open={createOpen} title="Cadastrar cliente" busy={writing || lookupPending === 'create'} busyLabel={lookupPending === 'create' ? 'Consultando CEP' : 'Salvando dados e sincronizando acesso do cliente'} onClose={() => { setCreateOpen(false); setEnrollmentProof(null) }}
      onSubmit={(event) => { event.preventDefault(); void write(() => create(event)) }} feedback={feedback}
      actions={<><Button disabled={writing || lookupPending !== null || !validProof(enrollmentProof, createForm.email, createForm.cpf)} type="submit" variant="contained">{writing ? 'Salvando...' : 'Cadastrar cliente'}</Button><Button disabled={writing || lookupPending === 'create'} onClick={() => { setCreateOpen(false); setEnrollmentProof(null) }}>Fechar</Button></>}>
      <Typography color="text.secondary" variant="body2">Os dados de acesso serão provisionados separadamente. Ao fechar, os campos são mantidos nesta página; verifique o rosto novamente ao reabrir.</Typography>
      <Details change={(field, value) => change('create', field, value)} form={createForm} id="create" lookup={() => void address('create')} pending={lookupPending === 'create'} />
      <FacialEnrollment key={personBinding(createForm.email, createForm.cpf)} token={accessToken} email={createForm.email} cpf={createForm.cpf} role="client" onReady={setEnrollmentProof} onUnauthenticated={onUnauthenticated} />
    </ManagementDialog>
    <ManagementDialog open={selected !== null && !createOpen} title="Editar cliente" busy={writing || lookupPending === 'edit'} busyLabel={lookupPending === 'edit' ? 'Consultando CEP' : 'Salvando dados e sincronizando acesso do cliente'} onClose={() => setSelected(null)}
      onSubmit={(event) => { event.preventDefault(); void write(() => update(event)) }} feedback={feedback}
      actions={<><Button disabled={writing || lookupPending !== null} type="submit" variant="contained">{writing ? 'Salvando...' : 'Salvar alterações'}</Button><Button disabled={writing || lookupPending === 'edit'} onClick={() => setSelected(null)}>Fechar</Button></>}>
      {selected && <>
        <Details change={(field, value) => change('edit', field, value)} form={editForm} id="edit" lookup={() => void address('edit')} pending={lookupPending === 'edit'} />
        <FacialEnrollment key={`${selected.id}:${selected.email}:${selected.cpf}`} token={accessToken} email={selected.email} cpf={selected.cpf} role="client" personId={selected.person_id} onUnauthenticated={onUnauthenticated} />
        <Box sx={{ bgcolor: 'action.hover', p: 2, borderRadius: 2 }}><Stack spacing={2}>
          <Typography component="h3" variant="h4">Acesso e conta</Typography>
          <FormControlLabel control={<Switch checked={clientActive} disabled={writing} onChange={(event) => setClientActive(event.target.checked)} />} label="Cliente ativo" />
          {selected.identity_provisioned === false && <Button onClick={() => void write(provision)} disabled={writing} variant="outlined">{writing ? 'Sincronizando...' : 'Provisionar acesso'}</Button>}
          {selected.identity_provisioned === true && selected.client_active && <Button onClick={() => void write(invite)} disabled={writing} variant="outlined">Enviar convite de onboarding</Button>}
          <Divider />
          <Button color="error" disabled={writing} onClick={() => void write(erase)} sx={{ alignSelf: 'flex-start' }}>Excluir cadastro de cliente</Button>
        </Stack></Box>
      </>}
    </ManagementDialog>
  </Stack>
}
