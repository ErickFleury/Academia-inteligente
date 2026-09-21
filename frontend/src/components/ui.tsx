import { Alert, Box, CircularProgress, Stack, Typography } from '@mui/material'
import type { ReactNode } from 'react'

type PageHeaderProps = {
  eyebrow?: string
  title: string
  description?: string
  action?: ReactNode
}

export function PageHeader({ eyebrow, title, description, action }: PageHeaderProps) {
  return (
    <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} sx={{ justifyContent: 'space-between', mb: 3 }}>
      <Box>
        {eyebrow && <Typography color="primary.main" variant="overline">{eyebrow}</Typography>}
        <Typography component="h1" variant="h2">{title}</Typography>
        {description && <Typography color="text.secondary" sx={{ maxWidth: 680, mt: 1 }}>{description}</Typography>}
      </Box>
      {action && <Box sx={{ alignSelf: { xs: 'flex-start', sm: 'center' } }}>{action}</Box>}
    </Stack>
  )
}

export function LoadingState({ label }: { label: string }) {
  return (
    <Stack aria-live="polite" spacing={1.5} sx={{ alignItems: 'center', py: 5 }}>
      <CircularProgress aria-label={label} />
      <Typography color="text.secondary">{label}</Typography>
    </Stack>
  )
}

export function EmptyState({ title, description }: { title: string; description: string }) {
  return (
    <Stack spacing={0.75} sx={{ alignItems: 'flex-start', border: '1px dashed', borderColor: 'divider', borderRadius: 2, p: 3 }}>
      <Typography component="h3" variant="h4">{title}</Typography>
      <Typography color="text.secondary">{description}</Typography>
    </Stack>
  )
}

export function StatusNotice({ severity, children }: { severity: 'error' | 'success' | 'info'; children: ReactNode }) {
  return <Alert severity={severity} variant="outlined">{children}</Alert>
}

export function ChatMessage({ role, children }: { role: 'user' | 'assistant'; children: ReactNode }) {
  const isUser = role === 'user'
  return (
    <Box
      component="article"
      sx={{
        alignSelf: isUser ? 'flex-end' : 'flex-start',
        bgcolor: isUser ? 'primary.main' : 'background.paper',
        border: isUser ? 0 : '1px solid',
        borderColor: 'divider',
        borderRadius: 2.5,
        color: isUser ? 'primary.contrastText' : 'text.primary',
        maxWidth: { xs: '92%', sm: '76%' },
        px: 2,
        py: 1.5,
      }}
    >
      <Typography component="p" sx={{ whiteSpace: 'pre-wrap' }}>{children}</Typography>
    </Box>
  )
}
