import { Alert, Button, CircularProgress, Stack, TextField, Typography } from '@mui/material'
import { FormEvent, useEffect, useState } from 'react'

import { type Client, createClient, getClient, listClients } from './clients'

type ClientManagementProps = {
  accessToken: string
}

export function ClientManagement({ accessToken }: ClientManagementProps) {
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [query, setQuery] = useState('')
  const [clients, setClients] = useState<Client[]>([])
  const [selectedClient, setSelectedClient] = useState<Client | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  async function loadClients(search = '') {
    setLoading(true)
    setError(null)
    try {
      setClients(await listClients(accessToken, search))
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Não foi possível carregar clientes.')
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
      setSelectedClient(client)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Não foi possível cadastrar o cliente.')
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
      setSelectedClient(await getClient(accessToken, clientId))
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Não foi possível carregar o cliente.')
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
                {client.name} — {client.email}
              </Button>
            </li>
          ))}
          {!clients.length && <Typography>Nenhum cliente encontrado.</Typography>}
        </Stack>
      )}
      {selectedClient && (
        <Alert severity="info">
          Cliente selecionado: {selectedClient.name} ({selectedClient.email})
        </Alert>
      )}
    </Stack>
  )
}
