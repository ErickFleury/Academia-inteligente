import { Box, Button, Card, CardContent, Chip, FormControlLabel, Stack, Switch, TextField, Typography } from '@mui/material'
import { FormEvent, useEffect, useRef, useState } from 'react'

import { ManagementDialog } from './components/management-dialog'
import { WorkspaceIcon } from './components/workspace-presentation'
import { EmptyState, LoadingState, StatusNotice } from './components/ui'
import { FacialEnrollment } from './components/facial-enrollment'
import { biometricMessage, isBiometricError, personBinding, validProof, type EnrollmentProof } from './biometrics'
import { ApiRequestError } from './clients'
import { type Employee, type EmployeeInput, createEmployee, getEmployee, listEmployees, lookupPostalCode, provisionEmployeeIdentity, updateEmployee } from './employees'

type Props = { accessToken: string; onUnauthenticated: () => void }
const blank: EmployeeInput = { first_name: '', surname: '', email: '', cpf: '', phone: '', postal_code: '', street: '', number: '', complement: '', neighborhood: '', city: '', state: '', cnpj: '', specialization: 'instructor' }
const fields: Array<[keyof EmployeeInput, string, boolean?]> = [['first_name', 'Nome'], ['surname', 'Sobrenome'], ['email', 'E-mail'], ['cpf', 'CPF'], ['phone', 'Telefone'], ['postal_code', 'CEP'], ['street', 'Logradouro'], ['number', 'Número'], ['complement', 'Complemento', false], ['neighborhood', 'Bairro'], ['city', 'Cidade'], ['state', 'UF'], ['cnpj', 'CNPJ (opcional)', false]]

function PersonForm({ form, onChange, lookup, lookupPending }: { form: EmployeeInput; onChange: (field: keyof EmployeeInput, value: string) => void; lookup: () => void; lookupPending: boolean }) {
  return <Stack spacing={3}>{[
    { title: 'Identificação e contato', fields: fields.slice(0, 5) },
    { title: 'Endereço', fields: fields.slice(5, 12) },
    { title: 'Dados profissionais', fields: fields.slice(12) },
  ].map((group) => <Stack key={group.title} spacing={2}>
    <Typography component="h3" variant="h4">{group.title}</Typography>
    <Box sx={{ display: 'grid', gridTemplateColumns: { xs: 'minmax(0, 1fr)', sm: 'repeat(2, minmax(0, 1fr))' }, gap: 2 }}>
      {group.fields.map(([field, label, required = true]) => <Stack key={field} spacing={1} sx={{ minWidth: 0 }}>
        <TextField fullWidth label={label} onChange={(event) => onChange(field, event.target.value)} required={required} type={field === 'email' ? 'email' : 'text'} value={form[field] ?? ''} />
        {field === 'postal_code' && <Button disabled={lookupPending || !form.postal_code.trim()} onClick={lookup} variant="outlined">{lookupPending ? 'Consultando...' : 'Buscar CEP'}</Button>}
      </Stack>)}
    </Box>
  </Stack>)}</Stack>
}

export function EmployeeManagement({ accessToken, onUnauthenticated }: Props) {
  const [createOpen, setCreateOpen] = useState(false)
  const [enrollmentProof, setEnrollmentProof] = useState<EnrollmentProof | null>(null)
  const registrationCommand = useRef<{ key: string; id: string } | null>(null)
  const [writing, setWriting] = useState(false)
  const writeLock = useRef(false)
  async function write(operation: () => Promise<void>) {
    if (writeLock.current) return
    writeLock.current = true; setWriting(true)
    try { await operation() } finally { writeLock.current = false; setWriting(false) }
  }
  const [createForm, setCreateForm] = useState(blank); const [editForm, setEditForm] = useState(blank); const [employees, setEmployees] = useState<Employee[]>([]); const [selected, setSelected] = useState<Employee | null>(null); const [active, setActive] = useState(true); const [query, setQuery] = useState(''); const [loading, setLoading] = useState(true); const [lookingUp, setLookingUp] = useState<'create' | 'edit' | null>(null); const [notice, setNotice] = useState<string | null>(null); const [error, setError] = useState<string | null>(null)
  const message = (reason: unknown, fallback: string, addressLookup = false) => {
    if (isBiometricError(reason)) return biometricMessage(reason)
    if (!(reason instanceof ApiRequestError)) return fallback
    if (reason.status === 401) { onUnauthenticated(); return 'Sua sessão expirou. Entre novamente.' }
    if (addressLookup) return reason.status === 404 ? 'CEP não encontrado. Preencha o endereço manualmente.' : fallback
    if (reason.status === 409) return 'Já existe uma conta incompatível com este e-mail ou CPF.'
    if (reason.status === 404) return 'Instrutor não encontrado. Atualize a lista e tente novamente.'
    if (reason.status === 422) return 'Verifique os dados informados: nome, e-mail, CPF, telefone, endereço e CNPJ opcional devem ser válidos.'
    if (reason.status === 503) return 'Sincronização de acesso pendente. Consulte os dados salvos e use Provisionar acesso para tentar novamente.'
    return fallback
  }
  const load = async (search = '') => { setLoading(true); try { setEmployees(await listEmployees(accessToken, search)) } catch (reason) { setError(message(reason, 'Não foi possível carregar instrutores.')) } finally { setLoading(false) } }
  useEffect(() => { void load() }, [accessToken])
  const select = (employee: Employee) => { setSelected(employee); setEditForm({ ...employee, complement: employee.complement ?? '', cnpj: employee.cnpj ?? '' }); setActive(employee.employee_active) }
  const change = (mode: 'create' | 'edit', field: keyof EmployeeInput, value: string) => (mode === 'create' ? setCreateForm : setEditForm)((form) => ({ ...form, [field]: value }))
  async function lookup(mode: 'create' | 'edit') { const form = mode === 'create' ? createForm : editForm; setLookingUp(mode); setError(null); try { const address = await lookupPostalCode(accessToken, form.postal_code); (mode === 'create' ? setCreateForm : setEditForm)((value) => ({ ...value, ...Object.fromEntries(Object.entries(address).filter(([, item]) => item)) })) } catch (reason) { setError(message(reason, 'Não foi possível consultar o CEP. Preencha o endereço manualmente.', true)) } finally { setLookingUp(null) } }
  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(null)
    if (!validProof(enrollmentProof, createForm.email, createForm.cpf)) { setError('Conclua a verificação facial antes de cadastrar o instrutor.'); return }
    const key = JSON.stringify([createForm, enrollmentProof])
    if (registrationCommand.current?.key !== key) registrationCommand.current = { key, id: crypto.randomUUID() }
    try {
      const employee = await createEmployee(accessToken, createForm, { command_id: registrationCommand.current.id, enrollment_session_id: enrollmentProof?.sessionId ?? null })
      setCreateForm(blank); setEnrollmentProof(null); registrationCommand.current = null
      setCreateOpen(false); select(employee); setNotice(employee.identity_provisioned ? 'Instrutor cadastrado com sucesso.' : 'Instrutor cadastrado. Provisionamento de acesso pendente.'); await load(query)
    } catch (reason) { setError(message(reason, 'Não foi possível cadastrar o instrutor.')) }
  }
  async function update(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!selected) return
    setError(null)
    setNotice(null)
    try {
      const employee = await updateEmployee(accessToken, selected.id, { ...editForm, employee_active: active })
      select(employee)
      setEmployees((items) => items.map((item) => item.id === employee.id ? employee : item))
      setNotice(employee.identity_provisioned ? 'Instrutor atualizado com sucesso.' : 'Dados salvos. Sincronização de acesso pendente. Use Provisionar acesso para tentar novamente.')
    } catch (reason) {
      if (reason instanceof ApiRequestError && [409, 503].includes(reason.status)) {
        try { select(await getEmployee(accessToken, selected.id)); await load(query) } catch { /* Keep the original error visible. */ }
      }
      setError(message(reason, 'Não foi possível concluir a atualização. Consulte os dados salvos e use Provisionar acesso se houver sincronização pendente.'))
    }
  }
  async function provision() { if (!selected) return; setError(null); setNotice(null); try { const employee = await provisionEmployeeIdentity(accessToken, selected.id); select(employee); setNotice('Acesso do instrutor sincronizado.') } catch (reason) { setError(message(reason, 'Não foi possível provisionar o acesso.')) } }
  const feedback = <Stack aria-live="polite" spacing={1}>{error && <StatusNotice severity="error">{error}</StatusNotice>}{notice && <StatusNotice severity="success">{notice}</StatusNotice>}</Stack>
  return <Stack spacing={3} sx={{ minWidth: 0 }}>
    <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} sx={{ justifyContent: 'space-between', alignItems: { sm: 'center' } }}>
      <Box><Typography component="h2" variant="h3">Instrutores cadastrados</Typography><Typography color="text.secondary" variant="body2">Gerencie os dados e o acesso da equipe de instrutores.</Typography></Box>
      <Button variant="contained" startIcon={<WorkspaceIcon name="clients" />} onClick={() => { setError(null); setNotice(null); setCreateOpen(true) }}>Novo instrutor</Button>
    </Stack>
    {!createOpen && !selected && feedback}
    <Card><CardContent><Stack component="form" direction={{ xs: 'column', sm: 'row' }} onSubmit={(event) => { event.preventDefault(); void load(query) }} spacing={2}><TextField fullWidth label="Pesquisar por nome ou e-mail" onChange={(event) => setQuery(event.target.value)} value={query} /><Button type="submit" variant="outlined">Pesquisar</Button></Stack></CardContent></Card>
    <Stack component="section" aria-label="Resultados de instrutores" aria-busy={loading} spacing={1.5}>
      {loading ? <LoadingState label="Carregando instrutores" /> : employees.length ? employees.map((employee) => <Card key={employee.id} variant="outlined">
        <Button color="inherit" aria-label={`${employee.name} — ${employee.email} (${employee.employee_active ? 'Ativo' : 'Inativo'})`} onClick={() => void getEmployee(accessToken, employee.id).then(select).catch((reason) => setError(message(reason, 'Não foi possível carregar o instrutor.')))} sx={{ alignItems: 'center', gap: 2, textAlign: 'left', justifyContent: 'space-between', px: 2.5, py: 2, width: '100%' }}>
          <Stack component="span" spacing={0.5} sx={{ minWidth: 0 }}><Typography component="span" sx={{ fontWeight: 750, overflowWrap: 'anywhere' }}>{employee.name}</Typography><Typography component="span" variant="body2" color="text.secondary" sx={{ overflowWrap: 'anywhere' }}>{employee.email}</Typography></Stack>
          <Chip component="span" color={employee.employee_active ? 'success' : 'default'} label={employee.employee_active ? 'Ativo' : 'Inativo'} size="small" variant="outlined" sx={{ flexShrink: 0 }} />
        </Button>
      </Card>) : <EmptyState description="Cadastre o primeiro instrutor da equipe." title="Nenhum instrutor encontrado." />}
    </Stack>
    <ManagementDialog open={createOpen} title="Cadastrar instrutor" busy={writing || lookingUp === 'create'} busyLabel={lookingUp === 'create' ? 'Consultando CEP' : 'Salvando dados e sincronizando acesso do instrutor'} onClose={() => { setCreateOpen(false); setEnrollmentProof(null) }}
      onSubmit={(event) => { event.preventDefault(); void write(() => create(event)) }} feedback={feedback}
      actions={<><Button disabled={writing || lookingUp !== null || !validProof(enrollmentProof, createForm.email, createForm.cpf)} type="submit" variant="contained">{writing ? 'Salvando...' : 'Cadastrar instrutor'}</Button><Button disabled={writing || lookingUp === 'create'} onClick={() => { setCreateOpen(false); setEnrollmentProof(null) }}>Fechar</Button></>}>
      <Typography color="text.secondary" variant="body2">A especialização deste cadastro é Instrutor. Ao fechar, os campos são mantidos nesta página; verifique o rosto novamente ao reabrir.</Typography>
      <PersonForm form={createForm} lookup={() => void lookup('create')} lookupPending={lookingUp === 'create'} onChange={(field, value) => change('create', field, value)} />
      <FacialEnrollment key={personBinding(createForm.email, createForm.cpf)} token={accessToken} email={createForm.email} cpf={createForm.cpf} role="employee" onReady={setEnrollmentProof} onUnauthenticated={onUnauthenticated} />
    </ManagementDialog>
    <ManagementDialog open={selected !== null && !createOpen} title="Editar instrutor" busy={writing || lookingUp === 'edit'} busyLabel={lookingUp === 'edit' ? 'Consultando CEP' : 'Salvando dados e sincronizando acesso do instrutor'} onClose={() => setSelected(null)}
      onSubmit={(event) => { event.preventDefault(); void write(() => update(event)) }} feedback={feedback}
      actions={<><Button disabled={writing || lookingUp !== null} type="submit" variant="contained">{writing ? 'Salvando...' : 'Salvar alterações'}</Button><Button disabled={writing || lookingUp === 'edit'} onClick={() => setSelected(null)}>Fechar</Button></>}>
      {selected && <>
        <PersonForm form={editForm} lookup={() => void lookup('edit')} lookupPending={lookingUp === 'edit'} onChange={(field, value) => change('edit', field, value)} />
        <FacialEnrollment key={`${selected.id}:${selected.email}:${selected.cpf}`} token={accessToken} email={selected.email} cpf={selected.cpf} role="employee" personId={selected.person_id} onUnauthenticated={onUnauthenticated} />
        <Box sx={{ bgcolor: 'action.hover', p: 2, borderRadius: 2 }}><Stack spacing={2}>
          <Typography component="h3" variant="h4">Acesso e conta</Typography>
          <FormControlLabel control={<Switch checked={active} disabled={writing} onChange={(event) => setActive(event.target.checked)} />} label="Instrutor ativo" />
          {!selected.identity_provisioned && <Button onClick={() => void write(provision)} disabled={writing} variant="outlined">{writing ? 'Sincronizando...' : 'Provisionar acesso'}</Button>}
        </Stack></Box>
      </>}
    </ManagementDialog>
  </Stack>
}
