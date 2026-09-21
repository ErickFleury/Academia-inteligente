import {
  Alert,
  Button,
  CircularProgress,
  FormControlLabel,
  Stack,
  Switch,
  TextField,
  Typography,
} from '@mui/material'
import { FormEvent, useEffect, useState } from 'react'

import {
  ApiRequestError,
  type Client,
  createClient,
  getClient,
  listClients,
  provisionClientIdentity,
  sendOnboardingInvitation,
  updateClient,
} from './clients'

type ClientManagementProps = {
  accessToken: string
  onUnauthenticated: () => void
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
      setSuccess('Cliente cadastrado com sucesso.')
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
      setClients((currentClients) =>
        currentClients.map((client) => (client.id === updated.id ? updated : client)),
      )
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

  return (
    <Stack spacing={2} sx={{ width: '100%' }}>
      <Typography component="h2" variant="h5">
        Clientes
      </Typography>
      {error && <Alert severity="error">{error}</Alert>}
      {success && <Alert severity="success">{success}</Alert>}
      <Stack component="form" spacing={2} onSubmit={handleCreate} sx={{ width: '100%' }}>
        <Typography component="h3" variant="h6">
          Cadastrar cliente
        </Typography>
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
          <TextField
            fullWidth
            label="Nome"
            onChange={(event) => setName(event.target.value)}
            required
            value={name}
          />
          <TextField
            fullWidth
            label="E-mail"
            onChange={(event) => setEmail(event.target.value)}
            required
            type="email"
            value={email}
          />
        </Stack>
        <Button sx={{ alignSelf: 'flex-start' }} type="submit" variant="contained">
          Cadastrar cliente
        </Button>
      </Stack>
      <Stack component="form" direction={{ xs: 'column', sm: 'row' }} spacing={2} onSubmit={handleSearch}>
        <TextField
          fullWidth
          label="Pesquisar por nome ou e-mail"
          onChange={(event) => setQuery(event.target.value)}
          value={query}
        />
        <Button type="submit" variant="outlined">
          Pesquisar
        </Button>
      </Stack>
      {loading ? (
        <CircularProgress aria-label="Carregando clientes" />
      ) : (
        <Stack component="ul" spacing={1} sx={{ listStyle: 'none', m: 0, p: 0 }}>
          {clients.map((client) => (
            <li key={client.id}>
              <Button onClick={() => void handleSelect(client.id)} variant="text">
                {client.name} — {client.email} ({client.account_active ? 'Ativo' : 'Inativo'})
              </Button>
            </li>
          ))}
          {!clients.length && <Typography>Nenhum cliente encontrado.</Typography>}
        </Stack>
      )}
      {selectedClient && (
        <Stack component="form" spacing={2} onSubmit={handleUpdate}>
          <Typography component="h3" variant="h6">
            Editar cliente
          </Typography>
          <TextField
            fullWidth
            label="Nome do cliente"
            onChange={(event) => setEditName(event.target.value)}
            required
            value={editName}
          />
          <TextField
            fullWidth
            label="E-mail do cliente"
            onChange={(event) => setEditEmail(event.target.value)}
            required
            type="email"
            value={editEmail}
          />
          <FormControlLabel
            control={
              <Switch
                checked={editAccountActive}
                onChange={(event) => setEditAccountActive(event.target.checked)}
              />
            }
            label="Conta ativa"
          />
          <Button sx={{ alignSelf: 'flex-start' }} type="submit" variant="contained">
            Salvar alterações
          </Button>
          {selectedClient.identity_provisioned === false && (
            <Button onClick={() => void handleProvisionIdentity()} variant="outlined">
              Provisionar acesso
            </Button>
          )}
          {selectedClient.identity_provisioned === true && selectedClient.account_active && (
            <Button onClick={() => void handleSendOnboardingInvitation()} variant="outlined">
              Enviar convite de onboarding
            </Button>
          )}
        </Stack>
      )}
    </Stack>
  )
}
