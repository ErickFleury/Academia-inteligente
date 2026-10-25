import { Alert, Container, CssBaseline, MenuItem, Stack, TextField, ThemeProvider } from '@mui/material'
import { useState } from 'react'
import { createRoot } from 'react-dom/client'

import { TrainingPrescriptionReview } from './components/training-prescription-review'
import { developmentAccepted, developmentSaved } from './prescription-development-fixtures'
import { theme } from './theme'
import type { PrescriptionOutcome } from './training-prescription'

if (!import.meta.env.DEV) throw new Error('Development preview only')

function Preview() {
  const [scenario, setScenario] = useState('accepted')
  const [role, setRole] = useState<'client' | 'instructor'>('client')
  const rejected: PrescriptionOutcome = { status: 'rejected', category: scenario === 'outage' ? 'technical_unavailability' : 'insufficient_support', reason_codes: [], message: '' }
  return <ThemeProvider theme={theme}><CssBaseline /><Container maxWidth="md" sx={{ py: 3 }}><Stack spacing={3}>
    <Alert severity="warning">Desenvolvimento isolado: todos os dados e parâmetros desta tela são fictícios. Não há conexão com contas reais, gravação ou aprovação de treinos.</Alert>
    <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
      <TextField select label="Cenário de desenvolvimento" value={scenario} onChange={(event) => setScenario(event.target.value)} fullWidth>
        <MenuItem value="accepted">Proposta verificada fictícia</MenuItem><MenuItem value="rejected">Lacuna de evidências</MenuItem><MenuItem value="outage">Serviço indisponível</MenuItem><MenuItem value="confirmation">Confirmação de informações</MenuItem>
      </TextField>
      <TextField select label="Perfil de desenvolvimento" value={role} onChange={(event) => setRole(event.target.value as 'client' | 'instructor')} fullWidth><MenuItem value="client">Aluno fictício</MenuItem><MenuItem value="instructor">Instrutor fictício</MenuItem></TextField>
    </Stack>
    <TrainingPrescriptionReview role={role} outcome={scenario === 'accepted' ? developmentAccepted : scenario === 'confirmation' ? undefined : rejected}
      savedDraft={scenario === 'rejected' ? developmentSaved : undefined}
      confirmation={scenario === 'confirmation' ? { snapshotHash: 'ficticio', facts: [{ id: 'goal', label: 'Objetivo', value: 'Objetivo fictício' }] } : undefined}
      onConfirm={async () => undefined} onSubmit={async () => undefined} onAssumeManual={async () => undefined} onRetry={() => setScenario('accepted')} />
  </Stack></Container></ThemeProvider>
}

createRoot(document.getElementById('root')!).render(<Preview />)
