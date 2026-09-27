import { SvgIcon } from '@mui/material'
import { alpha, createTheme } from '@mui/material/styles'
import { createContext } from 'react'
import { theme } from '../theme'

// Shared by authenticated client, instructor and admin sidebars; authentication retains its theme.
export const WorkspacePresentationContext = createContext(false)
export const workspaceTheme = createTheme(theme, {
  typography: {
    h2: { fontSize: 'clamp(1.75rem, 3vw, 2.6rem)', lineHeight: 1.15, letterSpacing: '-0.045em', fontWeight: 800 },
    h3: { fontSize: '1.2rem', lineHeight: 1.4, fontWeight: 750 },
    body1: { lineHeight: 1.65 },
    body2: { lineHeight: 1.6 },
  },
  components: {
    MuiCard: { styleOverrides: { root: { borderRadius: 20, backgroundColor: '#192529', borderColor: alpha('#B7C5C6', 0.18) } } },
    MuiCardContent: { styleOverrides: { root: { padding: 24, '&:last-child': { paddingBottom: 24 }, '@media (max-width:599px)': { padding: 16, '&:last-child': { paddingBottom: 16 } } } } },
    MuiChip: { styleOverrides: { root: { borderRadius: 8, fontWeight: 650, maxWidth: '100%', height: 'auto', minHeight: 28 }, label: { whiteSpace: 'normal', paddingBlock: 3, overflowWrap: 'anywhere' } } },
    MuiTab: { styleOverrides: { root: { minHeight: 48, minWidth: 0, textTransform: 'none', fontWeight: 700 } } },
    MuiTabs: { styleOverrides: { root: { backgroundColor: alpha('#F5F7F4', 0.035), borderRadius: 12 }, indicator: { height: 3, borderRadius: 3 } } },
  },
})

const paths = {
  feed: 'M4 4h16v16H4z M8 8h8 M8 12h8 M8 16h5',
  training: 'M5 7v10 M2 9v6 M19 7v10 M22 9v6 M5 12h14',
  assistant: 'M5 4h14v12h-7l-5 4v-4H5z M8 8h8 M8 12h5',
  pending: 'M14 3H5v18h14v-9 M9 8h3 M9 12h3 M9 16h6 M18 2v6 M15 5h6',
  plans: 'M8 3h12v15H8z M4 7v14h12 M11 7h6 M11 11h6 M11 15h4',
  clients: 'M16 21v-3a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v3 M21 21v-3a4 4 0 0 0-3-4 M13 6a4 4 0 1 1-8 0 4 4 0 0 1 8 0 M17 2a4 4 0 0 1 0 8',
  equipment: 'M4 4h6v6H4z M14 4h6v6h-6z M4 14h6v6H4z M14 14h6v6h-6z',
  profile: 'M20 21v-2a6 6 0 0 0-6-6h-4a6 6 0 0 0-6 6v2 M16 6a4 4 0 1 1-8 0 4 4 0 0 1 8 0',
  onboarding: 'M16 4h3v17H5V4h3 M8 2h8v5H8z M8 12h8 M8 16h5',
  logout: 'M9 3H4v18h5 M9 12h12 M17 8l4 4-4 4',
  menu: 'M4 6h16 M4 12h16 M4 18h16',
  close: 'M6 6l12 12 M6 18 18 6',
  image: 'M3 3h18v18H3z M3 16l6-6 5 5 3-3 4 4 M16 7h.01',
  send: 'm3 3 18 9-18 9 4-9-4-9z M7 12h14',
  comment: 'M4 4h16v13H9l-5 4V4z M8 8h8 M8 12h5',
  heart: 'M12 21 3.5 12.5C-2 6 7 0 12 6c5-6 14 0 8.5 6.5z',
  edit: 'm4 16-1 5 5-1L21 7l-4-4L4 16z M14 6l4 4',
  settings: 'M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8 M12 2v3 M12 19v3 M2 12h3 M19 12h3 M5 5l2 2 M17 17l2 2 M5 19l2-2 M17 7l2-2',
} as const
export type WorkspaceIconName = keyof typeof paths
export function WorkspaceIcon({ name }: { name: WorkspaceIconName }) {
  return <SvgIcon aria-hidden="true" sx={{ fontSize: 21, flexShrink: 0 }}><path d={paths[name]} fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" /></SvgIcon>
}

export const navigationLinkSx = {
  justifyContent: 'flex-start', px: 1.75, py: 1.25, width: '100%', minHeight: 48,
  borderRadius: 2, color: 'text.secondary', fontWeight: 600,
  '& .MuiButton-startIcon': { mr: 1.5 },
  '&[aria-current="page"]': { color: 'primary.main', bgcolor: 'rgba(255,133,100,0.10)', boxShadow: 'inset 3px 0 #FF8564' },
  '&:hover': { bgcolor: 'rgba(245,247,244,0.06)', color: 'text.primary' },
}
