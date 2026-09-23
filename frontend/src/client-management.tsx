import {
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Divider,
  FormControlLabel,
  Stack,
  Switch,
  TextField,
  Typography,
} from '@mui/material'
import { FormEvent, useEffect, useState } from 'react'

import { EmptyState, LoadingState, StatusNotice } from './components/ui'
import {
  ApiRequestError,
  type Client,
  createClient,
  getClient,
  listClients,
  provisionClientIdentity,
  sendOnboardingInvitation,
  updateClient,
  eraseClient,
} from './clients'

type ClientManagementProps = {
  accessToken: string
  onUnauthenticated: () => void
}

function accountStatus(client: Client) {
  return client.account_active ? 'Ativo' : 'Inativo'
}

export function ClientManagement({ accessToken, onUnauthenticated }: ClientManagementProps) {
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [query, setQuery] = useState('')
  const [clients, setClients] = useState<Client[]>([])
  const [selectedClient, setSelectedClient] = useState<Client | null>(null)
  const [editName, setEditName] = useState('')
  const [editEmail, setEditEmail] = useState('')
  const [editAccountActive, setEditAccountActive] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  function errorMessage(reason: unknown, fallback: string): string {
    if (reason instanceof ApiRequestError && reason.status === 401) {
      onUnauthenticated()
      return 'Sua sessão expirou. Entre novamente.'
    }
    if (reason instanceof ApiRequestError && reason.message === 'An account already uses this e-mail address') {
      return 'Já existe uma conta com este e-mail.'
    }
    if (reason instanceof ApiRequestError) return fallback
    return reason instanceof Error ? reason.message : fallback
  }

  async function loadClients(search = '') {
    setLoading(true)
    setError(null)
    try {
      setClients(await listClients(accessToken, search))
    } catch (reason) {
      setError(errorMessage(reason, 'Não foi possível carregar clientes.'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadClients()
  }, [accessToken])

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    setSuccess(null)
    try {
      const client = await createClient(accessToken, name, email)
      setName('')
      setEmail('')
      setSuccess(client.identity_provisioned ? 'Cliente cadastrado com sucesso.' : 'Cliente cadastrado. Provisionamento de acesso pendente.')
      await loadClients(query)
      selectClient(client)
    } catch (reason) {
      setError(errorMessage(reason, 'Não foi possível cadastrar o cliente.'))
    }
  }

  async function handleSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSelectedClient(null)
    await loadClients(query)
  }

  async function handleSelect(clientId: string) {
    setError(null)
    try {
      selectClient(await getClient(accessToken, clientId))
    } catch (reason) {
      setError(errorMessage(reason, 'Não foi possível carregar o cliente.'))
    }
  }

  function selectClient(client: Client) {
    setSelectedClient(client)
    setEditName(client.name)
    setEditEmail(client.email)
    setEditAccountActive(client.account_active)
  }

  async function handleUpdate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!selectedClient) return
    setError(null)
    setSuccess(null)
    try {
      const updated = await updateClient(accessToken, selectedClient.id, {
        name: editName,
        email: editEmail,
        account_active: editAccountActive,
      })
      setClients((currentClients) => currentClients.map((client) => (client.id === updated.id ? updated : client)))
      selectClient(updated)
      setSuccess('Cliente atualizado com sucesso.')
    } catch (reason) {
      setError(errorMessage(reason, 'Não foi possível atualizar o cliente.'))
    }
  }

  async function handleProvisionIdentity() {
    if (!selectedClient) return
    setError(null)
    setSuccess(null)
    try {
      const updated = await provisionClientIdentity(accessToken, selectedClient.id)
      setClients((currentClients) => currentClients.map((client) => (client.id === updated.id ? updated : client)))
      selectClient(updated)
      setSuccess('Acesso do cliente provisionado. O cliente recebeu instruções para criar a senha.')
    } catch (reason) {
      setError(errorMessage(reason, 'Não foi possível provisionar o acesso do cliente.'))
    }
  }

  async function handleSendOnboardingInvitation() {
    if (!selectedClient) return
    setError(null)
    setSuccess(null)
    try {
      await sendOnboardingInvitation(accessToken, selectedClient.id)
      setSuccess('Convite de onboarding enviado. Expira em 24 horas.')
    } catch (reason) {
      setError(errorMessage(reason, 'Não foi possível enviar o convite de onboarding.'))
    }
  }

  async function handleErase() {
    if (!selectedClient || !window.confirm(`Excluir permanentemente ${selectedClient.name} e todos os seus dados? Esta ação não pode ser desfeita.`)) return
    try {
      await eraseClient(accessToken, selectedClient.id)
      setClients((items) => items.filter((item) => item.id !== selectedClient.id))
      setSelectedClient(null)
      setSuccess('Conta e dados do cliente excluídos permanentemente.')
    } catch (reason) { setError(errorMessage(reason, 'Não foi possível excluir a conta do cliente.')) }
  }

  return (
    <Stack spacing={3} sx={{ width: '100%' }}>
      <Stack aria-live="polite" spacing={1}>
        {error && <StatusNotice severity="error">{error}</StatusNotice>}
        {success && <StatusNotice severity="success">{success}</StatusNotice>}
      </Stack>

      <Card component="section">
        <CardContent>
          <Stack component="form" spacing={2.5} onSubmit={handleCreate}>
            <Box>
              <Typography color="primary.main" variant="overline">Novo cadastro</Typography>
              <Typography component="h2" variant="h3">Cadastrar cliente</Typography>
              <Typography color="text.secondary" sx={{ mt: 0.5 }}>Os dados de acesso serão provisionados separadamente.</Typography>
            </Box>
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
              <TextField autoComplete="name" fullWidth label="Nome" onChange={(event) => setName(event.target.value)} required value={name} />
              <TextField autoComplete="email" fullWidth label="E-mail" onChange={(event) => setEmail(event.target.value)} required type="email" value={email} />
            </Stack>
            <Box><Button type="submit" variant="contained">Cadastrar cliente</Button></Box>
          </Stack>
        </CardContent>
      </Card>

      <Card component="section">
        <CardContent>
          <Stack component="form" direction={{ xs: 'column', sm: 'row' }} spacing={2} onSubmit={handleSearch}>
            <TextField fullWidth label="Pesquisar por nome ou e-mail" onChange={(event) => setQuery(event.target.value)} value={query} />
            <Button type="submit" variant="outlined">Pesquisar</Button>
          </Stack>
        </CardContent>
      </Card>

      <Stack aria-busy={loading} component="section" spacing={1.5} aria-label="Resultados de clientes">
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} sx={{ alignItems: { xs: 'flex-start', sm: 'center' }, justifyContent: 'space-between' }}>
          <Typography component="h2" variant="h3">Clientes cadastrados</Typography>
          {!loading && <Typography color="text.secondary" variant="body2">{clients.length} {clients.length === 1 ? 'resultado' : 'resultados'}</Typography>}
        </Stack>
        {loading ? <LoadingState label="Carregando clientes" /> : (
          <Stack component="ul" spacing={1.25} sx={{ listStyle: 'none', m: 0, p: 0 }}>
            {clients.map((client) => (
              <Box component="li" key={client.id}>
                <Card variant="outlined">
                  <Button
                    aria-label={`${client.name} — ${client.email} (${accountStatus(client)})`}
                    color="inherit"
                    onClick={() => void handleSelect(client.id)}
                    sx={{ alignItems: 'center', gap: 1.5, justifyContent: 'space-between', px: 2, py: 1.5, textAlign: 'left', width: '100%' }}
                    variant="text"
                  >
                    <Stack spacing={0.25} sx={{ minWidth: 0 }}>
                      <Typography sx={{ color: 'text.primary', fontWeight: 750, overflowWrap: 'anywhere' }}>{client.name} — {client.email}</Typography>
                      <Typography color="text.secondary" variant="body2">Selecionar para consultar ou editar</Typography>
                    </Stack>
                    <Chip color={client.account_active ? 'success' : 'default'} label={accountStatus(client)} size="small" />
                  </Button>
                </Card>
              </Box>
            ))}
            {!clients.length && <EmptyState description="Ajuste a busca ou cadastre o primeiro cliente." title="Nenhum cliente encontrado." />}
          </Stack>
        )}
      </Stack>

      {selectedClient && (
        <Card component="section" sx={{ borderColor: 'primary.main' }}>
          <CardContent>
            <Stack component="form" spacing={2.5} onSubmit={handleUpdate}>
              <Box>
                <Typography color="primary.main" variant="overline">Perfil e acesso</Typography>
                <Typography component="h2" variant="h3">Editar cliente</Typography>
              </Box>
              <Divider />
              <TextField autoComplete="name" fullWidth label="Nome do cliente" onChange={(event) => setEditName(event.target.value)} required value={editName} />
              <TextField autoComplete="email" fullWidth label="E-mail do cliente" onChange={(event) => setEditEmail(event.target.value)} required type="email" value={editEmail} />
              <FormControlLabel
                control={<Switch checked={editAccountActive} onChange={(event) => setEditAccountActive(event.target.checked)} />}
                label="Conta ativa"
              />
              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.25}>
                <Button type="submit" variant="contained">Salvar alterações</Button>
                {selectedClient.identity_provisioned === false && <Button onClick={() => void handleProvisionIdentity()} variant="outlined">Provisionar acesso</Button>}
                {selectedClient.identity_provisioned === true && selectedClient.account_active && <Button onClick={() => void handleSendOnboardingInvitation()} variant="outlined">Enviar convite de onboarding</Button>}
              </Stack>
              <Button color="error" onClick={() => void handleErase()} variant="outlined">Excluir conta permanentemente</Button>
            </Stack>
          </CardContent>
        </Card>
      )}
    </Stack>
  )
}
