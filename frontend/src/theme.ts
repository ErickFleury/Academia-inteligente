import { alpha, createTheme } from '@mui/material/styles'

const ink = '#10181B'
const chalk = '#F5F7F4'
const coral = '#FF8564'
const border = '#405157'

export const theme = createTheme({
  palette: {
    mode: 'dark',
    primary: { main: coral, contrastText: '#172024' },
    secondary: { main: '#90CBE9', contrastText: ink },
    success: { main: '#85D8AD', contrastText: ink },
    warning: { main: '#F5C968', contrastText: ink },
    error: { main: '#FF9A91', contrastText: ink },
    info: { main: '#90CBE9', contrastText: ink },
    background: { default: ink, paper: '#1B272B' },
    text: { primary: chalk, secondary: '#B7C5C6' },
    divider: border,
  },
  shape: { borderRadius: 12 },
  spacing: 8,
  typography: {
    fontFamily: 'Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
    h1: { fontSize: 'clamp(2.25rem, 7vw, 4.75rem)', fontWeight: 800, letterSpacing: '-0.055em', lineHeight: 0.98 },
    h2: { fontSize: 'clamp(1.8rem, 4vw, 3rem)', fontWeight: 800, letterSpacing: '-0.04em', lineHeight: 1.04 },
    h3: { fontSize: '1.25rem', fontWeight: 750, letterSpacing: '-0.02em' },
    h4: { fontSize: '1.1rem', fontWeight: 750 },
    button: { fontWeight: 750, letterSpacing: '0.015em', textTransform: 'none' },
    overline: { fontWeight: 800, fontSize: '0.72rem', letterSpacing: '0.12em', lineHeight: 1.5 },
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: { minWidth: 320, backgroundColor: ink },
        '*:focus-visible': { outline: `3px solid ${alpha('#90CBE9', 0.95)}`, outlineOffset: 3 },
      },
    },
    MuiIconButton: { styleOverrides: { root: { minWidth: 44, minHeight: 44 } } },
    MuiButton: {
      defaultProps: { disableElevation: true },
      styleOverrides: {
        root: {
          minHeight: 44,
          borderRadius: 10,
          paddingInline: 20,
          '&.Mui-disabled': { color: alpha(chalk, 0.46) },
        },
        outlined: { borderColor: alpha(chalk, 0.35), '&:hover': { borderColor: coral, backgroundColor: alpha(coral, 0.08) } },
      },
    },
    MuiTextField: { defaultProps: { variant: 'outlined', size: 'medium' } },
    MuiOutlinedInput: {
      styleOverrides: {
        root: {
          backgroundColor: alpha(chalk, 0.035),
          '&:hover .MuiOutlinedInput-notchedOutline': { borderColor: '#90CBE9' },
          '&.Mui-focused .MuiOutlinedInput-notchedOutline': { borderWidth: 2 },
        },
      },
    },
    MuiFormHelperText: { styleOverrides: { root: { marginInline: 0, lineHeight: 1.35 } } },
    MuiCard: {
      styleOverrides: {
        root: {
          border: `1px solid ${alpha(chalk, 0.13)}`,
          borderRadius: 16,
          boxShadow: 'none',
          backgroundImage: 'none',
        },
      },
    },
    MuiAlert: { styleOverrides: { root: { alignItems: 'center', borderRadius: 10 } } },
    MuiChip: { styleOverrides: { root: { fontWeight: 750, borderRadius: 8 } } },
    MuiSnackbarContent: { styleOverrides: { root: { borderRadius: 10 } } },
  },
})
