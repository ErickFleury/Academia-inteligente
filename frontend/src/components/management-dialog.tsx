import { Box, Dialog, DialogActions, DialogContent, DialogTitle, IconButton, LinearProgress, Stack, Typography, useMediaQuery, useTheme } from '@mui/material'
import { useId, type FormEvent, type ReactNode } from 'react'
import { WorkspaceIcon } from './workspace-presentation'

type Props = {
  open: boolean; title: string; busy: boolean; busyLabel: string;
  onClose: () => void; onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  feedback: ReactNode; children: ReactNode; actions: ReactNode;
}

/** One focused form, with feedback and actions inside the dialog's focus boundary. */
export function ManagementDialog({ open, title, busy, busyLabel, onClose, onSubmit, feedback, children, actions }: Props) {
  const titleId = useId()
  const phone = useMediaQuery(useTheme().breakpoints.down('sm'))
  return <Dialog open={open} onClose={() => { if (!busy) onClose() }} fullScreen={phone} fullWidth maxWidth="md" aria-labelledby={titleId}>
    <Box component="form" onSubmit={onSubmit} sx={{ display: 'flex', flexDirection: 'column', overflow: 'hidden', minHeight: 0 }}>
      <DialogTitle id={titleId} component="h2" sx={{ pr: 1.5 }}>
        <Stack direction="row" sx={{ alignItems: 'center', justifyContent: 'space-between', gap: 1 }}>
          {title}<IconButton aria-label="Fechar formulário" disabled={busy} onClick={onClose}><WorkspaceIcon name="close" /></IconButton>
        </Stack>
      </DialogTitle>
      <DialogContent dividers><Stack spacing={3} sx={{ pt: 1 }}>
        {busy && <Stack spacing={1} role="status"><LinearProgress aria-label={busyLabel}/><Typography variant="body2">{busyLabel}</Typography></Stack>}
        {feedback}
        {children}
      </Stack></DialogContent>
      <DialogActions sx={{ p: 2, gap: 1, flexWrap: 'wrap', justifyContent: 'flex-start' }}>{actions}</DialogActions>
    </Box>
  </Dialog>
}
