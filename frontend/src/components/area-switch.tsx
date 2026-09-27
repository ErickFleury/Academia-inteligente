import { Box, SvgIcon, Typography } from '@mui/material'
import { alpha } from '@mui/material/styles'
import { useContext } from 'react'

import { SessionContext } from '../session-context'
import { RouterButtonLink } from './router-button-link'

export type ApplicationArea = 'client' | 'instructor'

export function AreaSwitch({ area, onNavigate }: { area: ApplicationArea; onNavigate?: () => void }) {
  const session = useContext(SessionContext)
  if (!session?.roles.includes('client') || !session.roles.includes('instructor')) return null

  const instructor = area === 'instructor'
  const currentLabel = instructor ? 'Área do instrutor' : 'Área do cliente'
  const targetLabel = instructor ? 'Área do cliente' : 'Área do instrutor'

  return (
    <Box
      sx={(theme) => ({
        mt: 2,
        mb: 1.5,
        p: 1.5,
        border: '1px solid',
        borderColor: alpha(theme.palette.primary.main, 0.25),
        borderRadius: 2,
        bgcolor: alpha(theme.palette.primary.main, 0.045),
      })}
    >
      <Typography component="p" variant="overline" color="text.secondary">Área atual</Typography>
      <Typography component="p" variant="body2" sx={{ fontWeight: 750, mb: 1.5 }}>
        {currentLabel}
      </Typography>
      <RouterButtonLink
        aria-label={`Mudar para a ${targetLabel.toLocaleLowerCase('pt-BR')}`}
        fullWidth
        onClick={onNavigate}
        startIcon={
          <SvgIcon aria-hidden="true" sx={{ fontSize: 20 }}>
            <path d="M7 7h13m-4-4 4 4-4 4M17 17H4m4-4-4 4 4 4" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
          </SvgIcon>
        }
        sx={{ justifyContent: 'flex-start', minHeight: 44, px: 1.25, textAlign: 'left' }}
        to={instructor ? '/cliente' : '/instrutor/feed'}
        variant="outlined"
      >
        {targetLabel}
      </RouterButtonLink>
    </Box>
  )
}
